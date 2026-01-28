# eoforeststac/catalog/reader.py

import pystac


def read_collection(href: str):
    return pystac.Collection.from_file(href)


def read_item(href: str):
    return pystac.Item.from_file(href)
