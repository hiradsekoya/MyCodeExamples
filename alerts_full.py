from flask import Blueprint, request, jsonify
from ..models import db, Alert, Farm, Zone
from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("alerts_full", __name__)

# ------------------------------------------------
# GET /api/alerts/   (full alert center w/ filters)
# ------------------------------------------------
@bp.route("/", methods=["GET"])
@jwt_required()
def list_alerts():
    user_id = int(get_jwt_identity())

    farm_id = request.args.get("farm_id", type=int)
    zone_id = request.args.get("zone_id", type=int)
    severity = request.args.get("severity")
    unread = request.args.get("unread")

    q = Alert.query.join(Zone, Alert.zone_id == Zone.id).join(Farm, Zone.farm_id == Farm.id)
    q = q.filter(Farm.owner_id == user_id)

    if farm_id:
        q = q.filter(Alert.farm_id == farm_id)
    if zone_id:
        q = q.filter(Alert.zone_id == zone_id)
    if severity:
        q = q.filter(Alert.severity == severity)
    if unread == "true":
        q = q.filter(Alert.read == False)

    alerts = q.order_by(Alert.timestamp.desc()).all()

    return jsonify([a.to_dict() for a in alerts]), 200


# ------------------------------------------------
# PATCH /api/alerts/<id>   (update fields)
# ------------------------------------------------
@bp.route("/<int:alert_id>", methods=["PATCH"])
@jwt_required()
def update_alert(alert_id):
    a = Alert.query.get(alert_id)
    if not a:
        return jsonify({"msg": "alert not found"}), 404

    data = request.get_json() or {}
    if "read" in data:
        a.read = bool(data["read"])

    db.session.commit()
    return jsonify({"msg": "updated"}), 200
