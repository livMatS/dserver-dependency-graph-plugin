"""Utility functions for MongoDB query construction.

These functions were originally part of dserver-direct-mongo-plugin but are
copied here to decouple the dependency-graph-plugin from that package.
"""

import logging

logger = logging.getLogger(__name__)


VALID_MONGO_QUERY_KEYS = (
    "free_text",
    "creator_usernames",
    "base_uris",
    "uuids",
    "tags",
)

MONGO_QUERY_LIST_KEYS = (
    "creator_usernames",
    "base_uris",
    "uuids",
    "tags",
)


def _dict_to_mongo(query_dict):
    """Convert a query dictionary to a MongoDB query.

    :param query_dict: Dictionary with query parameters
    :returns: MongoDB query dictionary
    """
    def _sanitise(query_dict):
        for key in list(query_dict.keys()):
            if key not in VALID_MONGO_QUERY_KEYS:
                del query_dict[key]
        for lk in MONGO_QUERY_LIST_KEYS:
            if lk in query_dict:
                if len(query_dict[lk]) == 0:
                    del query_dict[lk]

    def _deal_with_possible_or_statment(a_list, key):
        if len(a_list) == 1:
            return {key: a_list[0]}
        else:
            return {"$or": [{key: v} for v in a_list]}

    def _deal_with_possible_and_statement(a_list, key):
        if len(a_list) == 1:
            return {key: a_list[0]}
        else:
            return {key: {"$all": a_list}}

    _sanitise(query_dict)

    sub_queries = []
    if "free_text" in query_dict:
        sub_queries.append({"$text": {"$search": query_dict["free_text"]}})
    if "creator_usernames" in query_dict:
        sub_queries.append(
            _deal_with_possible_or_statment(
                query_dict["creator_usernames"], "creator_username"
            )
        )
    if "base_uris" in query_dict:
        sub_queries.append(
            _deal_with_possible_or_statment(query_dict["base_uris"], "base_uri")
        )
    if "uuids" in query_dict:
        sub_queries.append(_deal_with_possible_or_statment(query_dict["uuids"], "uuid"))
    if "tags" in query_dict:
        sub_queries.append(
            _deal_with_possible_and_statement(query_dict["tags"], "tags")
        )

    if len(sub_queries) == 0:
        return {}
    elif len(sub_queries) == 1:
        return sub_queries[0]
    else:
        return {"$and": [q for q in sub_queries]}


# MongoDB operators that execute server-side JavaScript. A raw query
# containing any of these could run arbitrary code on the database server.
_FORBIDDEN_MONGO_OPERATORS = frozenset(
    ("$where", "$function", "$accumulator"))


def _assert_no_forbidden_operators(raw_mongo):
    """Recursively reject MongoDB operators that execute JavaScript.

    :raises: ValueError if a forbidden operator occurs anywhere in the query
    """
    if isinstance(raw_mongo, dict):
        for key, value in raw_mongo.items():
            if key in _FORBIDDEN_MONGO_OPERATORS:
                raise ValueError(
                    f"Operator '{key}' is not allowed in raw MongoDB queries")
            _assert_no_forbidden_operators(value)
    elif isinstance(raw_mongo, (list, tuple)):
        for item in raw_mongo:
            _assert_no_forbidden_operators(item)


def _dict_to_mongo_query(query_dict):
    """Construct mongo query, allowing embedding of a raw mongo query.

    Converts a query dictionary to a MongoDB query format. If the query_dict
    contains a 'query' key with a dict value, that raw MongoDB query is
    merged with the constructed query.

    :param query_dict: Dictionary with query parameters. May contain:
        - free_text: Text search string
        - creator_usernames: List of creator usernames
        - base_uris: List of base URIs
        - uuids: List of UUIDs
        - tags: List of tags
        - query: Raw MongoDB query dict (optional)
    :returns: MongoDB query dictionary
    :raises: ValueError if the raw query contains JavaScript-executing
             operators ($where, $function, $accumulator)
    """
    if "query" in query_dict and isinstance(query_dict["query"], dict):
        raw_mongo = query_dict["query"]
        _assert_no_forbidden_operators(raw_mongo)
        del query_dict["query"]
    else:
        raw_mongo = {}

    mongo_query = _dict_to_mongo(query_dict)

    if len(raw_mongo) > 0 and len(mongo_query) == 0:
        mongo_query = raw_mongo
    elif len(raw_mongo) > 0 and len(mongo_query) == 1 and "$and" in mongo_query:
        mongo_query["$and"].append(raw_mongo)
    elif len(raw_mongo) > 0:
        mongo_query = {"$and": [mongo_query, raw_mongo]}

    logger.debug("Constructed mongo query: {}".format(mongo_query))
    return mongo_query
