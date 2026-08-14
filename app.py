"""Minimal web UI for the receipt OCR tool.

Serves a single page where you drop a receipt image and get the key
fields back. All the heavy lifting stays in ocr_receipt.py; this file is
just the HTTP glue.

Run:
    pip install -r requirements.txt
    python app.py
    # open http://localhost:5000
"""

import io
import os
import tempfile

from flask import Flask, jsonify, render_template, request

import ocr_receipt

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB uploads

# Allow the static GitHub Pages frontend (a different origin) to call /scan.
# Optional: the app still runs if flask-cors isn't installed.
try:
    from flask_cors import CORS

    CORS(app)
except ImportError:
    pass

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    file = request.files.get("image")
    if file is None or file.filename == "":
        return jsonify({"error": "No image uploaded."}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # Persist to a temp file so PIL / Donut can open it by path.
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = ocr_receipt.run(tmp_path)
    except Exception as exc:  # surface errors cleanly to the UI
        return jsonify({"error": f"OCR failed: {exc}"}), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
