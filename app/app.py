import os
import random
import time
from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Initialize Prometheus Metrics
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Application info', version=os.environ.get('VERSION', 'v1'))

# Get configuration from env
VERSION = os.environ.get('VERSION', 'v1')
ERROR_RATE = float(os.environ.get('ERROR_RATE', '0'))

@app.route('/')
def hello():
    # Inject artificial failure based on ERROR_RATE
    if ERROR_RATE > 0:
        if random.random() < ERROR_RATE:
            return jsonify({
                "status": "error",
                "message": "Internal Server Error (Simulated)",
                "version": VERSION
            }), 500
            
    return jsonify({
        "status": "success",
        "message": f"Hello from Python Flask API {VERSION}",
        "version": VERSION
    })

@app.route('/healthz')
def healthz():
    return jsonify({"status": "healthy", "version": VERSION}), 200

if __name__ == '__main__':
    # Flask app will listen on port 8080
    app.run(host='0.0.0.0', port=8080)
