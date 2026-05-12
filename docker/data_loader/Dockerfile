# docker/data_loader/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

COPY requirements.txt .
# 🔥 Добавь в requirements.txt: fastapi, uvicorn, python-multipart
RUN pip install --no-cache-dir -r requirements.txt

COPY logger.py .
COPY config_manager.py .
COPY T_con.py .
COPY db_manager.py .
COPY main_loader.py .
COPY price_loader.py .
#COPY strategy/strategy_runner.py .
#COPY strategy.py .
COPY constants.py .
COPY db_queries.py .
COPY telegram_notifier.py .
COPY admin_ui /app/admin_ui/
COPY metrics /app/metrics/
COPY strategy /app/strategy/
#COPY ../../config.yaml .

RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["python", "-m", "main_loader"]