FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask prometheus-flask-exporter

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]
