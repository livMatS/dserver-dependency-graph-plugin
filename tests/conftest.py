import random
import string
import os
import sys
import yaml

import pytest

JWT_PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8LrEp0Q6l1WPsY32uOPqEjaisQScnzO/XvlhQTzj5w+hFObjiNgIaHRceYh3hZZwsRsHIkCxOY0JgUPeFP9IVXso0VptIjCPRF5yrV/+dF1rtl4eyYj/XOBvSDzbQQwqdjhHffw0TXW0f/yjGGJCYM+tw/9dmj9VilAMNTx1H76uPKUo4M3vLBQLo2tj7z1jlh4Jlw5hKBRcWQWbpWP95p71Db6gSpqReDYbx57BW19APMVketUYsXfXTztM/HWz35J9HDya3ID0Dl+pE22Wo8SZo2+ULKu/4OYVcD8DjF15WwXrcuFDypX132j+LUWOVWxCs5hdMybSDwF3ZhVBH ec2-user@ip-172-31-41-191.eu-west-1.compute.internal"  # NOQA

snowwhite_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYyMTEwMDgzMywianRpIjoiNmE3Yjk5NDYtNzU5My00OGNmLTg2NmUtMWJjZGIzNjYxNTVjIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InNub3ctd2hpdGUiLCJuYmYiOjE2MjExMDA4MzN9.gXdQpGnHDdOHTMG5OKJwNe8JoJU7JSGYooU5d8AxA_Vs8StKBBRKZJ6C6zS8SovIgcDEYGP12V25ZOF_fa42GuQErKqfwJ_RTLB8nHvfEJule9dl_4z-8-5dZigm3ieiYPpX8MktHq4FQ5vdQ36igWyTO5sK4X4GSvZjG6BRphM52Rb9J2aclO1lxuD_HV_c_rtIXI-SLxH3O6LLts8RdjqLJZBNhAPD4qjAbg_IDi8B0rh_I0R42Ou6J_Sj2s5sL97FEY5Jile0MSvBH7OGmXjlcvYneFpPLnfLwhsYUrzqYB-fdhH9AZVBwzs3jT4HGeL0bO0aBJ9sJ8YRU7sjTg"  # NOQA
@pytest.fixture
def snowwhite_token():
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYyMTEwMDgzMywianRpIjoiNmE3Yjk5NDYtNzU5My00OGNmLTg2NmUtMWJjZGIzNjYxNTVjIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InNub3ctd2hpdGUiLCJuYmYiOjE2MjExMDA4MzN9.gXdQpGnHDdOHTMG5OKJwNe8JoJU7JSGYooU5d8AxA_Vs8StKBBRKZJ6C6zS8SovIgcDEYGP12V25ZOF_fa42GuQErKqfwJ_RTLB8nHvfEJule9dl_4z-8-5dZigm3ieiYPpX8MktHq4FQ5vdQ36igWyTO5sK4X4GSvZjG6BRphM52Rb9J2aclO1lxuD_HV_c_rtIXI-SLxH3O6LLts8RdjqLJZBNhAPD4qjAbg_IDi8B0rh_I0R42Ou6J_Sj2s5sL97FEY5Jile0MSvBH7OGmXjlcvYneFpPLnfLwhsYUrzqYB-fdhH9AZVBwzs3jT4HGeL0bO0aBJ9sJ8YRU7sjTg"  # NOQA

@pytest.fixture
def grumpy_token():
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYyMTEwMTY0NywianRpIjoiYWFmMTc3NTQtNzc4Mi00ODAzLThlZDItODZhYmI0ZDVhYThlIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImdydW1weSIsIm5iZiI6MTYyMTEwMTY0N30.tvYTnOflEGjPM1AmDMQxE-2CAa7Je3uhq5DEQutUUGyuMHyT7phsam8l0aHGQjlCZb2X98Gs9QeQ5rXwxP5y8oteQzk26QbunW3Jpg46E1PheESURqOScLgyyiKa6aHtztb5aa5VxK2LgFB13JrQZ03GJpuDPQj7q1Lbu2Cn0JjX3YXRuF14ZkZk8ZrybnKsJ3RLKup_SUDeDx20hJFYBbnyd8jZSd5xV9eQfSrMHFhDBAnV9c8gzMXKnNR5OtVLyFWVrOB4OsP3Woy2eyXmM9G3Qljft6j_jtYcra7-7BnvIZE8JSLcTT0cH563KISFNqMxmkrWqhZaHRCRRhwsPg"  # NOQA

TESTING_FAMILY = {
    'grandfather': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e040"
    },
    'grandmother': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e041",
        'derived_from': ["a2218059-5bd0-4690-b090-062faf08e039"]  # not in set
    },
    'mother': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e042",
        'derived_from': ['grandfather', 'grandmother'],
    },
    'father': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e043",
        'derived_from': ['unknown'],  # invalid
    },
    'brother': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e044",
        'derived_from': ['mother', 'father'],
    },
    'sister': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e045",
        'derived_from': ['mother', 'father'],
    },
    'stepsister': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e046",
        'derived_from': ['mother', 'ex-husband'],
    },
    'ex-husband': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e047",
        'derived_from': ['unknown'],  # invalid
    },
    'friend': {
        'uuid': "a2218059-5bd0-4690-b090-062faf08e048",
        "verived_from": ["friend's mother, friend's father"]
    }
}


TESTING_FAMILY_DEPENDENCIES = [
    {'derived_from': [
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e042'},
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e043'}],
     'name': 'brother',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e044'},
    {'derived_from': [{'uuid': 'unknown'}],
     'name': 'ex-husband',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e047'},
    {'derived_from': [{'uuid': 'unknown'}],
     'name': 'father',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e043'},
    {'name': 'grandfather',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e040'},
    {'derived_from': [{'uuid': 'a2218059-5bd0-4690-b090-062faf08e039'}],
     'name': 'grandmother',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e041'},
    {'derived_from': [
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e040'},
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e041'}],
     'name': 'mother',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e042'},
    {'derived_from': [
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e042'},
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e043'}],
     'name': 'sister',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e045'},
    {'derived_from': [
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e042'},
        {'uuid': 'a2218059-5bd0-4690-b090-062faf08e047'}],
     'name': 'stepsister',
     'uuid': 'a2218059-5bd0-4690-b090-062faf08e046'},
]

BASE_URI = "s3://snow-white"


@pytest.fixture
def testing_family():
    return TESTING_FAMILY


@pytest.fixture
def testing_family_dependencies():
    return TESTING_FAMILY_DEPENDENCIES


def family_datasets(base_uri=BASE_URI):
    return [
        {
            "base_uri": base_uri,
            "type": "dataset",
            "uuid": family_tree_entry['uuid'],
            "uri": "{}/{}".format(base_uri, family_tree_entry['uuid']),
            "name": role,
            "readme": yaml.dump({
                                    "derived_from": [
                                        {"uuid": TESTING_FAMILY[parent]["uuid"] if parent in TESTING_FAMILY else parent}
                                        for parent in family_tree_entry["derived_from"]
                                    ]
                                } if "derived_from" in family_tree_entry else {}),
            "creator_username": "god",
            "frozen_at": 1536238185.881941,
            "manifest": {
                "dtoolcore_version": "3.7.0",
                "hash_function": "md5sum_hexdigest",
                "items": {}
            },
            "annotations": {"type": "member of the family"},
            "tags": ["person"],
        } for role, family_tree_entry in TESTING_FAMILY.items()
    ]


def random_string(
        size=9,
        prefix="test_",
        chars=string.ascii_uppercase + string.ascii_lowercase + string.digits
):
    return prefix + ''.join(random.choice(chars) for _ in range(size))


@pytest.fixture
def tmp_app_with_users(request):
    from flask import current_app
    from dservercore import create_app, sql_db
    from dservercore.utils import (
        register_users,
        register_base_uri,
        register_permissions,
    )

    tmp_mongo_db_name = random_string()

    config = {
        "API_TITLE": 'dserver API',
        "API_VERSION": 'v1',
        "OPENAPI_VERSION": '3.0.2',
        "SECRET_KEY": "secret",
        "FLASK_ENV": "development",
        "CONFIG_SECRETS_TO_OBFUSCATE": [],
        "ENABLE_DEPENDENCY_VIEW": True,
        "MONGO_DEPENDENCY_VIEW_PREFIX": "dep:",
        "MONGO_DEPENDENCY_VIEW_BOOKKEEPING": "dep_views",
        "MONGO_DEPENDENCY_VIEW_CACHE_SIZE": 10,
        "FORCE_REBUILD_DEPENDENCY_VIEW": False,
        "DEPENDENCY_KEYS": [
            'readme_parsed.derived_from.uuid',
            'annotations.source_dataset_uuid'
        ],
        "DYNAMIC_DEPENDENCY_KEYS": True,
        "RETRIEVE_MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "RETRIEVE_MONGO_DB": tmp_mongo_db_name,
        "RETRIEVE_MONGO_COLLECTION": "datasets",
        "SEARCH_MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "SEARCH_MONGO_DB": tmp_mongo_db_name,
        "SEARCH_MONGO_COLLECTION": "datasets",
        "MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "MONGO_DB": tmp_mongo_db_name,
        "MONGO_COLLECTION": "datasets",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_ALGORITHM": "RS256",
        "JWT_PUBLIC_KEY": JWT_PUBLIC_KEY,
        "JWT_TOKEN_LOCATION": "headers",
        "JWT_HEADER_NAME": "Authorization",
        "JWT_HEADER_TYPE": "Bearer",
    }

    app = create_app(config)

    # Ensure the sql database has been put into the context.
    app.app_context().push()

    # Populate the database.
    sql_db.Model.metadata.create_all(sql_db.engine)

    # Register some users.
    register_users([
        dict(username="snow-white", is_admin=True),
        dict(username="grumpy"),
        dict(username="sleepy"),
    ])

    base_uri = "s3://snow-white"
    register_base_uri(base_uri)

    permissions = {
        "base_uri": base_uri,
        "users_with_search_permissions": ["grumpy", "sleepy"],
        "users_with_register_permissions": ["grumpy"]
    }
    register_permissions(base_uri, permissions)

    @request.addfinalizer
    def teardown():
        current_app.retrieve.client.drop_database(tmp_mongo_db_name)
        current_app.search.client.drop_database(tmp_mongo_db_name)
        sql_db.session.remove()

    return app.test_client()


@pytest.fixture
def tmp_app_with_dependent_data(request):
    from flask import current_app
    from dservercore.config import Config
    from dservercore import create_app, sql_db
    from dservercore.utils import (
        register_users,
        register_base_uri,
        register_dataset,
        register_permissions,
    )

    tmp_mongo_db_name = random_string()

    config = {
        "API_TITLE": 'dserver API',
        "API_VERSION": 'v1',
        "OPENAPI_VERSION": '3.0.2',
        "FLASK_ENV": "development",
        "CONFIG_SECRETS_TO_OBFUSCATE": [],
        "RETRIEVE_MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "RETRIEVE_MONGO_DB": tmp_mongo_db_name,
        "RETRIEVE_MONGO_COLLECTION": "datasets",
        "SEARCH_MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "SEARCH_MONGO_DB": tmp_mongo_db_name,
        "SEARCH_MONGO_COLLECTION": "datasets",
        "MONGO_URI": os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017/"),
        "MONGO_DB": tmp_mongo_db_name,
        "MONGO_COLLECTION": "datasets",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_ALGORITHM": "RS256",
        "JWT_PUBLIC_KEY": JWT_PUBLIC_KEY,
        "JWT_TOKEN_LOCATION": "headers",
        "JWT_HEADER_NAME": "Authorization",
        "JWT_HEADER_TYPE": "Bearer",
    }

    app = create_app(config)

    # Ensure the sql database has been put into the context.
    app.app_context().push()

    # Populate the database.
    sql_db.Model.metadata.create_all(sql_db.engine)

    # Register some users.
    username = "grumpy"
    register_users([
        dict(username=username),
    ])

    base_uri = "s3://snow-white"
    register_base_uri(base_uri)
    permissions = {
        "base_uri": base_uri,
        "users_with_search_permissions": [username],
        "users_with_register_permissions": [username]
    }
    register_permissions(base_uri, permissions)

    for dataset_info in family_datasets(base_uri):
        register_dataset(dataset_info)

    @request.addfinalizer
    def teardown():
        current_app.retrieve.client.drop_database(tmp_mongo_db_name)
        current_app.search.client.drop_database(tmp_mongo_db_name)
        sql_db.session.remove()

    return app.test_client()
