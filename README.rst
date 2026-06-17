dserver Dependency Graph Plugin
===============================

.. |dtool| image:: https://github.com/livMatS/dserver-dependency-graph-plugin/blob/main/icons/22x22/dtool_logo.png?raw=True
    :height: 20px
    :target: https://github.com/livMatS/dserver-dependency-graph-plugin
.. |pypi| image:: https://img.shields.io/pypi/v/dserver-dependency-graph-plugin
    :target: https://pypi.org/project/dserver-dependency-graph-plugin/
.. |tag| image:: https://img.shields.io/github/v/tag/livMatS/dserver-dependency-graph-plugin
    :target: https://github.com/livMatS/dserver-dependency-graph-plugin/tags
.. |test| image:: https://img.shields.io/github/actions/workflow/status/livMatS/dserver-dependency-graph-plugin/test.yml?branch=main&label=tests
    :target: https://github.com/livMatS/dserver-dependency-graph-plugin/actions/workflows/test.yml
.. |zenodo| image:: https://zenodo.org/badge/298694291.svg
    :target: https://zenodo.org/doi/10.5281/zenodo.12702000

|dtool| |pypi| |tag| |test| |zenodo|

- GitHub: https://github.com/livMatS/dserver-dependency-graph-plugin
- PyPI: https://pypi.python.org/pypi/dserver-dependency-graph-plugin
- Free software: MIT License


Features
--------

- Use a dataset UUID to lookup all datasets within the same dependency graph
- Build views on dataset dependency trees based on arbitrary connecting keys


Introduction
------------

`dtool <https://dtool.readthedocs.io>`_ is a command line tool for packaging
data and metadata into a dataset. A dtool dataset manages data and metadata
without the need for a central database.

However, if one has to manage more than a hundred datasets it can be helpful
to have the datasets' metadata stored in a central server to enable one to
quickly find datasets of interest.

The `dservercore <https://github.com/jic-dtool/dservercore>`_
provides a web API for registering datasets' metadata
and provides functionality to lookup, list and search for datasets.

This plugin enables the dserver to directly provide all
datasets within a specific dependency graph.


Installation
------------

Install the dserver dependency graph plugin

.. code-block:: bash

    $ pip install dserver-dependency-graph-plugin

Setup and configuration
-----------------------

Configure plugin behavior
^^^^^^^^^^^^^^^^^^^^^^^^^

With

.. code-block:: bash

    export DSERVER_ENABLE_DEPENDENCY_VIEW=True

the underlying database will offer a view on the default collection.
This view offers an on-the-fly-generated collection of undirected per-dataset
adjacency lists in order to facilitate searching dataset dependeny graphs
in both directions. With

.. code-block:: bash

    export DSERVER_FORCE_REBUILD_DEPENDENCY_VIEW=True

this view is reestablished at every query. This is required to apply changes to
related options, such as the JSON-formatted list

.. code-block:: bash

    export DSERVER_DEPENDENCY_KEYS='["readme.derived_from.uuid", "annotations.source_dataset_uuid"]'

which indicates at which keys to look for source dataset(s) by UUID. The example
above illustrates the default. All keys are treated equivalently and nested
fields are separated by the dot (.). The actual nesting hierarchy does not
matter. This means, for example, both structures evaluate equivalently in the
following

.. code-block:: python

    {'readme': {'derived_from': {'uuid':
        ['8ecd8e05-558a-48e2-b563-0c9ea273e71e',
         'faa44606-cb86-4877-b9ea-643a3777e021']}}}

    {'readme': {'derived_from':
        [{'uuid': '8ecd8e05-558a-48e2-b563-0c9ea273e71e'},
         {'uuid': 'faa44606-cb86-4877-b9ea-643a3777e021'}]}}


Setting

.. code-block:: bash

     export DSERVER_DYNAMIC_DEPENDENCY_KEYS=True

will allow the client side to request graphs spanned by arbitrary dependency
keys (see below). The related options

.. code-block:: bash

    export DSERVER_MONGO_DEPENDENCY_VIEW_PREFIX=dep
    export DSERVER_MONGO_DEPENDENCY_VIEW_BOOKKEEPING=dep_views
    export DSERVER_MONGO_DEPENDENCY_VIEW_CACHE_SIZE=10

control internal behavior. See source code and examples below.

Note that the above exports containing JSON syntax are formatted for usage in
bash. Enclosing single quotes are not to be part of the actual variable value
when environment variables are configured elsewhere.


dserver API
-----------

dserver makes use of the Authorized header to pass through the
JSON web token for authorization. Below we create environment variables for the
token and the header used in the ``curl`` commands

.. code-block:: bash

  $ TOKEN=$(flask user token olssont)
  $ HEADER="Authorization: Bearer $TOKEN"


Standard user usage
^^^^^^^^^^^^^^^^^^^

Looking up dependency graphs based on a dataset's UUID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A dataset can be derived from one or several source datasets, usually
by machine-generated annotations attached via the Python API at dataset
creation time, or manually by recording the UUIDs of parent datasets in some
arbitrary fields within the README.yml. If configured appropriately,
querying the server directly for all datasets within the same dependency
graph by UUID is possible, i.e.

.. code-block:: bash

    $ UUID=41a2e3e2-0c01-444f-bd7d-f9bb45512373
    $ curl -H "$HEADER" http://localhost:5000/graph/uuids/$UUID

Looking up a dependency graph by UUID will result in unique per-UUID hits.
As it is possible for a dataset to be registered in more than one base
URI, the query will yield one arbitrary hit in such a case.


Looking up graphs spanned by arbitrary dependency keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If ``DSERVER_DYNAMIC_DEPENDENCY_KEYS=True``, then the client may
ask the server to explore a graph spanned by dependency keys differing from
the server-side defaults in ``DSERVER_DEPENDENCY_KEYS``. This
happens as above, but with via a ``POST`` request with a JSON-formatted list
of desired dependency keys attached

.. code-block:: bash

    $ curl -H "$HEADER" -H "Content-Type: application/json"  \
        -X POST -d  \
        '["annotations.source_dataset_uuid","readme.derived_from.uuid"]'
        http://localhost:5000/graph/uuids/$UUID

If a view for this particular set of keys does not exist yet, the server will
generate and cache it on-the-fly. This can be observed in the mongo shell

.. code-block:: bash

    $ mongo

    > show dbs
    admin       0.000GB
    config      0.000GB
    dtool_info  0.020GB
    local       0.000GB

    > use dtool_info
    switched to db dtool_info

    > show collections
    datasets
    dep:2020-10-05T01:22:39.581592
    dep:2020-10-06T21:45:00.525410
    dep:2020-10-06T21:45:28.495903
    dep_views
    dependencies
    system.views

Here, all ``dep``-prefixed collections are dependency views for distinct sets
of keys. The bookkeeping collection``dep_views`` holds records of all
dependency view - key set mappings together with the latest access

.. code-block:: js

    > db.dep_views.find()
    { "_id" : ObjectId("5f7a755faea9fcf239f68dba"), "name" : "dep:2020-10-05T01:22:39.581592", "keys" : [ "annotations.source_dataset_uuid", "readme.derived_from.uuid" ], "accessed_on" : ISODate("2020-10-07T12:24:32.724Z") }
    { "_id" : ObjectId("5f7ce55caea9fcf239f68dbb"), "name" : "dep:2020-10-06T21:45:00.525410", "keys" : [ "readme.derived_from.uuid" ], "accessed_on" : ISODate("2020-10-06T21:45:00.538Z") }
    { "_id" : ObjectId("5f7ce578aea9fcf239f68dbc"), "name" : "dep:2020-10-06T21:45:28.495903", "keys" : [ "bla" ], "accessed_on" : ISODate("2020-10-06T21:45:28.498Z") }

and querying with a specific set of keys for the first time

.. code-block:: bash

    $ curl -H "$HEADER" -H "Content-Type: application/json"  \
        -X POST -d  \
        '["another.possibly_nested.dependency_key"]'  \
        http://localhost:5000/graph/uuids/$UUID

will result in an additional view named uniquely by the current UTC time::

    > show collections
    datasets
    dep:2020-10-05T01:22:39.581592
    dep:2020-10-06T21:45:00.525410
    dep:2020-10-06T21:45:28.495903
    dep:2020-10-07T17:03:58.831223
    dep_views
    dependencies
    system.views

and an according entry within ``dep_views``

.. code-block:: js

    > db.dep_views.find()
    { "_id" : ObjectId("5f7a755faea9fcf239f68dba"), "name" : "dep:2020-10-05T01:22:39.581592", "keys" : [ "annotations.source_dataset_uuid", "readme.derived_from.uuid" ], "accessed_on" : ISODate("2020-10-07T16:59:12.467Z") }
    { "_id" : ObjectId("5f7ce55caea9fcf239f68dbb"), "name" : "dep:2020-10-06T21:45:00.525410", "keys" : [ "readme.derived_from.uuid" ], "accessed_on" : ISODate("2020-10-06T21:45:00.538Z") }
    { "_id" : ObjectId("5f7ce578aea9fcf239f68dbc"), "name" : "dep:2020-10-06T21:45:28.495903", "keys" : [ "bla" ], "accessed_on" : ISODate("2020-10-06T21:45:28.498Z") }
    { "_id" : ObjectId("5f7df4feaea9fcf239f68dbd"), "name" : "dep:2020-10-07T17:03:58.831223", "keys" : [ "another.possibly_nested.dependency_key" ], "accessed_on" : ISODate("2020-10-07T17:03:58.833Z") }

If the total number of such cached views exceeds the allowed maximum value
configured in ``DSERVER_MONGO_DEPENDENCY_VIEW_CACHE_SIZE``, then
the view accessed least recently is dropped.