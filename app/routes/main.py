import os

from flask import Blueprint, current_app, render_template, send_from_directory

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/uploads/screenshots/<path:filename>")
def uploaded_screenshot(filename):
    folder = os.path.join(current_app.instance_path, "uploads", "screenshots")
    return send_from_directory(folder, filename)

