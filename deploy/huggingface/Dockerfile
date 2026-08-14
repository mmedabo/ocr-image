# Docker Space that runs the Donut receipt backend (app.py + ocr_receipt.py).
# The app code is pulled from the public GitHub repo at build time, so this
# Space only needs this Dockerfile and README.md.

FROM python:3.10-slim

WORKDIR /app

# CPU-only torch keeps the image small and works on the free HF hardware.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
      flask flask-cors Pillow sentencepiece protobuf transformers

# App code, fetched from the public repo (main branch).
ADD https://raw.githubusercontent.com/mmedabo/ocr-image/main/ocr_receipt.py ./ocr_receipt.py
ADD https://raw.githubusercontent.com/mmedabo/ocr-image/main/app.py ./app.py
RUN mkdir -p templates
ADD https://raw.githubusercontent.com/mmedabo/ocr-image/main/templates/index.html ./templates/index.html

# Model weights + HF cache must live somewhere writable.
ENV HF_HOME=/tmp/huggingface
ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]
