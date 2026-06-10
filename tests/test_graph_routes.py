"""Test the dependency graph querying."""

import json

from . import compare_marked_nested, comparison_marker_from_obj


def test_query_dependency_graph_by_default_keys(tmp_app_with_dependent_data, testing_family, grumpy_token):  # NOQA

    headers = dict(Authorization="Bearer " + grumpy_token)

    uuid = "a2218059-5bd0-4690-b090-062faf08e044"  # brother

    r = tmp_app_with_dependent_data.get(
        "/graph/uuids/{}".format(uuid),
        headers=headers,
    )
    assert r.status_code == 200
    response = json.loads(r.data.decode("utf-8"))

    expected_response = []
    for role, p in testing_family.items():
        if role == 'friend':
            continue  # skip unrelated family friend

        r = tmp_app_with_dependent_data.get(
            "/uuids/{}".format(p['uuid']),
            headers=headers,
        )
        assert r.status_code == 200
        ref_response = json.loads(r.data.decode("utf-8"))
        expected_response.extend(ref_response)

    expected_response = sorted(expected_response, key=lambda s: s['uuid'])

    marker = comparison_marker_from_obj(expected_response)
    # exclude fields not to compare
    for m in marker:
        m['created_at'] = False
        m['frozen_at'] = False
        m['size_in_bytes'] = False
        m['number_of_items'] = False

    assert compare_marked_nested(response, expected_response, marker)


def test_query_dependency_graph_by_custom_keys(tmp_app_with_dependent_data, testing_family, grumpy_token):  # NOQA

    headers = dict(Authorization="Bearer " + grumpy_token)

    uuid = "a2218059-5bd0-4690-b090-062faf08e044"  # brother

    dependency_keys = ["readme_parsed.derived_from.uuid", "some_nonexistant_key"]

    r = tmp_app_with_dependent_data.post(
        "/graph/uuids/{}".format(uuid),
        headers=headers,
        data=json.dumps({"dependency_keys": dependency_keys}),
        content_type="application/json"
    )
    assert r.status_code == 200
    response = json.loads(r.data.decode("utf-8"))

    expected_response = []
    for role, p in testing_family.items():
        if role == 'friend':
            continue  # skip unrelated family friend

        r = tmp_app_with_dependent_data.get(
            "/uuids/{}".format(p['uuid']),
            headers=headers,
        )
        assert r.status_code == 200
        ref_response = json.loads(r.data.decode("utf-8"))
        expected_response.extend(ref_response)

    expected_response = sorted(expected_response, key=lambda s: s['uuid'])

    marker = comparison_marker_from_obj(expected_response)
    # exclude fields not to compare
    for m in marker:
        m['created_at'] = False
        m['frozen_at'] = False
        m['size_in_bytes'] = False
        m['number_of_items'] = False

    assert compare_marked_nested(response, expected_response, marker)


def test_query_dependency_graph_by_custom_nonexistant_keys(tmp_app_with_dependent_data, testing_family, grumpy_token):  # NOQA

    headers = dict(Authorization="Bearer " + grumpy_token)

    uuid = "a2218059-5bd0-4690-b090-062faf08e044"  # brother

    dependency_keys = ["some_nonexistant_key"]

    r = tmp_app_with_dependent_data.post(
        "/graph/uuids/{}".format(uuid),
        headers=headers,
        data=json.dumps({"dependency_keys": dependency_keys}),
        content_type="application/json"
    )
    assert r.status_code == 200
    response = json.loads(r.data.decode("utf-8"))

    expected_response = []
    for role, p in testing_family.items():
        if role != 'brother':
            continue  # skip unrelated family friend

        r = tmp_app_with_dependent_data.get(
            "/uuids/{}".format(p['uuid']),
            headers=headers,
        )
        assert r.status_code == 200
        ref_response = json.loads(r.data.decode("utf-8"))
        expected_response.extend(ref_response)

    expected_response = sorted(expected_response, key=lambda s: s['uuid'])

    marker = comparison_marker_from_obj(expected_response)
    # exclude fields not to compare
    for m in marker:
        m['created_at'] = False
        m['frozen_at'] = False
        m['size_in_bytes'] = False
        m['number_of_items'] = False

    assert compare_marked_nested(response, expected_response, marker)


def test_generate_many_dependency_views(tmp_app_with_dependent_data, testing_family, grumpy_token):  # NOQA

    headers = dict(Authorization="Bearer " + grumpy_token)

    uuid = "a2218059-5bd0-4690-b090-062faf08e044"  # brother

    dependency_keys_list = [
        ["readme_parsed.derived_from.uuid", "some_nonexistant_key_{}".format(i)] for i in range(12)]

    expected_response = []
    for role, p in testing_family.items():
        if role == 'friend':
            continue  # skip unrelated family friend

        r = tmp_app_with_dependent_data.get(
            "/uuids/{}".format(p['uuid']),
            headers=headers,
        )
        assert r.status_code == 200
        ref_response = json.loads(r.data.decode("utf-8"))
        expected_response.extend(ref_response)

    expected_response = sorted(expected_response, key=lambda s: s['uuid'])

    marker = comparison_marker_from_obj(expected_response)
    # exclude fields not to compare
    for m in marker:
        m['created_at'] = False
        m['frozen_at'] = False
        m['size_in_bytes'] = False
        m['number_of_items'] = False

    for dependency_keys in dependency_keys_list:
        r = tmp_app_with_dependent_data.post(
            "/graph/uuids/{}".format(uuid),
            headers=headers,
            data=json.dumps({"dependency_keys": dependency_keys}),
            content_type="application/json"
        )
        assert r.status_code == 200
        response = json.loads(r.data.decode("utf-8"))
        assert compare_marked_nested(response, expected_response, marker)
