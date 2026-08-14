---
title: OCR Image Donut Backend
emoji: 🧾
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# OCR Image — Donut backend

This Space runs the original Donut receipt model (`app.py` + `ocr_receipt.py`)
as an HTTP API for the [ocr-image](https://github.com/mmedabo/ocr-image)
GitHub Pages frontend.

- `POST /scan` with form field `image` → `{ "fields": {...}, "raw": {...} }`
- `GET /` → the same UI, served directly from the Space

The first request downloads the model (~1 GB) and is slow; later requests
are fast while the Space stays warm.

## Deploy

1. Create a new **Docker** Space at <https://huggingface.co/new-space>
   (name it `ocr-image` to match the frontend's default URL).
2. Upload the two files from this folder (`Dockerfile` and this `README.md`)
   to the Space repo root.
3. Wait for the build. Your API base URL will be
   `https://<username>-ocr-image.hf.space`.
4. Put that URL in `index.html` (`BACKEND_URL`) in the GitHub repo.
