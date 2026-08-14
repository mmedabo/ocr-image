"""Hugging Face Gradio Space: receipt OCR with the Donut model.

Self-contained so the Space only needs three files (this app.py, a
requirements.txt, and README.md). It loads the Donut receipt model, lets
you upload an image, and returns the key fields as JSON.

Runs on the free CPU tier — no Docker, no Pro needed.
"""

import re
from typing import Any, Dict, List, Optional

import gradio as gr
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

MODEL_NAME = "mychen76/invoice-and-receipts_donut_v1"

processor = DonutProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


# ---------------------------------------------------------------------------
# Donut: image -> structured parse
# ---------------------------------------------------------------------------

def parse_receipt(image: Image.Image) -> Dict[str, Any]:
    image = image.convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values

    task_prompt = "<s_receipt>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids

    with torch.no_grad():
        outputs = model.generate(
            pixel_values.to(device),
            decoder_input_ids=decoder_input_ids.to(device),
            max_length=model.config.decoder.max_position_embeddings,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(
        processor.tokenizer.pad_token, ""
    )
    sequence = re.sub(r"<s_receipt>", "", sequence, count=1).strip()

    parsed = processor.token2json(sequence)
    return parsed if isinstance(parsed, dict) else {"receipt": parsed}


# ---------------------------------------------------------------------------
# Map the parse onto the fields we need
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b",
    r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
    r"\b\d{1,2}[ \t]+[A-Za-z]{3,9}\.?[ \t]+\d{2,4}\b",
    r"\b[A-Za-z]{3,9}\.?[ \t]+\d{1,2},?[ \t]+\d{2,4}\b",
]

FIELD_KEYWORDS = {
    "device_id": ["device id", "deviceid", "device no", "device number", "imei", "serial"],
    "model_number": ["model number", "model no", "model #", "model:", "model"],
    "warranty_number": ["warranty number", "warranty no", "warranty #", "warranty"],
    "receipt_number": [
        "receipt number", "receipt no", "receipt #", "invoice number",
        "invoice no", "invoice #", "order number", "order no", "transaction",
    ],
    "manufacturer": ["manufacturer", "manufactured by", "brand", "make"],
    "service_provider": ["service provider", "provider", "retailer", "store", "sold by"],
}


def _flatten(obj: Any, out: Optional[List[tuple]] = None) -> List[tuple]:
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                _flatten(v, out)
            else:
                out.append((str(k).lower(), str(v)))
    elif isinstance(obj, list):
        for item in obj:
            _flatten(item, out)
    else:
        out.append(("", str(obj)))
    return out


def _find_dates(text: str) -> List[str]:
    found: List[str] = []
    for pat in DATE_PATTERNS:
        for m in re.findall(pat, text):
            if m not in found:
                found.append(m)
    return found


def extract_fields(parsed: Dict[str, Any]) -> Dict[str, Any]:
    pairs = _flatten(parsed)
    result: Dict[str, Any] = {
        "device_id": None,
        "model_number": None,
        "warranty_number": None,
        "receipt_number": None,
        "dates": [],
        "manufacturer": None,
        "service_provider": None,
    }

    for key, value in pairs:
        for field, keywords in FIELD_KEYWORDS.items():
            if result.get(field):
                continue
            if any(kw in key for kw in keywords):
                result[field] = value.strip()

    all_text = "\n".join(v for _, v in pairs)
    for field, keywords in FIELD_KEYWORDS.items():
        if result.get(field):
            continue
        for kw in keywords:
            m = re.search(
                rf"{re.escape(kw)}\s*[:#\-]?\s*([A-Za-z0-9\-/]+)",
                all_text,
                re.IGNORECASE,
            )
            if m:
                result[field] = m.group(1).strip()
                break

    result["dates"] = _find_dates(all_text)
    return result


# ---------------------------------------------------------------------------
# Gradio UI + API
# ---------------------------------------------------------------------------

def scan(image: Optional[Image.Image]) -> Dict[str, Any]:
    if image is None:
        return {"error": "No image provided."}
    parsed = parse_receipt(image)
    return {"fields": extract_fields(parsed), "raw": parsed}


demo = gr.Interface(
    fn=scan,
    inputs=gr.Image(type="pil", label="Receipt / warranty image"),
    outputs=gr.JSON(label="Extracted fields"),
    title="Receipt Scanner (Donut)",
    description=(
        "Upload a receipt or warranty image to extract its key details "
        "(device ID, model number, warranty/receipt number, dates, "
        "manufacturer). Powered by the Donut receipt model."
    ),
    allow_flagging="never",
)

if __name__ == "__main__":
    demo.launch()
