import os

from flask import Flask, jsonify, render_template, request

from config import Config

from .extensions import csrf, db, login_manager


def _configure_logging(app):
    """Rotating file log (logs/app.log) in addition to console output."""
    if app.testing or app.debug:
        return
    import logging
    from logging.handlers import RotatingFileHandler

    log_dir = os.path.join(os.path.dirname(app.root_path), "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(os.path.join(log_dir, "app.log"), maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///") and ":memory:" not in uri:
        os.makedirs(os.path.dirname(uri.replace("sqlite:///", "")), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from . import models  # noqa: F401  (register models)
    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    _configure_logging(app)
    if not app.testing and not app.debug and app.config["SECRET_KEY"] == "dev-only-change-me":
        app.logger.warning("SECRET_KEY is the insecure development default. Set SECRET_KEY in .env.")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        if request.path.startswith(("/admin", "/api", "/uploads", "/result", "/history")):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def inject_globals():
        return {
            "ALMOST_FULL": app.config["ALMOST_FULL_PERCENT"],
            "ALERT": app.config["ALERT_PERCENT"],
        }

    @app.template_filter("dt")
    def fmt_dt(value):
        return value.strftime("%d %b %Y, %H:%M") if value else "-"

    def wants_json():
        return request.path.startswith("/api/") or request.path.startswith("/admin/api/")

    @app.errorhandler(403)
    def forbidden(e):
        if wants_json():
            return jsonify(error="Forbidden"), 403
        return render_template("error.html", code=403, message="Access denied."), 403

    @app.errorhandler(404)
    def not_found(e):
        if wants_json():
            return jsonify(error="Not found"), 404
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(e):
        if wants_json():
            return jsonify(error="Image too large (max 8 MB)."), 413
        return render_template("error.html", code=413, message="Image too large (max 8 MB)."), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        if wants_json():
            return jsonify(error="Internal server error"), 500
        return render_template("error.html", code=500, message="Something went wrong."), 500

    return app
