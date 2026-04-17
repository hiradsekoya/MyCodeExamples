from flask import Blueprint, jsonify
from ..models import db, Telemetry, Device, Zone, Alert
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint("reports", __name__)

# -------------------------------------------
# GET /api/reports/resource-usage
# -------------------------------------------
@bp.route("/resource-usage", methods=["GET"])
def resource_usage():
    """
    Returns lightweight resource usage statistics.
    These values are approximate and intended for dashboard KPIs.
    """

    # Count total telemetry entries
    total_telemetry = Telemetry.query.count()

    # Last 24 hours range
    since = datetime.utcnow() - timedelta(hours=24)

    # Compute averages for last 24 hours
    recent = (
        db.session.query(Telemetry)
        .filter(Telemetry.timestamp >= since)
        .all()
    )

    avg_temp = None
    avg_humidity = None
    avg_moist = None

    if recent:
        temps = [t.payload.get("temperature") for t in recent if "temperature" in t.payload]
        hums = [t.payload.get("humidity") for t in recent if "humidity" in t.payload]
        moist = [t.payload.get("soil_moisture") for t in recent if "soil_moisture" in t.payload]

        avg_temp = round(sum(temps) / len(temps), 2) if temps else None
        avg_humidity = round(sum(hums) / len(hums), 2) if hums else None
        avg_moist = round(sum(moist) / len(moist), 2) if moist else None

    # Very simple estimation model:
    # Water usage ≈ soil-moisture deficit * device count
    # Energy usage ≈ temperature variation * device count
    device_count = Device.query.count()
    zone_count = Zone.query.count()
    active_alerts = Alert.query.filter_by(acknowledged=False).count()

    estimated_water = None
    estimated_energy = None

    if avg_moist is not None:
        moisture_deficit = max(0, 40 - avg_moist)
        estimated_water = round(moisture_deficit * device_count * 0.1, 2)

    if avg_temp is not None:
        temp_variation = abs(avg_temp - 24)
        estimated_energy = round(temp_variation * device_count * 0.05, 2)

    return jsonify({
        "summary": {
            "zones": zone_count,
            "devices": device_count,
            "active_alerts": active_alerts,
            "total_telemetry_entries": total_telemetry
        },
        "environment_avg_24h": {
            "temperature": avg_temp,
            "humidity": avg_humidity,
            "soil_moisture": avg_moist
        },
        "estimated_usage": {
            "water_liters": estimated_water,
            "energy_kwh": estimated_energy
        },
        "window_hours": 24
    }), 200
