# ocr-image

Small OCR tool that reads a receipt/warranty image and extracts the key
parameters needed for device warranty tracking.

## What it extracts

- **Device ID & Model Number**
- **Warranty Number / Receipt Number**
- **Dates**
- **Manufacturer / Service Provider** (optional)

## Live web app (GitHub Pages)

**→ https://mmedabo.github.io/ocr-image/**

The hosted app runs **entirely in your browser** — the image never leaves
your device. It uses [Tesseract.js](https://tesseract.projectnaptha.com/)
for OCR and the same regex/keyword layer (ported to JavaScript) to pull out
the fields above. This is what makes it hostable on GitHub Pages, which
only serves static files.

> The Python **Donut** model below is more accurate on structured receipts,
> but needs ~1 GB of weights and real compute, so it can't run on GitHub
> Pages. Use it locally/on a server when you want the higher-accuracy parse;
> use the static web app for zero-setup, private, in-browser scanning.

### Enabling Pages

Repo **Settings → Pages → Build and deployment → Source: _Deploy from a
branch_ → Branch: `main` / `/ (root)`**. The site is served from
`index.html` at the repo root.

### Using the Donut model from the web app

The web app can call the original **Donut** model instead of Tesseract by
pointing it at a backend that runs `app.py`. Deploy that backend to a
Hugging Face Space (see [`deploy/huggingface/`](deploy/huggingface/)),
then set `BACKEND_URL` near the top of `index.html` to the Space URL, e.g.:

```javascript
const BACKEND_URL = "https://mmedabo-ocr-image.hf.space";
```

When set, the app uploads the image to that backend and shows the Donut
parse. If the backend is unreachable (e.g. the Space is asleep), it
automatically falls back to in-browser Tesseract, so the page always works.

## Local version (Python + Donut)

How it works:

1. The image is run through the [Donut](https://huggingface.co/mychen76/invoice-and-receipts_donut_v1)
   receipt model, which produces a structured parse of the whole receipt.
2. A light regex/keyword pass maps that parse onto the specific fields
   above, so they are found even when the model labels them differently,
   and collects every date-shaped value it can find.

### Install

```bash
pip install -r requirements.txt
```

The model (~1 GB) downloads automatically from the Hugging Face Hub on
first run. A GPU is used automatically if available, otherwise it runs on
CPU.

### Local web UI (Flask)

A minimal, immersive single-page app for drag-and-drop scanning, backed by
the Donut model:

```bash
python app.py
# open http://localhost:5000
```

Drop a receipt/warranty image, hit **Scan**, and the extracted fields
appear as cards. The first scan takes longer because the model loads on
demand; subsequent scans are fast. All processing happens locally — the
image is held only in a temp file for the duration of the request and then
deleted.

### Command line

```bash
# Print the extracted fields as JSON
python ocr_receipt.py path/to/receipt.jpg

# Also include the full raw model parse
python ocr_receipt.py path/to/receipt.jpg --raw

# Write to a file
python ocr_receipt.py path/to/receipt.jpg -o result.json
```

### Example output

```json
{
  "fields": {
    "device_id": "SN-99231145",
    "model_number": "KD-55X80K",
    "warranty_number": "W-2024-8842",
    "receipt_number": "INV-00123",
    "dates": ["2024-01-31", "31 Jan 2024"],
    "manufacturer": "Sony",
    "service_provider": "ACME Electronics"
  }
}
```

### Use as a library

```python
from ocr_receipt import run

result = run("receipt.jpg")
print(result["fields"])   # the extracted key parameters
print(result["raw"])      # the full Donut parse
```
