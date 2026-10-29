"""Which data stores need a pyramid, and which pyramids are no longer needed.

The data on S3 is the reference: every finished ``*.zarr`` store (one with
consolidated metadata) under the collections prefix is found by listing the
bucket, so products that are hidden from the catalog or nested in site
sub-collections (ALS, ULS) are covered too. Only the newest version of each
store gets a pyramid, as the explorer shows the newest, and only when it is
larger than ``target_size`` pixels; smaller stores render fine without one.

Reducers come from the ``"pyramid"`` entry of the product config whose ``id``
matches the store's collection folder; variables it does not list get a
reducer inferred from their name and metadata.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import fsspec

from eoforeststac.pyramids.build import SPATIAL_DIMS, pyramid_path

_VERSION = re.compile(r"^(?P<name>.+)_v(?P<version>\d[\w.]*)\.zarr$")


@dataclass
class Store:
    collection: str
    name: str  # store name without version, e.g. ALS_SPAIN_PNOA_1m
    version: tuple
    path: str  # bucket/key
    height: int = 0
    width: int = 0

    @property
    def label(self) -> str:
        return self.path.rsplit("/", 1)[-1].removesuffix(".zarr")


@dataclass
class Task:
    kind: str  # build | finish | ok | small | unfinished-data | delete
    path: str
    reason: str
    store: Store | None = None
    reducers: dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.store.label if self.store else self.path.rsplit("/", 1)[-1]


def _version_key(version: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"[._]", version) if p)


@lru_cache(maxsize=1)
def product_configs() -> dict[str, dict[str, Any]]:
    """Product configs by collection id, from every eoforeststac.products module."""
    import eoforeststac.products as products

    configs: dict[str, dict[str, Any]] = {}
    for info in pkgutil.iter_modules(products.__path__):
        module = importlib.import_module(f"eoforeststac.products.{info.name}")
        for name, value in vars(module).items():
            if name.endswith("_CFG") and isinstance(value, dict) and "id" in value:
                configs[value["id"]] = value
    return configs


def configured_reducers(collection: str) -> dict[str, str]:
    config = product_configs().get(collection, {})
    return dict(config.get("pyramid", {}).get("reducers", {}))


def _grid_size(metadata: dict[str, Any]) -> tuple[int, int]:
    """Largest (height, width) of the store's gridded variables."""
    best = (0, 0)
    for key, attrs in metadata.items():
        if not key.endswith("/.zattrs") or key.count("/") != 1:
            continue
        dims = attrs.get("_ARRAY_DIMENSIONS", [])
        array = metadata.get(key[: -len(".zattrs")] + ".zarray")
        if not array:
            continue
        for y_dim, x_dim in SPATIAL_DIMS:
            if y_dim in dims and x_dim in dims:
                h, w = (
                    array["shape"][dims.index(y_dim)],
                    array["shape"][dims.index(x_dim)],
                )
                if h * w > best[0] * best[1]:
                    best = (h, w)
    return best


def find_stores(
    fs: fsspec.AbstractFileSystem, prefix: str
) -> tuple[list[Store], list[str], list[str]]:
    """(finished data stores, unfinished data stores, pyramid stores) under prefix."""
    stores, unfinished, pyramids = [], [], []
    for folder in fs.ls(prefix, detail=False):
        folder = folder.lstrip("/")  # some filesystems list "/bucket/key"
        try:
            entries = fs.ls(folder, detail=False)
        except (FileNotFoundError, NotADirectoryError):
            continue
        for path in entries:
            path = path.lstrip("/")
            base = path.rsplit("/", 1)[-1]
            if base.endswith("_pyramid.zarr"):
                pyramids.append(path)
                continue
            match = _VERSION.match(base)
            if not match:
                continue
            try:
                metadata = json.loads(fs.cat(f"{path}/.zmetadata"))["metadata"]
            except (FileNotFoundError, KeyError, ValueError):
                unfinished.append(path)
                continue
            height, width = _grid_size(metadata)
            stores.append(
                Store(
                    collection=folder.rsplit("/", 1)[-1],
                    name=match["name"],
                    version=_version_key(match["version"]),
                    path=path,
                    height=height,
                    width=width,
                )
            )
    return stores, unfinished, pyramids


def pyramid_state(fs: fsspec.AbstractFileSystem, path: str) -> tuple[int, int]:
    """(complete levels, expected levels); (0, 0) when the pyramid is missing."""
    try:
        multiscales = json.loads(fs.cat(f"{path}/.zattrs"))["multiscales"][0]
    except (FileNotFoundError, KeyError, IndexError, ValueError):
        return (0, 1) if fs.exists(path) else (0, 0)
    levels = [d["path"] for d in multiscales.get("datasets", [])]
    done = sum(fs.exists(f"{path}/{level}/_SUCCESS") for level in levels)
    return done, len(levels)


def plan(
    fs: fsspec.AbstractFileSystem,
    prefix: str,
    target_size: int = 8192,
    collections: set[str] | None = None,
    rebuild: set[str] | None = None,
) -> list[Task]:
    """What to do for every store and pyramid under the prefix."""
    stores, unfinished, pyramids = find_stores(fs, prefix)
    newest: dict[tuple[str, str], Store] = {}
    for store in stores:
        key = (store.collection, store.name)
        if key not in newest or store.version > newest[key].version:
            newest[key] = store

    tasks: list[Task] = []
    needed: set[str] = set()
    for store in sorted(newest.values(), key=lambda s: s.path):
        if collections and store.collection not in collections:
            continue
        target = pyramid_path(store.path)
        reducers = configured_reducers(store.collection)
        if max(store.height, store.width) <= target_size:
            tasks.append(
                Task(
                    "small",
                    target,
                    f"{store.height:,} x {store.width:,} px",
                    store,
                    reducers,
                )
            )
            continue
        needed.add(target)
        if rebuild and (store.collection in rebuild or store.name in rebuild):
            tasks.append(Task("rebuild", target, "requested", store, reducers))
            continue
        done, expected = pyramid_state(fs, target)
        if expected == 0:
            tasks.append(Task("build", target, "no pyramid yet", store, reducers))
        elif done < expected:
            tasks.append(
                Task(
                    "finish", target, f"{done}/{expected} levels done", store, reducers
                )
            )
        else:
            tasks.append(Task("ok", target, f"{expected} levels", store, reducers))

    for path in unfinished:
        if not collections or path.split("/")[-2] in collections:
            tasks.append(Task("unfinished-data", path, "no consolidated metadata yet"))

    for path in sorted(pyramids):
        if path in needed:
            continue
        collection = path.split("/")[-2]
        if collections and collection not in collections:
            continue
        native = path.removesuffix("_pyramid.zarr") + ".zarr"
        if not fs.exists(native):
            reason = "its data store is gone"
        elif any(t.path == path for t in tasks if t.kind == "small"):
            reason = "its data store is small enough without one"
        else:
            reason = "older version; the explorer shows the newest"
        tasks.append(Task("delete", path, reason))
    return tasks


def remove_pyramid(fs: fsspec.AbstractFileSystem, path: str, prefix: str) -> None:
    """Delete a pyramid store; refuses anything else."""
    if not (
        path.startswith(prefix.rstrip("/") + "/") and path.endswith("_pyramid.zarr")
    ):
        raise RuntimeError(f"Refusing to delete {path}")
    fs.rm(path, recursive=True)
