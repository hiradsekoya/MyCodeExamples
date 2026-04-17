from flask import Blueprint, request, jsonify
from ..models import db, Zone, Farm
from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("zones", __name__)

@bp.route("/", methods=["POST"])
@jwt_required()
def create_zone():
    data = request.get_json()
    name = data.get("name")
    farm_id = data.get("farm_id")

    if not name or not farm_id:
        return jsonify({"msg": "name and farm_id required"}), 400

    # Identity is user_id (string)
    owner_id = int(get_jwt_identity())

    # Check that the farm belongs to this user
    farm = Farm.query.filter_by(id=farm_id, owner_id=owner_id).first()
    if not farm:
        return jsonify({"msg": "farm not found or not owned by you"}), 404

    z = Zone(name=name, farm_id=farm_id)
    db.session.add(z)
    db.session.commit()

    return jsonify({"id": z.id, "name": z.name, "farm_id": z.farm_id}), 201


@bp.route("/", methods=["GET"])
@jwt_required()
def list_zones():
    owner_id = int(get_jwt_identity())

    zones = (
        Zone.query.join(Farm, Farm.id == Zone.farm_id)
        .filter(Farm.owner_id == owner_id)
        .all()
    )

    out = [{
        "id": z.id,
        "name": z.name,
        "farm_id": z.farm_id,
        "twin_state": z.twin_state
    } for z in zones]

    return jsonify(out), 200


@bp.route("/<int:zone_id>", methods=["GET"])
@jwt_required()
def get_zone(zone_id):
    owner_id = int(get_jwt_identity())

    zone = (
        Zone.query.join(Farm, Farm.id == Zone.farm_id)
        .filter(Zone.id == zone_id, Farm.owner_id == owner_id)
        .first()
    )

    if not zone:
        return jsonify({"msg": "zone not found"}), 404

    return jsonify({
        "id": zone.id,
        "name": zone.name,
        "farm_id": zone.farm_id,
        "twin_state": zone.twin_state
    }), 200
