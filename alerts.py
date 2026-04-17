from flask import Blueprint, jsonify
from ..models import db, Alert
from flask_jwt_extended import jwt_required

bp = Blueprint("alerts", __name__)

# -----------------------------
# GET /api/alerts/active
# -----------------------------
@bp.route("/active", methods=["GET"])
@jwt_required()
def active_alerts():
    """Return all unread alerts."""
    alerts = Alert.query.filter_by(read=False).order_by(Alert.timestamp.desc()).all()
    return jsonify([a.to_dict() for a in alerts]), 200


# -----------------------------
# POST /api/alerts/ack/<id>
# -----------------------------
@bp.route("/ack/<int:alert_id>", methods=["POST"])
@jwt_required()
def acknowledge_alert(alert_id):
    """Mark an alert as read."""
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"msg": "alert not found"}), 404

    alert.read = True
    db.session.commit()

    return jsonify({"msg": "alert acknowledged"}), 200
