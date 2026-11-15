import os
import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .extensions import db
from .models import Location, SmartBin, WasteRecord
from .services import bins as bin_service
from .services import classifier

bp = Blueprint("main", __name__)


class UploadError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def process_upload(file, location_id):
    """Validate + save the image, classify it, assign it to a virtual bin, store the record."""
    cfg = current_app.config
    location = db.session.get(Location, location_id) if location_id else None
    if location is None:
        raise UploadError("Select the location where the waste is being disposed.")
    if file is None or not file.filename:
        raise UploadError("Choose an image to upload or capture one with the webcam.")
    ext = secure_filename(file.filename).rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in cfg["ALLOWED_EXTENSIONS"]:
        raise UploadError("Unsupported file type. Use PNG, JPG, JPEG, WEBP or BMP.")

    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(cfg["UPLOAD_FOLDER"], filename)
    file.save(path)
    try:
        category, confidence = classifier.classify(path, cfg)
    except classifier.InvalidImage as e:
        os.remove(path)
        raise UploadError(str(e))
    except classifier.ModelNotAvailable as e:
        os.remove(path)
        raise UploadError(str(e), 503)
    except Exception:
        os.remove(path)
        current_app.logger.exception("Classification failed")
        raise UploadError("Classification failed. Please try another image.", 500)

    if confidence / 100 < cfg["MIN_CONFIDENCE"]:
        os.remove(path)
        raise UploadError(
            f"Prediction confidence too low ({confidence}%). Try a clearer image.", 422
        )

    volume = cfg["ESTIMATED_VOLUME_LITRES"].get(category, 0.5)
    compartment = bin_service.assign_waste(location.id, category, volume)
    record = WasteRecord(
        user_id=current_user.id,
        image_filename=filename,
        category=category,
        confidence=confidence,
        recommendation=classifier.RECOMMENDATIONS.get(category, ""),
        is_recyclable=category in cfg["RECYCLABLE_CATEGORIES"],
        estimated_volume=volume,
    )
    if compartment is not None:
        record.bin_id = compartment.bin_id
        record.compartment_id = compartment.id
    db.session.add(record)
    db.session.commit()
    return record


def record_to_dict(r):
    return {
        "id": r.id,
        "category": r.category,
        "confidence": r.confidence,
        "recommendation": r.recommendation,
        "recyclable": r.is_recyclable,
        "bin": r.bin.name if r.bin else None,
        "location": r.bin.location.name if r.bin else None,
        "assigned": r.bin_id is not None,
        "image_url": url_for("main.uploaded_file", filename=r.image_filename),
        "result_url": url_for("main.result", record_id=r.id),
    }


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/public-stats")
def public_stats():
    """Aggregate, non-personal counters for the landing page (real records only)."""
    total = WasteRecord.query.count()
    recyclable = WasteRecord.query.filter_by(is_recyclable=True).count()
    return jsonify(
        items=total,
        bins=SmartBin.query.count(),
        locations=Location.query.count(),
        recyclable_pct=round(recyclable / total * 100) if total else 0,
    )


@bp.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ok", database="up")
    except Exception:
        current_app.logger.exception("Health check failed")
        return jsonify(status="degraded", database="down"), 503


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    cfg = current_app.config
    q = WasteRecord.query.filter_by(user_id=current_user.id)
    total = q.count()
    recyclable = q.filter_by(is_recyclable=True).count()
    by_cat = dict(
        db.session.query(WasteRecord.category, db.func.count(WasteRecord.id))
        .filter(WasteRecord.user_id == current_user.id)
        .group_by(WasteRecord.category)
        .all()
    )
    recent = q.order_by(WasteRecord.created_at.desc()).limit(6).all()
    return render_template(
        "dashboard.html",
        total=total,
        recyclable=recyclable,
        categories={c: by_cat.get(c, 0) for c in cfg["CATEGORIES"]},
        recent=recent,
    )


@bp.route("/classify", methods=["GET", "POST"])
@login_required
def classify_page():
    locations = Location.query.order_by(Location.name).all()
    if request.method == "POST":
        try:
            loc_id = request.form.get("location_id", type=int)
            record = process_upload(request.files.get("image"), loc_id)
        except UploadError as e:
            flash(str(e), "danger")
            return render_template("classify.html", locations=locations), e.status
        if record.bin_id is None:
            flash(
                "Classified, but every bin at this location has no room left in the "
                f"{record.category} compartment. Collection is required.",
                "warning",
            )
        return redirect(url_for("main.result", record_id=record.id))
    return render_template("classify.html", locations=locations)


@bp.route("/api/classify", methods=["POST"])
@login_required
def api_classify():
    try:
        record = process_upload(request.files.get("image"), request.form.get("location_id", type=int))
    except UploadError as e:
        return jsonify(error=str(e)), e.status
    return jsonify(record_to_dict(record)), 201


@bp.route("/result/<int:record_id>")
@login_required
def result(record_id):
    record = db.session.get(WasteRecord, record_id)
    if record is None or (record.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    return render_template("result.html", r=record)


@bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    pagination = (
        WasteRecord.query.filter_by(user_id=current_user.id)
        .order_by(WasteRecord.created_at.desc())
        .paginate(page=page, per_page=12, error_out=False)
    )
    return render_template("history.html", pagination=pagination)


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    record = WasteRecord.query.filter_by(image_filename=filename).first()
    if record is None or (record.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
