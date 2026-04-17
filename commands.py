from flask import Blueprint, request, jsonify
from ..models import db, CommandLog, Zone
from datetime import datetime

bp = Blueprint("commands", __name__)

# -------------------------------------
# POST /api/commands/send
# -------------------------------------
@bp.route("/send", methods=["POST"])
def send_command():
    """
    Logs a command to a zone.
    Example payload:
    {
        "zone_id": 1,
        "command": "pump_on"
    }
    """
    data = request.get_json()
    zone_id = data.get("zone_id")
    command = data.get("command")

    if not zone_id or not command:
        return jsonify({"msg": "zone_id and command required"}), 400

    if Zone.query.get(zone_id) is None:
        return jsonify({"msg": "zone not found"}), 404

    entry = CommandLog(zone_id=zone_id, command=command, timestamp=datetime.utcnow())
    db.session.add(entry)
    db.session.commit()

    return jsonify({
        "msg": "command logged",
        "command_id": entry.id,
        "zone_id": zone_id,
        "command": command
    }), 201
