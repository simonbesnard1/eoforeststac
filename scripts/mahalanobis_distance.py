from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset
import geopandas as gpd

import numpy as np
import pandas as pd

import os
from shapely.ops import unary_union

def _get_site_geom_wgs84(roi_gdf: gpd.GeoDataFrame):
    g = roi_gdf.to_crs("EPSG:4326").geometry
    return unary_union(g.values)

def _buffer_in_meters(geom_wgs84, buffer_m: float, metric_crs="EPSG:3035"):
    g = gpd.GeoSeries([geom_wgs84], crs="EPSG:4326").to_crs(metric_crs)
    gbuf = g.buffer(buffer_m)
    return gbuf.to_crs("EPSG:4326").iloc[0]

def _bbox(geom_wgs84):
    minx, miny, maxx, maxy = geom_wgs84.bounds
    return dict(lon_min=minx, lat_min=miny, lon_max=maxx, lat_max=maxy)

def _open_crop_da(da, bbox):
    coords = set(da.coords)
    lon_name = "lon" if "lon" in coords else ("longitude" if "longitude" in coords else None)
    lat_name = "lat" if "lat" in coords else ("latitude" if "latitude" in coords else None)
    if lon_name is None or lat_name is None:
        raise ValueError(f"Can't infer lon/lat names from coords {list(da.coords)}")

    lon = da[lon_name]
    lat = da[lat_name]
    lon_slice = slice(bbox["lon_min"], bbox["lon_max"]) if lon[0] < lon[-1] else slice(bbox["lon_max"], bbox["lon_min"])
    lat_slice = slice(bbox["lat_min"], bbox["lat_max"]) if lat[0] < lat[-1] else slice(bbox["lat_max"], bbox["lat_min"])
    return da.sel({lon_name: lon_slice, lat_name: lat_slice})

def _mask_by_polygon(da2d, geom_wgs84):
    """
    Best effort polygon mask using rioxarray clip.
    If clip fails, falls back to bbox-only.
    """
    try:
        import rioxarray  # noqa
        da = da2d
        # Normalize names for rioxarray
        if "lon" in da.coords and "lat" in da.coords:
            da = da.rename({"lon": "x", "lat": "y"})
        elif "longitude" in da.coords and "latitude" in da.coords:
            da = da.rename({"longitude": "x", "latitude": "y"})

        da = da.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=False)
        da = da.rio.write_crs("EPSG:4326", inplace=False)

        gdf = gpd.GeoDataFrame({"geometry": [geom_wgs84]}, crs="EPSG:4326")
        clipped = da.rio.clip(gdf.geometry, gdf.crs, drop=True)
        return clipped.values
    except Exception:
        return da2d.values

def one_dim_mahalanobis_distances(core_vals, mu_context, sigma_context, eps=1e-6):
    """
    Returns per-pixel distances d_i = |x_i - mu| / sigma
    """
    x = np.asarray(core_vals).ravel()
    x = x[np.isfinite(x)]
    if x.size == 0 or not np.isfinite(mu_context) or not np.isfinite(sigma_context):
        return np.array([], dtype=np.float32)
    s = float(sigma_context) + eps
    return np.abs(x - float(mu_context)) / s

def site_1d_mahalanobis_BH(
    roi_paths,
    B2020,
    core_buffer_m=1000,
    context_buffer_m=5000,
    q_pot=0.95,
    metric_crs="EPSG:3035",
    eps=1e-6,
    robust_sigma=False,   # if True, use MAD->sigma instead of std
):
    rows = []

    for p in roi_paths:
        roi = gpd.read_file(p)
        site_id = roi.iloc[0].get("SITE_ID", os.path.splitext(os.path.basename(p))[0])
        geom = _get_site_geom_wgs84(roi)

        geom_core = _buffer_in_meters(geom, core_buffer_m, metric_crs=metric_crs)
        geom_ctx  = _buffer_in_meters(geom, context_buffer_m, metric_crs=metric_crs)

        # Crop by context bbox to limit IO
        B2020 = B2020.where(B2020 >0)
        B_ctx_da = _open_crop_da(B2020, _bbox(geom_ctx))
        
        # Mask to polygons (or bbox fallback)
        B_core_vals = _mask_by_polygon(_open_crop_da(B2020, _bbox(geom_core)), geom_core)
        B_ctx_vals  = _mask_by_polygon(B_ctx_da, geom_ctx)
        
        # Context stats (independent!)
        b_ctx = np.asarray(B_ctx_vals).ravel()
        b_ctx = b_ctx[np.isfinite(b_ctx)]
        
        muB = float(np.nanquantile(b_ctx, q_pot)) if b_ctx.size else np.nan
        
        if robust_sigma:
            # robust sigma via MAD (median absolute deviation)
            # sigma ≈ 1.4826 * MAD
            if b_ctx.size:
                madB = np.nanmedian(np.abs(b_ctx - np.nanmedian(b_ctx)))
                sigB = float(1.4826 * madB)
            else:
                sigB = np.nan
        else:
            sigB = float(np.nanstd(b_ctx)) if b_ctx.size else np.nan
            
        # Per-pixel 1D Mahalanobis distances in the core
        dB = one_dim_mahalanobis_distances(B_core_vals, muB, sigB, eps=eps)

        # Summaries (choose what you like later)
        def summarize(d):
            if d.size == 0:
                return dict(median=np.nan, mean=np.nan, p90=np.nan, max=np.nan, n=0)
            return dict(
                median=float(np.nanmedian(d)),
                mean=float(np.nanmean(d)),
                p90=float(np.nanquantile(d, 0.90)),
                max=float(np.nanmax(d)),
                n=int(d.size),
            )

        sB = summarize(dB)

        rows.append({
            "SITE_ID": site_id,
            # context stats
            "B_q95_ctx": muB, "B_sigma_ctx": sigB, "n_ctx_B": int(b_ctx.size),
            # core distance summaries
            "B_MD_median": sB["median"], 
            "B_MD_mean": sB["mean"], "B_MD_p90": sB["p90"], 
            "B_MD_max": sB["max"], "n_core_B": sB["n"],
        })

    return pd.DataFrame(rows)


provider = ZarrProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

# Biomass time series: choose one source
B = provider.open_dataset(
                    collection_id="CCI_BIOMASS",
                    version="6.0")
ds_biomass = subset(
    B,
    geometry=geometry)  # optional

import glob
roi_paths = sorted(glob.glob("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/*.geojson"))

df_dm = site_1d_mahalanobis_BH(
    roi_paths= roi_paths,
    B2020=B.sel(time='2020-01-01')['aboveground_biomass']
)

import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(7.2, 6), constrained_layout=True)

sc = ax.scatter(
    df_dm["B_MD_median"],
    df_dm["B_MD_p90"],
    c=df_dm["B_q95_ctx"],
    cmap="viridis",
    s=40,
    alpha=0.85
)

ax.set_ylabel("Mahalanobis distance (p90)", fontsize=13)
ax.set_xlabel("Mahalanobis distance (median)", fontsize=13)
ax.set_title("Mahalanobis distance across FLUXNET sites", fontsize=15, fontweight="bold")

cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("Biomass potential (q95, 5 km) [MgC ha$^{-1}$]"
    , fontsize=12)

ax.legend(frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)


fig, ax = plt.subplots(1, 1, figsize=(6.8, 4.6), constrained_layout=True)

ax.hist(
    df_dm["B_MD_median"],
    bins=25,
    color="#4C72B0",
    alpha=0.85
)

ax.set_xlabel("Mahalanobis distance to steady state", fontsize=13)
ax.set_ylabel("Number of sites", fontsize=13)
ax.set_title("Most ecosystems are far from steady state", fontsize=15, fontweight="bold")

ax.legend(frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)


import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec

fig, ax = plt.subplots(1, 1, figsize=(6, 4.5), constrained_layout=True)

sc = ax.scatter(
    df_dm["B_MD_median"],
    df_dm["B_MD_p90"],
    c=df_dm["B_q95_ctx"],
    cmap="viridis",
    s=40,
    alpha=0.85
)

ax.plot([0, mx], [0, mx], "k--", lw=2)
ax.set_xlabel("Mahalanobis distance (median)", fontsize=13)
ax.set_ylabel("Mahalanobis distance (p90)", fontsize=13)
ax.legend(frameon=False) 
ax.spines["top"].set_visible(False) 
ax.spines["right"].set_visible(False)
ax.set_title("Mahalanobis distance across FLUXNET sites", fontsize=15, fontweight="bold")

# Inset histogram
axins = ax.inset_axes([0.6, 0.1, 0.35, 0.35])
axins.hist(df_dm["B_MD_median"], bins=20, color="#4C72B0", alpha=0.85)
axins.set_title("Median MD", fontsize=10)
axins.tick_params(labelsize=9)
axins.spines["top"].set_visible(False) 
axins.spines["right"].set_visible(False)


cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("Biomass potential (q95)")

plt.savefig('/home/simon/Documents/science/GFZ/presentation/fluxcom-x/kickoff2026_besnard/images/data_mahalanobis', dpi=220, bbox_inches="tight")


