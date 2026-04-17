from flask import Blueprint, request, jsonify
from ..models import db, Rule
from flask_jwt_extended import jwt_required

bp = Blueprint("rules", __name__)

# -------------------------------
# CREATE RULE
# -------------------------------
@bp.route("/", methods=["POST"])
@jwt_required()
def create_rule():
    data = request.get_json()
    name = data.get("name")
    condition = data.get("condition")  # JSON string
    action = data.get("action", "alert")
    zone_id = data.get("zone_id")

    if not name or not condition:
        return jsonify({"msg": "name and condition required"}), 400

    r = Rule(
        name=name,
        condition=condition,
        action=action,
        zone_id=zone_id,
        enabled=True
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"id": r.id, "name": r.name}), 201


# -------------------------------
# LIST ALL RULES
# -------------------------------
@bp.route("/", methods=["GET"])
@jwt_required(optional=True)
def list_rules():
    rules = Rule.query.all()
    out = []
    for r in rules:
        out.append({
            "id": r.id,
            "name": r.name,
            "condition": r.condition,
            "action": r.action,
            "enabled": r.enabled,
            "zone_id": r.zone_id
        })
    return jsonify(out)


# -------------------------------
# DELETE RULE
# -------------------------------
@bp.route("/<int:rule_id>", methods=["DELETE"])
@jwt_required()
def delete_rule(rule_id):
    r = Rule.query.get(rule_id)
    if not r:
        return jsonify({"msg": "rule not found"}), 404

    db.session.delete(r)
    db.session.commit()
    return jsonify({"msg": "rule deleted"}), 200


# -------------------------------
# ENABLE / DISABLE RULE (PATCH)
# -------------------------------
@bp.route("/<int:rule_id>", methods=["PATCH"])
@jwt_required()
def update_rule(rule_id):
    r = Rule.query.get(rule_id)
    if not r:
        return jsonify({"msg": "rule not found"}), 404

    data = request.get_json()
    enabled = data.get("enabled")

    # Only update provided fields
    if enabled is not None:
        r.enabled = bool(enabled)

    db.session.commit()
    return jsonify({
        "id": r.id,
        "enabled": r.enabled,
        "msg": "rule updated"
    }), 200
