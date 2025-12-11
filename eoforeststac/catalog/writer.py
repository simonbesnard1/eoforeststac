# eoforeststac/catalog/writer.py

from eoforeststac.core.io import write_json

def write_collection(collection):
    write_json(collection.self_href, collection.to_dict())


def write_item(item):
    write_json(item.self_href, item.to_dict())
