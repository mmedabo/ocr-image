"""Receipt / warranty OCR.

Reads a receipt image, runs it through the Donut receipt model to get a
structured parse, and then pulls out the key parameters we care about:

    - Device ID & Model Number
    - Warranty Number / Receipt Number
    - Dates
    - Manufacturer / Service Provider (optional)

Usage:
    python ocr_receipt.py path/to/receipt.jpg
    python ocr_receipt.py path/to/receipt.jpg --raw     # also dump the full model parse
    python ocr_receipt.py path/to/receipt.jpg -o out.json

The Donut model gives us a best-effort structured parse of the whole
receipt; on top of that we run a light regex/keyword pass so the specific
fields above are found even when the model labels them differently.
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Model loading (lazy, so `--help` and imports stay fast)
# ---------------------------------------------------------------------------

MODEL_NAME = "mychen76/invoice-and-receipts_donut_v1"

_MODEL = None
_PROCESSOR = None
_DEVICE = None


def _load_model():
    """Load the Donut processor + model once and cache them."""
    global _MODEL, _PROCESSOR, _DEVICE
    if _MODEL is not None:
        return _PROCESSOR, _MODEL, _DEVICE

    import torch
    from transformers import DonutProcessor, VisionEncoderDecoderModel

    _PROCESSOR = DonutProcessor.from_pretrained(MODEL_NAME)
    _MODEL = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    _MODEL.to(_DEVICE)
    return _PROCESSOR, _MODEL, _DEVICE


# ---------------------------------------------------------------------------
# Step 1: run the receipt image through Donut -> structured dict
# ---------------------------------------------------------------------------

def parse_receipt(image_path: str) -> Dict[str, Any]:
    """Run the Donut model on a receipt image and return its structured parse."""
    import torch
    from PIL import Image

    processor, model, device = _load_model()

    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values

    # Prime the decoder with the receipt task token.
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
    # Strip the leading task token so token2json parses the body cleanly.
    sequence = re.sub(r"<s_receipt>", "", sequence, count=1).strip()

    parsed = processor.token2json(sequence)
    return parsed if isinstance(parsed, dict) else {"receipt": parsed}


# ---------------------------------------------------------------------------
# Step 2: flatten + extract the fields we actually need
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    # 2024-01-31, 2024/01/31
    r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b",
    # 31-01-2024, 01/31/2024, 31.01.24
    r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
    # 31 Jan 2024 / Jan 31, 2024
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{2,4}\b",
    r"\b[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{2,4}\b",
]

# Keyword -> which output field the value should land in.
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
    """Flatten nested dict/list from Donut into (key, value) string pairs."""
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
    """Map the raw Donut parse onto the required key parameters."""
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

    # 1) Match by key name coming out of the model.
    for key, value in pairs:
        for field, keywords in FIELD_KEYWORDS.items():
            if result.get(field):
                continue
            if any(kw in key for kw in keywords):
                result[field] = value.strip()

    # 2) Fallback: scan values themselves for "Label: value" patterns.
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

    # 3) Dates: collect everything date-shaped from the whole parse.
    result["dates"] = _find_dates(all_text)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(image_path: str) -> Dict[str, Any]:
    parsed = parse_receipt(image_path)
    fields = extract_fields(parsed)
    return {"fields": fields, "raw": parsed}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="OCR a receipt and extract key fields.")
    ap.add_argument("image", help="path to the receipt image (jpg/png)")
    ap.add_argument("-o", "--output", help="write result JSON to this file")
    ap.add_argument(
        "--raw", action="store_true", help="include the full Donut parse in the output"
    )
    args = ap.parse_args(argv)

    result = run(args.image)
    if not args.raw:
        result = {"fields": result["fields"]}

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
