from flask import Blueprint, request, jsonify
from ..models import db, Device, Telemetry, Zone, Farm
from ..rule_engine import evaluate_rules_for_telemetry
from datetime import datetime
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import os

bp = Blueprint("telemetry", __name__)

SIM_TOKEN = os.getenv("SIM_TOKEN") 


@bp.route("/ingest", methods=["POST"])
def ingest():
    sim_token = request.headers.get("Sim-Token")
    is_simulation = (sim_token == SIM_TOKEN)

    if is_simulation:
        user_id = None
    else:

        try:
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())
        except Exception:
            return jsonify({"msg": "Missing or invalid token"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"msg": "invalid json"}), 400

    device_uid = data.get("device_uid")
    if not device_uid:
        return jsonify({"msg": "device_uid required"}), 400

    device = Device.query.filter_by(device_uid=device_uid).first()
    if not device:
        return jsonify({"msg": "device not registered"}), 404

    zone = Zone.query.get(device.zone_id)

    if not is_simulation:
        farm = Farm.query.filter_by(id=zone.farm_id, owner_id=user_id).first()
        if not farm:
            return jsonify({"msg": "device does not belong to your farms"}), 403

    temperature = data.get("temperature")
    humidity = data.get("humidity")
    soil_moisture = data.get("soil_moisture")
    ph = data.get("ph")
    ec = data.get("ec")
    ts = data.get("timestamp")

    timestamp = (
        datetime.utcnow() 
        if not ts else datetime.fromisoformat(ts.replace("Z", "+00:00"))
    )

    tel = Telemetry(
        device_id=device.id,
        temperature=temperature,
        humidity=humidity,
        soil_moisture=soil_moisture,
        ph=ph,
        ec=ec,
        created_at=timestamp
    )

    device.last_seen = timestamp

    db.session.add(tel)
    db.session.commit()

    zone.twin_state = {
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "ph": ph,
        "ec": ec,
        "last_seen": timestamp.isoformat()
    }
    db.session.commit()

    # --- 8) RULE ENGINE ---
    evaluate_rules_for_telemetry(zone, device, tel)

    return jsonify({"msg": "ok"}), 201


@bp.route("/latest", methods=["GET"])
def latest_snapshot():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return jsonify({"msg": "Missing or invalid token"}), 401

    zone_id = request.args.get("zone_id", type=int)

    q = Telemetry.query.order_by(Telemetry.created_at.desc())

    if zone_id:
        q = (
            q.join(Device)
             .join(Zone)
             .join(Farm)
             .filter(Device.zone_id == zone_id, Farm.owner_id == user_id)
        )
    else:
        q = (
            q.join(Device)
             .join(Zone)
             .join(Farm)
             .filter(Farm.owner_id == user_id)
        )

    tel = q.first()
    if not tel:
        return jsonify({}), 204

    return jsonify({
        "id": tel.id,
        "device_id": tel.device_id,
        "timestamp": tel.created_at.isoformat(),
        "payload": tel.payload
    }), 200



@bp.route("/history", methods=["GET"])
def history():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return jsonify({"msg": "Missing or invalid token"}), 401

    zone_id = request.args.get("zone_id", type=int)
    limit = request.args.get("limit", type=int, default=100)

    if not zone_id:
        return jsonify({"msg": "zone_id required"}), 400

    farm = (
        Farm.query.join(Zone, Zone.farm_id == Farm.id)
        .filter(Zone.id == zone_id, Farm.owner_id == user_id)
        .first()
    )

    if not farm:
        return jsonify({"msg": "zone not owned by you"}), 403

    q = (
        Telemetry.query.join(Device)
        .filter(Device.zone_id == zone_id)
        .order_by(Telemetry.created_at.desc())
        .limit(limit)
    )

    items = list(reversed(q.all()))

    out = [{
        "timestamp": t.created_at.isoformat(),
        "payload": t.payload,
        "device_id": t.device_id
    } for t in items]

    return jsonify(out), 200