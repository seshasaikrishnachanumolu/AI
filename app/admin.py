import csv
import io
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from .extensions import db
from .models import (
    Alert,
    BinCompartment,
    CollectionRecord,
    Location,
    SmartBin,
    WasteRecord,
)
from .services import bins as bin_service
from .utils import admin_required

bp = Blueprint("admin", __name__)


def _thresholds():
    c = current_app.config
    return c["ALMOST_FULL_PERCENT"], c["ALERT_PERCENT"]


# ---------------------------------------------------------------- dashboard
def compute_stats():
    """All dashboard figures, calculated from stored records only."""
    cfg = current_app.config
    total = WasteRecord.query.count()
    recyclable = WasteRecord.query.filter_by(is_recyclable=True).count()
    by_cat = dict(
        db.session.query(WasteRecord.category, db.func.count(WasteRecord.id))
        .group_by(WasteRecord.category)
        .all()
    )
    counts = bin_service.bin_status_counts(*_thresholds())
    return {
        "total": total,
        "recyclable": recyclable,
        "non_recyclable": total - recyclable,
        "categories": {c: by_cat.get(c, 0) for c in cfg["CATEGORIES"]},
        "bins_total": SmartBin.query.count(),
        "bins_normal": counts["Normal"],
        "bins_almost": counts["Almost Full"],
        "bins_collect": counts["Collection Required"],
        "open_alerts": Alert.query.filter_by(resolved=False).count(),
        "pending_collections": CollectionRecord.query.filter_by(status="pending").count(),
    }


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", stats=compute_stats())


@bp.route("/api/live")
@admin_required
def api_live():
    """Polled by the dashboard every few seconds."""
    almost, alert = _thresholds()
    bins_out = []
    for b in SmartBin.query.order_by(SmartBin.id).all():
        bins_out.append(
            {
                "id": b.id,
                "name": b.name,
                "location": b.location.name,
                "fill": b.max_fill_percent,
                "status": b.status(almost, alert),
                "url": url_for("admin.bin_detail", bin_id=b.id),
                "compartments": [
                    {"category": c.category, "fill": c.fill_percent, "load": c.current_load, "max": c.max_capacity}
                    for c in sorted(b.compartments, key=lambda c: c.category)
                ],
            }
        )
    recent = WasteRecord.query.order_by(WasteRecord.id.desc()).limit(8).all()
    alerts = Alert.query.filter_by(resolved=False).order_by(Alert.id.desc()).limit(6).all()
    latest_alert = db.session.query(db.func.max(Alert.id)).scalar() or 0
    return jsonify(
        stats=compute_stats(),
        bins=bins_out,
        recent=[
            {
                "id": r.id,
                "category": r.category,
                "confidence": r.confidence,
                "user": r.user.name,
                "location": r.bin.location.name if r.bin else None,
                "bin": r.bin.name if r.bin else None,
                "at": r.created_at.isoformat() + "Z",
            }
            for r in recent
        ],
        alerts=[{"id": a.id, "message": a.message, "at": a.created_at.isoformat() + "Z"} for a in alerts],
        latest_alert_id=latest_alert,
        server_time=datetime.utcnow().isoformat() + "Z",
    )

# --------------------------------------------------------------------- bins
@bp.route("/bins", methods=["GET", "POST"])
@admin_required
def bins():
    cfg = current_app.config
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        loc_id = request.form.get("location_id", type=int)
        capacity = request.form.get("capacity", type=float)
        if not name or len(name) > 100:
            flash("Enter a bin name (max 100 characters).", "danger")
        elif db.session.get(Location, loc_id) is None:
            flash("Choose a valid location.", "danger")
        elif capacity is not None and not (0 < capacity <= 10000):
            flash("Capacity must be between 0 and 10000 litres.", "danger")
        else:
            bin_service.create_bin(name, loc_id, capacity)
            db.session.commit()
            flash(f"Bin '{name}' created with one compartment per category.", "success")
        return redirect(url_for("admin.bins"))
    return render_template(
        "admin/bins.html",
        bins=SmartBin.query.order_by(SmartBin.id).all(),
        locations=Location.query.order_by(Location.name).all(),
        default_capacity=cfg["DEFAULT_COMPARTMENT_CAPACITY"],
    )


@bp.route("/bins/<int:bin_id>")
@admin_required
def bin_detail(bin_id):
    b = db.session.get(SmartBin, bin_id) or abort(404)
    history = (
        CollectionRecord.query.filter_by(bin_id=b.id)
        .order_by(CollectionRecord.requested_at.desc())
        .limit(10)
        .all()
    )
    recent = (
        WasteRecord.query.filter_by(bin_id=b.id)
        .order_by(WasteRecord.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template("admin/bin_detail.html", b=b, history=history, recent=recent)


@bp.route("/bins/<int:bin_id>/capacity", methods=["POST"])
@admin_required
def set_capacity(bin_id):
    b = db.session.get(SmartBin, bin_id) or abort(404)
    changed = False
    for comp in b.compartments:
        raw = request.form.get(f"capacity_{comp.id}")
        if raw is None or raw == "":
            continue
        try:
            value = float(raw)
        except ValueError:
            flash(f"Invalid capacity for {comp.category}.", "danger")
            return redirect(url_for("admin.bin_detail", bin_id=b.id))
        if not (0 < value <= 10000):
            flash(f"Capacity for {comp.category} must be between 0 and 10000 litres.", "danger")
            return redirect(url_for("admin.bin_detail", bin_id=b.id))
        comp.max_capacity = value
        changed = True
    if changed:
        db.session.commit()
        flash("Compartment capacities updated.", "success")
    return redirect(url_for("admin.bin_detail", bin_id=b.id))


# -------------------------------------------------------------- collections
@bp.route("/collections")
@admin_required
def collections():
    almost, alert = _thresholds()
    pending = (
        CollectionRecord.query.filter_by(status="pending")
        .order_by(CollectionRecord.requested_at)
        .all()
    )
    completed = (
        CollectionRecord.query.filter_by(status="completed")
        .order_by(CollectionRecord.collected_at.desc())
        .limit(50)
        .all()
    )
    pending_bin_ids = {p.bin_id for p in pending}
    needing = [
        b
        for b in SmartBin.query.all()
        if b.status(almost, alert) != "Normal" and b.id not in pending_bin_ids
    ]
    return render_template(
        "admin/collections.html", pending=pending, completed=completed, needing=needing
    )


@bp.route("/bins/<int:bin_id>/request-collection", methods=["POST"])
@admin_required
def request_collection(bin_id):
    b = db.session.get(SmartBin, bin_id) or abort(404)
    if not CollectionRecord.query.filter_by(bin_id=b.id, status="pending").first():
        db.session.add(CollectionRecord(bin_id=b.id, status="pending"))
        db.session.commit()
        flash(f"Collection requested for {b.name}.", "success")
    else:
        flash("A collection is already pending for this bin.", "info")
    return redirect(request.referrer or url_for("admin.collections"))


@bp.route("/bins/<int:bin_id>/collect", methods=["POST"])
@admin_required
def collect(bin_id):
    b = db.session.get(SmartBin, bin_id) or abort(404)
    rec = bin_service.reset_bin(b, current_user)
    db.session.commit()
    flash(
        f"{b.name} marked as collected ({rec.volume_collected} L simulated). Capacity reset.",
        "success",
    )
    return redirect(request.referrer or url_for("admin.collections"))


# ------------------------------------------------------------------- alerts
@bp.route("/alerts")
@admin_required
def alerts():
    items = Alert.query.order_by(Alert.resolved, Alert.created_at.desc()).limit(100).all()
    return render_template("admin/alerts.html", alerts=items)


@bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@admin_required
def resolve_alert(alert_id):
    a = db.session.get(Alert, alert_id) or abort(404)
    a.resolved = True
    a.resolved_at = datetime.utcnow()
    db.session.commit()
    flash("Alert marked as resolved.", "success")
    return redirect(url_for("admin.alerts"))


# ---------------------------------------------------------------- locations
@bp.route("/locations", methods=["GET", "POST"])
@admin_required
def locations():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()[:255]
        if not name or len(name) > 100:
            flash("Enter a location name (max 100 characters).", "danger")
        elif Location.query.filter_by(name=name).first():
            flash("That location already exists.", "danger")
        else:
            db.session.add(Location(name=name, description=desc))
            db.session.commit()
            flash("Location added.", "success")
        return redirect(url_for("admin.locations"))
    return render_template("admin/locations.html", locations=Location.query.order_by(Location.name).all())


# ---------------------------------------------------------------- analytics
def _bucket_key(d, period):
    if period == "daily":
        return d.date()
    if period == "weekly":
        return d.date() - timedelta(days=d.weekday())
    return date(d.year, d.month, 1)


def _buckets(period, today):
    if period == "daily":
        return [today - timedelta(days=i) for i in range(6, -1, -1)]
    if period == "weekly":
        monday = today - timedelta(days=today.weekday())
        return [monday - timedelta(weeks=i) for i in range(7, -1, -1)]
    out, y, m = [], today.year, today.month
    for _ in range(12):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def analytics_data(period):
    cfg = current_app.config
    today = datetime.utcnow().date()
    buckets = _buckets(period, today)
    start = datetime.combine(buckets[0], datetime.min.time())
    records = WasteRecord.query.filter(WasteRecord.created_at >= start).all()

    series = {c: defaultdict(int) for c in cfg["CATEGORIES"]}
    by_location, by_category = Counter(), Counter()
    for r in records:
        series.setdefault(r.category, defaultdict(int))[_bucket_key(r.created_at, period)] += 1
        by_category[r.category] += 1
        by_location[r.bin.location.name if r.bin else "Unassigned"] += 1

    fmt = {"daily": "%d %b", "weekly": "Wk of %d %b", "monthly": "%b %Y"}[period]
    return {
        "period": period,
        "labels": [b.strftime(fmt) for b in buckets],
        "series": {c: [series[c].get(b, 0) for b in buckets] for c in series},
        "totals": [sum(series[c].get(b, 0) for c in series) for b in buckets],
        "by_category": dict(by_category),
        "by_location": dict(by_location),
        "count": len(records),
    }


@bp.route("/analytics")
@admin_required
def analytics():
    return render_template("admin/analytics.html")


@bp.route("/api/analytics")
@admin_required
def api_analytics():
    period = request.args.get("period", "daily")
    if period not in ("daily", "weekly", "monthly"):
        return jsonify(error="period must be daily, weekly or monthly"), 400
    return jsonify(analytics_data(period))


# ------------------------------------------------------------------ history
def _filtered_records():
    q = WasteRecord.query
    cat = request.args.get("category")
    loc = request.args.get("location_id", type=int)
    if cat:
        q = q.filter(WasteRecord.category == cat)
    if loc:
        q = q.join(SmartBin, WasteRecord.bin_id == SmartBin.id).filter(SmartBin.location_id == loc)
    return q.order_by(WasteRecord.created_at.desc())


@bp.route("/history")
@admin_required
def history():
    page = request.args.get("page", 1, type=int)
    pagination = _filtered_records().paginate(page=page, per_page=20, error_out=False)
    return render_template(
        "admin/history.html",
        pagination=pagination,
        locations=Location.query.order_by(Location.name).all(),
        categories=current_app.config["CATEGORIES"],
    )


def _csv_safe(value):
    """Prevent spreadsheet formula injection in exported cells."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


@bp.route("/reports/export.csv")
@admin_required
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["id", "date_utc", "user", "category", "confidence_%", "recyclable",
         "location", "bin", "estimated_volume_L"]
    )
    for r in _filtered_records().all():
        w.writerow(
            [
                r.id,
                r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                _csv_safe(r.user.email),
                r.category,
                r.confidence,
                "yes" if r.is_recyclable else "no",
                _csv_safe(r.bin.location.name) if r.bin else "",
                _csv_safe(r.bin.name) if r.bin else "",
                r.estimated_volume,
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=waste_report.csv"},
    )
