# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A `dservercore` extension plugin that lets a [dserver](https://github.com/livMatS/dservercore)
instance answer "give me every dataset in the same dependency graph as this UUID."
It registers a Flask blueprint at `/graph` and is wired into the host server through the
`dservercore.extension` entry point (`pyproject.toml`):
`DependencyGraphExtension = "dserver_dependency_graph_plugin:DependencyGraphExtension"`.

The plugin does **not** register or own dataset metadata. It reads the dataset collection
that the search/retrieve mongo plugins populate, building MongoDB *views* on top of it.
`register_dataset` is intentionally a no-op.

## Commands

```bash
# Install with test deps (needs the sibling livMatS plugins, see test.yml for git installs)
pip install .[test]

# Run the full test suite (requires a running MongoDB)
pytest -sv

# Point tests at a non-default mongo
TEST_MONGO_URI=mongodb://localhost:27017/ pytest -sv

# Single test
pytest tests/test_graph_routes.py::test_query_dependency_graph_by_default_keys -sv

# Lint (matches CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

Tests spin up a real dserver app via `create_app` and a temporary mongo database per run
(`conftest.py`). **A MongoDB server must be reachable** — there is no mocking layer. CI
(`.github/workflows/test.yml`) runs a matrix of Python 3.8–3.12 × MongoDB 4.2–6.0 and
installs `dservercore`, `dserver-search-plugin-mongo`, `dserver-retrieve-plugin-mongo`,
and `dserver-direct-mongo-plugin` from their `main` branches first.

Build backend is `flit_scm`; version is derived from git tags via `setuptools_scm` and
written to `dserver_dependency_graph_plugin/version.py` (do not edit by hand).

## Routes (actual)

Defined in `__init__.py` on `graph_bp` (`url_prefix="/graph"`):

- `GET  /graph/uuids/<uuid>` — graph using server-default `DEPENDENCY_KEYS`.
- `POST /graph/uuids/<uuid>` — body is a `DependencyKeysSchema` (`{"dependency_keys": [...]}`);
  only honored when `DYNAMIC_DEPENDENCY_KEYS` is enabled, otherwise it silently falls back
  to the defaults.

Note: `README.rst` documents an older `/graph/lookup/<uuid>` path — the code uses
`/graph/uuids/<uuid>`. Trust the code.

## Architecture / request flow

The hard part is all MongoDB aggregation-pipeline construction. Two files carry it:

- **`graph.py`** — pure pipeline builders (no DB calls), two distinct concerns:
  1. `build_undirected_adjacency_lists(keys)` builds the **view** definition: it unwinds
     each configured dependency key into directed `(uuid → derived_from)` edges, then
     emits *both* directions (`group_dependencies` + `group_inverse_dependencies`) so the
     graph can be traversed forward and backward. Invalid edges are dropped by a
     `UUID_v4_REGEX` `$match`.
  2. `query_dependency_graph(...)` builds the **query** pipeline: a `$graphLookup` over that
     view starting from the requested uuid, re-joined (`$lookup`) against the real dataset
     collection, with `pre_query`/`post_query` privilege filters and a final `$project` that
     strips `readme`, `manifest`, `annotations`.

- **`__init__.py`** — the stateful half. `DependencyGraphExtension.init_app` opens the
  mongo client and stashes `client`/`db`/`collection` as **class variables** (so the
  module-level route functions can reach the DB — see the NOTE comment there).
  `dependency_graph_by_user_and_uuid` is the orchestrator: gates on `ENABLE_DEPENDENCY_VIEW`,
  resolves a cached view via `_get_dependency_view_from_keys`, applies privilege filtering
  through `dservercore`'s `_preprocess_privileges` + the local `_dict_to_mongo_query`, runs
  the aggregation, and converts datetimes to float timestamps for the response.

### View caching / bookkeeping

Each distinct *set* of dependency keys gets its own materialized view named
`<PREFIX><utc-iso-timestamp>` (e.g. `dep:2020-10-05T01:22:39.581592`). A bookkeeping
collection (`dep_views`) maps `keys → view name` with an `accessed_on` timestamp and acts
as an LRU: when count exceeds `MONGO_DEPENDENCY_VIEW_CACHE_SIZE`, the least-recently-accessed
view is dropped. `FORCE_REBUILD_DEPENDENCY_VIEW=True` drops and recreates the view on every
query (needed to pick up changes to `DEPENDENCY_KEYS`). All bookkeeping helpers are wrapped
by `@assert_dependency_view_bookkeeping_collection` which lazily creates that collection.

### Security boundary in `utils.py`

`utils.py` is a vendored copy of query-building helpers from `dserver-direct-mongo-plugin`
(deliberately copied to drop the runtime dependency). `_dict_to_mongo_query` can merge a
caller-supplied raw mongo `query`; `_assert_no_forbidden_operators` **recursively rejects**
`$where`, `$function`, `$accumulator` to block server-side JavaScript execution. Tests in
`test_raw_query_hardening.py` lock this down — keep that guarantee when editing.

## Configuration (`config.py`)

`Config` reads env vars at import time. Key behavioral switches (all `DSERVER_`-prefixed
env vars, parsed against `AFFIRMATIVE_EXPRESSIONS`):

- `MONGO_URI` / `MONGO_DB` / `MONGO_COLLECTION` — **required**; `init_app` raises if absent.
  Listed in `CONFIG_SECRETS_TO_OBFUSCATE` so the `/config/info` route never returns them clear-text.
- `DSERVER_ENABLE_DEPENDENCY_VIEW` (default True), `DSERVER_DYNAMIC_DEPENDENCY_KEYS` (default True),
  `DSERVER_FORCE_REBUILD_DEPENDENCY_VIEW` (default False).
- `DSERVER_DEPENDENCY_KEYS` — JSON list (or bare string) of dotted paths to source UUIDs.
  Default: `["readme_parsed.derived_from.uuid", "annotations.source_dataset_uuid"]`. Nesting
  hierarchy is irrelevant; the dot-path is just unwound. Note it traverses `readme_parsed`
  (the server-parsed README), **not** raw `readme` — a string README breaks traversal.

## Conventions / gotchas

- A dataset is truly identified by `(uuid, base_uri)`, but the graph is keyed on `uuid`
  alone — duplicate registrations of one uuid across base URIs yield one arbitrary hit
  (see the `TODO` in `graph.py`).
- Privilege filtering happens **twice** (pre- and post-graph-traversal) so a user who lacks
  access to part of a graph gets a truncated/disconnected result rather than a leak.
- When changing the response shape, update the field-exclusion markers in
  `tests/test_graph_routes.py` (server-stamped fields like `created_at`, `frozen_at`,
  `uploaded_at`, `uploaded_by` are excluded from comparison).
