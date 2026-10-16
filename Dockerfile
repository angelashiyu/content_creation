FROM python:3.12-slim

# Unbuffered output so print() lines reach CloudWatch as they happen
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py config.json ./

USER nobody
CMD ["python", "pipeline.py"]
