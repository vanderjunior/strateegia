FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts/start_backend.sh ./scripts/start_backend.sh
COPY scripts/create_staging_user.py ./scripts/create_staging_user.py
RUN chmod +x ./scripts/start_backend.sh ./scripts/create_staging_user.py

EXPOSE 8000

CMD ["./scripts/start_backend.sh"]
