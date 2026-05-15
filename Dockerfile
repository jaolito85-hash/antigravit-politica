FROM python:3.11-slim

WORKDIR /app

# ffmpeg necessário para yt-dlp extrair/converter áudio (aba Vídeos & Podcasts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5004

ENV PORT=5004
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-w", "4", "--timeout", "300", "-b", "0.0.0.0:5004", "server:app"]
