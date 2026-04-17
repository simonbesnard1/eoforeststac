from eoforeststac.catalog.root import build_catalog

catalog = build_catalog(write=True, build_browser=True)
print("Root catalog built at:", catalog.self_href)
