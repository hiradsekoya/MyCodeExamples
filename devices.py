from flask import Blueprint, request, jsonify
from ..models import db, Device, Zone, Farm
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("devices", __name__)

# ---------------------------------------------------
# POST /api/devices/  → Register device
# ---------------------------------------------------
@bp.route("/", methods=["POST"])
@jwt_required()
def register_device():
    data = request.get_json()

    device_uid = data.get("device_uid")
    zone_id = data.get("zone_id")
    device_type = data.get("type")

    if not device_uid or not zone_id:
        return jsonify({"msg": "device_uid and zone_id required"}), 400

    # Allowed device types
    allowed_types = ["temp-only", "temp-hum-soil"]
    if device_type not in allowed_types:
        return jsonify({"msg": "Invalid device type"}), 400

    # UID must be unique
    if Device.query.filter_by(device_uid=device_uid).first():
        return jsonify({"msg": "device already exists"}), 400

    # Check zone existence
    zone = Zone.query.get(zone_id)
    if not zone:
        return jsonify({"msg": "zone not found"}), 404

    # Check ownership
    owner_id = int(get_jwt_identity())
    farm = Farm.query.filter_by(id=zone.farm_id, owner_id=owner_id).first()
    if not farm:
        return jsonify({"msg": "zone does not belong to your farms"}), 403

    # Create device
    d = Device(
        device_uid=device_uid,
        zone_id=zone_id,
        type=device_type,
        last_seen=None
    )

    db.session.add(d)
    db.session.commit()

    return jsonify({
        "id": d.id,
        "device_uid": d.device_uid,
        "zone_id": d.zone_id,
        "type": d.type
    }), 201


# ---------------------------------------------------
# GET /api/devices/ → List user's devices
# ---------------------------------------------------
@bp.route("/", methods=["GET"])
@jwt_required()
def list_devices():
    owner_id = int(get_jwt_identity())

    devices = (
        Device.query
        .join(Zone, Zone.id == Device.zone_id)
        .join(Farm, Farm.id == Zone.farm_id)
        .filter(Farm.owner_id == owner_id)
        .all()
    )

    out = [{
        "id": d.id,
        "device_uid": d.device_uid,
        "zone_id": d.zone_id,
        "farm_id": d.zone.farm_id if d.zone else None,
        "type": d.type,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None
    } for d in devices]



    return jsonify(out), 200


# ---------------------------------------------------
# GET /api/devices/status → Online/offline status
# ---------------------------------------------------
@bp.route("/status", methods=["GET"])
@jwt_required()
def device_status():
    owner_id = int(get_jwt_identity())
    now = datetime.utcnow()

    devices = (
        Device.query
        .join(Zone, Zone.id == Device.zone_id)
        .join(Farm, Farm.id == Zone.farm_id)
        .filter(Farm.owner_id == owner_id)
        .all()
    )

    out = []
    for d in devices:
        last_seen = d.last_seen
        online = last_seen and (now - last_seen) < timedelta(seconds=30)

        out.append({
            "id": d.id,
            "device_uid": d.device_uid,
            "zone_id": d.zone_id,
            "type": d.type,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "online": bool(online)
        })

    return jsonify(out), 200


# ---------------------------------------------------
# DELETE /api/devices/<id> → Delete device
# ---------------------------------------------------
@bp.route("/<int:device_id>", methods=["DELETE"])
@jwt_required()
def delete_device(device_id):
    user_id = int(get_jwt_identity())

    device = Device.query.get(device_id)
    if not device:
        return jsonify({"msg": "Device not found"}), 404

    # Check ownership
    zone = Zone.query.get(device.zone_id)
    farm = Farm.query.filter_by(id=zone.farm_id, owner_id=user_id).first()
    if not farm:
        return jsonify({"msg": "Not allowed"}), 403

    db.session.delete(device)
    db.session.commit()

    return jsonify({"msg": "deleted"}), 200