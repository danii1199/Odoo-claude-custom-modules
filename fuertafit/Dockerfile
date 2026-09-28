FROM python:3.12-slim

# tzdata para que "hoy" sea la fecha de Madrid y no UTC.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core.py bot.py server.py ./
COPY static ./static

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Madrid

EXPOSE 8000
CMD ["python", "server.py"]
