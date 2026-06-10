"""Audit hardening: raw MongoDB queries merged into constructed queries
must not be able to execute server-side JavaScript."""

import pytest

from dserver_dependency_graph_plugin.utils import _dict_to_mongo_query


def test_benign_raw_query_is_merged():
    query = _dict_to_mongo_query({
        "base_uris": ["s3://bucket"],
        "query": {"readme.project": "test"},
    })
    assert "readme.project" in str(query)


@pytest.mark.parametrize("malicious", [
    {"$where": "sleep(10000)"},
    {"$expr": {"$function": {"body": "function(){}", "args": [],
                             "lang": "js"}}},
    {"nested": {"$where": "this.a == 1"}},
    {"$or": [{"a": 1}, {"$where": "true"}]},
    {"group": {"$accumulator": {"init": "function(){}"}}},
])
def test_javascript_operators_rejected(malicious):
    with pytest.raises(ValueError):
        _dict_to_mongo_query({
            "base_uris": ["s3://bucket"],
            "query": malicious,
        })
