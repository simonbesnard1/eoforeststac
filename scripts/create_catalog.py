from eoforeststac.catalog.root import build_root_catalog

catalog = build_root_catalog(write=True)
print("Root catalog built at:", catalog.self_href)