FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PUSHAN_API_URL=http://pushan-api:8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend ./frontend

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "frontend/streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true"]
