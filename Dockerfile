FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PUSHAN_API_HOST=0.0.0.0 \
    PUSHAN_API_PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY knowledge ./knowledge

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main_api:app", "--host", "0.0.0.0", "--port", "8000"]
