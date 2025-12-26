FROM python:3.11-slim

# Çalışma dizini
WORKDIR /app

# Python path (ÇOK ÖNEMLİ)
ENV PYTHONPATH=/app

# Requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# UYGULAMANIN TAMAMI (app klasörü dahil)
COPY app ./app

# Port
EXPOSE 8000

# Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]