from flask import Blueprint, request, jsonify
from ..models import db, Farm
from flask_jwt_extended import jwt_required, get_jwt_identity

bp = Blueprint("farms", __name__)

@bp.route("/", methods=["POST"])
@jwt_required()
def create_farm():
    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"msg": "name required"}), 400

    # get_jwt_identity() returns the user_id as a STRING now
    owner_id = int(get_jwt_identity())

    f = Farm(name=name, owner_id=owner_id)
    db.session.add(f)
    db.session.commit()

    return jsonify({"id": f.id, "name": f.name, "owner_id": owner_id}), 201


@bp.route("/", methods=["GET"])
@jwt_required()
def list_farms():
    owner_id = int(get_jwt_identity())

    farms = Farm.query.filter_by(owner_id=owner_id).all()
    out = [{"id": f.id, "name": f.name, "owner_id": f.owner_id} for f in farms]

    return jsonify(out), 200
