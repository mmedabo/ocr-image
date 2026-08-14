---
title: OCR Image Donut
emoji: 🧾
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
---

# OCR Image — Donut receipt scanner

Runs the Donut receipt model to extract key fields (device ID, model
number, warranty/receipt number, dates, manufacturer) from a receipt or
warranty image.

Companion to the [ocr-image](https://github.com/mmedabo/ocr-image) repo.
Runs on the **free** Gradio CPU tier — no Docker, no Pro.

## Deploy (free)

1. Create a new Space at <https://huggingface.co/new-space>:
   - **SDK: Gradio** (the free SDK — *not* the "Gradio-Lite" static
     template, and not Docker)
   - **Hardware: CPU basic · Free**
   - **Visibility: Public**
   - Name it `ocr-image`.
2. Upload the three files from this folder to the Space repo root:
   `app.py`, `requirements.txt`, and this `README.md`.
3. Wait for the build. The first scan downloads the model (~1 GB) and is
   slow; later scans are fast while the Space stays awake.

Your app will be live at `https://<username>-ocr-image.hf.space`.

## API

The Space also exposes an API (see the "Use via API" link at the bottom of
the Space page), so the GitHub Pages frontend can call it if you want to
wire the two together.
