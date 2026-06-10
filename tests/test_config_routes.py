"""Test the /scaffolding/config blueprint route."""

import json

"""Test the /config blueprint route."""

import json

from . import compare_marked_nested, comparison_marker_from_obj



def test_config_info_route(tmp_app_with_users, snowwhite_token):  # NOQA

    headers = dict(Authorization="Bearer " + snowwhite_token)
    r = tmp_app_with_users.get(
        "/config/info",
        headers=headers,
    )
    assert r.status_code == 200

    expected_response = {
        'dependency_keys': ['readme_parsed.derived_from.uuid',
                            'annotations.source_dataset_uuid'],
        'dynamic_dependency_keys': True,
        'enable_dependency_view': True,
        'force_rebuild_dependency_view': False,
        'mongo_dependency_view_bookkeeping': 'dep_views',
        'mongo_dependency_view_cache_size': 10,
        'mongo_dependency_view_prefix': 'dep:',
    }

    response = json.loads(r.data.decode("utf-8"))['config']

    marker = comparison_marker_from_obj(expected_response)
    assert compare_marked_nested(response, expected_response, marker)