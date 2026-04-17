from flask import Blueprint, jsonify
from ..models import db, Farm, Zone, Device, Alert, Telemetry
from datetime import datetime, timedelta

bp = Blueprint("dashboard", __name__)

# ----------------------------------------
# GET /api/dashboard/stats
# ----------------------------------------
@bp.route("/stats", methods=["GET"])
def dashboard_stats():
    """
    Returns system-wide KPIs for the dashboard.
    Lightweight summary — fast and easily consumed by UI.
    """

    total_farms = Farm.query.count()
    total_zones = Zone.query.count()
    total_devices = Device.query.count()

    # Device online/offline calculation
    now = datetime.utcnow()
    online_devices = 0
    offline_devices = 0

    for d in Device.query.all():
        if d.last_seen and (now - d.last_seen) < timedelta(seconds=30):
            online_devices += 1
        else:
            offline_devices += 1

    # Alerts
    active_alerts = Alert.query.filter_by(acknowledged=False).count()
    acknowledged_alerts = Alert.query.filter_by(acknowledged=True).count()

    # Latest telemetry snapshot (global)
    latest = Telemetry.query.order_by(Telemetry.timestamp.desc()).first()
    latest_payload = latest.payload if latest else None
    latest_time = latest.timestamp.isoformat() if latest else None

    # Approximate averages from the last hour
    one_hour_ago = now - timedelta(hours=1)
    recent = Telemetry.query.filter(Telemetry.timestamp >= one_hour_ago).all()

    avg_temp = None
    avg_humidity = None
    avg_moisture = None

    if recent:
        temps = [t.payload.get("temperature") for t in recent if "temperature" in t.payload]
        hums = [t.payload.get("humidity") for t in recent if "humidity" in t.payload]
        moist = [t.payload.get("soil_moisture") for t in recent if "soil_moisture" in t.payload]

        avg_temp = round(sum(temps) / len(temps), 2) if temps else None
        avg_humidity = round(sum(hums) / len(hums), 2) if hums else None
        avg_moisture = round(sum(moist) / len(moist), 2) if moist else None

    return jsonify({
        "entities": {
            "farms": total_farms,
            "zones": total_zones,
            "devices": total_devices
        },
        "devices_status": {
            "online": online_devices,
            "offline": offline_devices
        },
        "alerts": {
            "active": active_alerts,
            "acknowledged": acknowledged_alerts
        },
        "latest_snapshot": {
            "timestamp": latest_time,
            "payload": latest_payload
        },
        "recent_averages_last_1h": {
            "temperature": avg_temp,
            "humidity": avg_humidity,
            "soil_moisture": avg_moisture
        }
    }), 200
