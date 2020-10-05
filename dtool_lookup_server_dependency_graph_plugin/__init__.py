from flask import (
    abort,
    Blueprint,
    jsonify,
    request
)
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)
from dtool_lookup_server import AuthenticationError

from .utils import (
    dependency_graph_by_user_and_uuid,
    config_to_dict,
)


__version__ = '0.1.0'

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


@graph_bp.route("/lookup/<uuid>", methods=["GET"])
@jwt_required
def lookup_dependency_graph_by_default_keys(uuid):
    """List the datasets within the same dependency graph as <uuid>.
    If not all datasets are accessible by the user, an incomplete, disconnected
    graph may arise."""
    username = get_jwt_identity()
    try:
        datasets = dependency_graph_by_user_and_uuid(username, uuid)
    except AuthenticationError:
        abort(401)
    return jsonify(datasets)


@graph_bp.route("/lookup/<uuid>", methods=["POST"])
@jwt_required
def lookup_dependency_graph_by_custom_keys(uuid):
    """List the datasets within the same dependency graph as <uuid>.
    If not all datasets are accessible by the user, an incomplete, disconnected
    graph may arise."""
    username = get_jwt_identity()
    dependency_keys = request.get_json()
    try:
        datasets = dependency_graph_by_user_and_uuid(username, uuid, dependency_keys)
    except AuthenticationError:
        abort(401)
    return jsonify(datasets)


@graph_bp.route("/config", methods=["GET"])
@jwt_required
def plugin_config():
    """Return the JSON-serialized dependency graph plugin configuration."""
    username = get_jwt_identity()
    try:
        config = config_to_dict(username)
    except AuthenticationError:
        abort(401)
    return jsonify(config)
