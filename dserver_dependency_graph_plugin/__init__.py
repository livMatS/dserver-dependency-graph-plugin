try:
    from importlib.metadata import version, PackageNotFoundError
except ModuleNotFoundError:
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
   pass

import datetime
import logging
import pymongo

import dtoolcore.utils

from flask import (
    abort,
    current_app,
    jsonify,
    request
)
from dservercore.utils_auth import (
    jwt_required,
    get_jwt_identity,
)
from flask_smorest import Blueprint
from flask_smorest.pagination import PaginationParameters

from pymongo import MongoClient

from dservercore import AuthenticationError, ExtensionABC
from dservercore.sql_models import DatasetSchema
from dservercore.utils import _preprocess_privileges
from dserver_direct_mongo_plugin.utils import _dict_to_mongo_query

from .schemas import DependencyKeysSchema

from .graph import (
    query_dependency_graph,
    build_undirected_adjecency_lists,
)
from .config import Config, CONFIG_SECRETS_TO_OBFUSCATE


graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


logger = logging.getLogger(__name__)


def _list_to_collection_name(ls, prefix=Config.MONGO_DEPENDENCY_VIEW_PREFIX):
    """Convert a list of str to a unique, valid mongo collection name.

    See https://docs.mongodb.com/manual/reference/limits/#Restriction-on-Collection-Names."""
    if not isinstance(ls, list) and not isinstance(ls, str):
        raise ValueError('Type of ls must be list or str, but type({}) is {}.'.format(ls, type(ls)))
    if isinstance(ls, str):
        ls = [ls]
    for l in ls:
        if not isinstance(l, str):
            raise ValueError('Type of all elements of ls must be str, but type({}) is {}.'.format(l, type(l)))
        if l.find('$') != -1:
            raise ValueError('No dollar char ($) allowed in collection name.')

    coll_name = prefix + ','.join(ls)
    coll_namespace = DependencyGraphExtension.db.name + '.' + coll_name
    if len(coll_namespace) > 255:
        raise ValueError('Maximum namespace length is 255, but len("{}") == {}.'.format(coll_namespace,
                                                                                        len(coll_namespace)))
    return coll_name


def _assert_list_of_mongo_keys(ls):
    """Assert argument is list of valid mongo collection keys."""
    if not isinstance(ls, list) and not isinstance(ls, str):
        raise ValueError('Type of ls must be list or str, but type({}) is {}.'.format(ls, type(ls)))
    if isinstance(ls, str):
        ls = [ls]
    for l in ls:
        if not isinstance(l, str):
            raise ValueError('Type of all elements of ls must be str, but type({}) is {}.'.format(l, type(l)))
        if l.find('$') != -1:
            raise ValueError('No dollar char ($) allowed.')
    ls = list(sorted(ls))
    if list(sorted(list(set(ls)))) != ls:
        raise ValueError('Elements must be unique.')
    return ls


def _list_collection_names(prefix=Config.MONGO_DEPENDENCY_VIEW_PREFIX):
    """List all collections whose name starts with prefix."""
    filter = {"name": {"$regex": "^(?!{})".format(prefix)}}
    return DependencyGraphExtension.db.list_collection_names(filter=filter)


# low-level bookkeeping record helpers

def assert_dependency_view_bookkeeping_collection(func):
    """Assure the existance of the dependency view cache bookkeeping collection."""
    def wrapper_assert_dependency_view_bookkeeping_collection(*args, **kwargs):
        if Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING not in DependencyGraphExtension.db.list_collection_names():
            DependencyGraphExtension.db.create_collection(Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING)
        return func(*args, **kwargs)
    return wrapper_assert_dependency_view_bookkeeping_collection


@assert_dependency_view_bookkeeping_collection
def _get_dependency_view_bookkeeping_record(dependency_keys):
    """Query bookkeeping record for unique set of dependency keys."""
    query = {'keys': dependency_keys}
    return DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].find_one(query)


@assert_dependency_view_bookkeeping_collection
def _create_dependency_view_bookkeeping_record(name, dependency_keys):
    ret = DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].insert_one(
        {'name': name, 'keys': dependency_keys, 'accessed_on': datetime.datetime.utcnow()})
    # drop oldest entry if number of documents exceeds allowed maximum
    count = DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].count_documents({})
    if count > Config.MONGO_DEPENDENCY_VIEW_CACHE_SIZE:
        # get least recently accessed view and drop
        to_drop = DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].find_one(sort=[('accessed_on', pymongo.ASCENDING)])
        logger.warning("Maximum dependency view cache size %s exceeded by %s. "
                       "Dropping least recently accessed view '%s': %s (%s)." % (
                            Config.MONGO_DEPENDENCY_VIEW_CACHE_SIZE, count,
                            to_drop["name"], to_drop["keys"], to_drop["accessed_on"]))
        DependencyGraphExtension.db[to_drop["name"]].drop()
        DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].delete_one(to_drop)
    return ret


@assert_dependency_view_bookkeeping_collection
def _update_dependency_view_bookkeeping_record(name):
    """Updated record to dependency view bookkeeping collection or add if new."""
    return DependencyGraphExtension.db[Config.MONGO_DEPENDENCY_VIEW_BOOKKEEPING].update_one(
        {'name': name}, {'$set': {'accessed_on': datetime.datetime.utcnow()}})


# mid-level dependency view helpers
def _create_dependency_view(dependency_keys):
    """Create a new view for dependency_keys and the according bookkeeping record.

    :param dependency_keys: list of str
    :returns: str"""

    # generate unique, valid name for view from prefix and ISO date string
    datestring = datetime.datetime.utcnow().isoformat()
    name = Config.MONGO_DEPENDENCY_VIEW_PREFIX + datestring

    if name in DependencyGraphExtension.db.list_collection_names():
        raise ValueError("View '%s' exists already." % name)  # must never happen

    aggregation_pipeline = build_undirected_adjecency_lists(dependency_keys)
    logger.debug("Create view '%s' with %s." % (name, aggregation_pipeline))
    DependencyGraphExtension.db.command(
        'create',
        name, viewOn=current_app.config['MONGO_COLLECTION'],
        pipeline=aggregation_pipeline)
    # raises pymongo.errors.OperationFailure
    _create_dependency_view_bookkeeping_record(name, dependency_keys)
    return name


def _get_dependency_view_from_keys(dependency_keys=Config.DEPENDENCY_KEYS):
    """Get a bidirectional dependency view on the core collection."""
    dependency_keys = _assert_list_of_mongo_keys(dependency_keys)

    dependency_view_doc = _get_dependency_view_bookkeeping_record(dependency_keys)

    # If no bookkeeping record for desired view exists, create view.
    if dependency_view_doc is None:
        dependency_view = _create_dependency_view(dependency_keys)
        return dependency_view

    dependency_view = dependency_view_doc["name"]

    # Bookkeeping record exists but view disappeared, recreate.
    if dependency_view not in DependencyGraphExtension.db.list_collection_names():
        logger.warning("Bookkeeping record for view '{}' still exists, "
                       "while view itself vanished. Recreating.".format(dependency_view))
        dependency_view = _create_dependency_view(dependency_keys)
        return dependency_view

    # View exists, but FORCE_REBUILD_DEPENDENCY_VIEW enforces recreation at every query.
    if Config.FORCE_REBUILD_DEPENDENCY_VIEW:
        logger.warning("Forced to drop exisitng view '{}'.".format(dependency_view))
        DependencyGraphExtension.db[dependency_view].drop()
        dependency_view = _create_dependency_view(dependency_keys)
        return dependency_view

    # Update accessed_on datetime.
    _update_dependency_view_bookkeeping_record(dependency_view)
    return dependency_view


def dependency_graph_by_user_and_uuid(username, uuid, dependency_keys=Config.DEPENDENCY_KEYS):
    """Aggregate all datasets within the same dependency graph as uuid.

    :param username: username
    :param uuid: UUID of dataset to start dependency graph search from
    :returns: List of dicts if user is valid and has access to datasets.
              Empty list if user is valid but has not got access to any
              datasets.
    :raises: AuthenticationError if user is invalid.
    """

    # enable undirected view on dependency graph
    if not Config.ENABLE_DEPENDENCY_VIEW:
        logger.warning(
            "Received dependency graph request from user '{}', but "
            "feature is disabled.".format(username))
        return []  # silently reject request

    # disable dynamic dependency keys
    if not Config.DYNAMIC_DEPENDENCY_KEYS and sorted(dependency_keys) != sorted(Config.DEPENDENCY_KEYS):
        logger.warning(
            "Received dependency graph request for dynamic keys '{}' from user "
            "'{}', but dynamic dependency key feature is disabled. Set env "
            "var DSERVER_DYNAMIC_DEPENDENCY_KEYS=True to enable.".format(
                dependency_keys, username))
        dependency_keys = Config.DEPENDENCY_KEYS

    dependency_view = _get_dependency_view_from_keys(dependency_keys)

    # in the pipeline, we need to filter privileges two times. Initially,
    # when looking up the specified uuid , and subsequently after building
    # the dependency graph for the hypothetical case of the user not having
    # sufficient privileges to view all datasets within the same graph.
    # Building those pre- and post-queries relies on the _dict_to_mongo_query
    # utility function and hence requires the 'uuids' keyword configured as
    # an allowed query key. This is the default configuration in config.Config.
    pre_query = _preprocess_privileges(username, {'uuids': [uuid]})
    post_query = _preprocess_privileges(username, {})

    # If there are no base URIs at this point it means that the user has not
    # got privileges to search for anything.
    if (len(pre_query["base_uris"]) == 0) or len(post_query["base_uris"]) == 0:
        return []

    pre_query = _dict_to_mongo_query(pre_query)
    post_query = _dict_to_mongo_query(post_query)

    datasets = []
    mongo_aggregation = query_dependency_graph(pre_query=pre_query,
                                               post_query=post_query,
                                               dependency_keys=dependency_keys,
                                               mongo_dependency_view=dependency_view)
    logger.debug("Constructed mongo aggregation: {}".format(mongo_aggregation))
    cx = DependencyGraphExtension.db[current_app.config['MONGO_COLLECTION']].aggregate(mongo_aggregation)

    for ds in cx:
        # Convert datetime object to float timestamp.
        for key in ("created_at", "frozen_at"):
            if key in ds:
                datetime_obj = ds[key]
                ds[key] = dtoolcore.utils.timestamp(datetime_obj)

        datasets.append(ds)

    return datasets


@graph_bp.route("/uuids/<uuid>", methods=["GET"])
@graph_bp.response(200, DatasetSchema(many=True))
@graph_bp.paginate()
@jwt_required()
def lookup_dependency_graph_by_default_keys(pagination_parameters: PaginationParameters,
                                            uuid):
    """List the datasets within the same dependency graph as <uuid>.
    If not all datasets are accessible by the user, an incomplete, disconnected
    graph may arise."""
    username = get_jwt_identity()
    try:
        datasets = dependency_graph_by_user_and_uuid(username, uuid)
    except AuthenticationError:
        abort(401)
    pagination_parameters.item_count = len(datasets)
    return jsonify(
        datasets[pagination_parameters.first_item: pagination_parameters.last_item + 1]
    )


@graph_bp.route("/uuids/<uuid>", methods=["POST"])
@graph_bp.arguments(DependencyKeysSchema(partial=True))
@graph_bp.response(200, DatasetSchema(many=True))
@graph_bp.paginate()
@jwt_required()
def lookup_dependency_graph_by_custom_keys(dependency_keys: DependencyKeysSchema,
                                           pagination_parameters: PaginationParameters,
                                           uuid):
    """List the datasets within the same dependency graph as <uuid>.
    If not all datasets are accessible by the user, an incomplete, disconnected
    graph may arise."""
    username = get_jwt_identity()
    # dependency_keys = request.get_json()
    try:
        datasets = dependency_graph_by_user_and_uuid(username, uuid, dependency_keys["dependency_keys"])
    except AuthenticationError:
        abort(401)
    pagination_parameters.item_count = len(datasets)
    return jsonify(
        datasets[pagination_parameters.first_item: pagination_parameters.last_item + 1]
    )


class DependencyGraphExtension(ExtensionABC):
    """Extensions for building and queryng dependency graphs."""

    # NOTE: Not very neat using class variables here, but the way the plugin
    # system works now, we need to provide the class-external route above some
    # means of accessing the database that's configured within the init_app
    # method here.
    client = None
    collection = None
    db = None

    def init_app(self, app):
        try:
            self._mongo_uri = app.config["MONGO_URI"]
            DependencyGraphExtension.client = MongoClient(self._mongo_uri,
                                      uuidRepresentation='standard')
        except KeyError:
            raise(RuntimeError("Please set the MONGO_URI environment variable"))  # NOQA

        try:
            self._mongo_db = app.config["MONGO_DB"]
            DependencyGraphExtension.db = self.client[self._mongo_db]
        except KeyError:
            raise(RuntimeError("Please set the MONGO_DB environment variable"))  # NOQA

        try:
            self._mongo_collection = app.config["MONGO_COLLECTION"]
            DependencyGraphExtension.collection = self.db[self._mongo_collection]
        except KeyError:
            raise(RuntimeError("Please set the MONGO_COLLECTION environment variable"))  # NOQA

    def register_dataset(self, dataset_info):
        """Does nothing, relies on dserver-direct-mongo-plugin."""
        pass

    def get_config(self):
        """Return initial Config object, available app-instance independent."""
        return Config

    def get_config_secrets_to_obfuscate(self):
        """Return config secrets never to be exposed clear text."""
        return CONFIG_SECRETS_TO_OBFUSCATE

    def get_blueprint(self):
        return graph_bp