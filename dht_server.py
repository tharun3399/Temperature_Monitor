import os
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# === Device configuration ===
# In production on Render, set DEVICE_001_TOKEN in the environment.
DEVICE_001_TOKEN = os.environ.get("DEVICE_001_TOKEN", "CHANGE_ME_TO_A_LONG_RANDOM_STRING")

# Map of device_id -> token (configure per device)
AUTHORIZED_DEVICES = {
    "device-001": DEVICE_001_TOKEN,
    # "device-002": "another_secret_here",
}

# Store last reading per device_id in memory.
# For a real production system you would persist this to a database.
last_readings = {}


def check_device_auth(device_id: str, token: str) -> bool:
    expected = AUTHORIZED_DEVICES.get(device_id)
    return expected is not None and token == expected


@app.route("/api/devices/<device_id>/readings", methods=["POST"])
def api_add_reading(device_id):
    """Receive data from ESP8266.

    Headers:
      X-Device-Token: <secret>

    JSON body:
      { "temperature": 23.4, "humidity": 55.0 }
    """

    token = request.headers.get("X-Device-Token", "")
    if not check_device_auth(device_id, token):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
        temperature = float(data.get("temperature"))
        humidity = float(data.get("humidity"))
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Invalid payload: {exc}"}), 400

    reading = {
        "device_id": device_id,
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    last_readings[device_id] = reading

    return jsonify({"status": "ok"})


@app.route("/api/devices/<device_id>/readings/latest", methods=["GET"])
def api_latest_reading(device_id):
    """Return the latest reading for a given device."""
    reading = last_readings.get(device_id)
    if reading is None:
        return jsonify({"status": "error", "message": "No data yet"}), 404
    return jsonify(reading)


@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok", "devices": list(last_readings.keys())})


if __name__ == "__main__":
    # Use PORT from environment for Render, default to 5000 for local dev.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
