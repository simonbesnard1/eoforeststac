from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset
import geopandas as gpd

import numpy as np
import pandas as pd

def circular_mask(radius_px: int) -> np.ndarray:
    yy, xx = np.ogrid[-radius_px:radius_px+1, -radius_px:radius_px+1]
    return (xx*xx + yy*yy) <= radius_px*radius_px

def extract_window(arr: np.ndarray, cy: int, cx: int, radius_px: int) -> np.ndarray:
    """Return (2r+1,2r+1) window clipped at edges (pad with NaN to keep shape)."""
    r = radius_px
    H, W = arr.shape
    y0, y1 = cy - r, cy + r + 1
    x0, x1 = cx - r, cx + r + 1

    win = np.full((2*r+1, 2*r+1), np.nan, dtype=np.float32)

    sy0 = max(y0, 0); sy1 = min(y1, H)
    sx0 = max(x0, 0); sx1 = min(x1, W)

    wy0 = sy0 - y0; wy1 = wy0 + (sy1 - sy0)
    wx0 = sx0 - x0; wx1 = wx0 + (sx1 - sx0)

    win[wy0:wy1, wx0:wx1] = arr[sy0:sy1, sx0:sx1]
    return win

def tower_mahalanobis_distance(
    B: np.ndarray,
    H: np.ndarray,
    towers_px: pd.DataFrame,   # must have columns: tower_id, row, col
    r_med_px: int,
    r_pot_px: int,
    q_pot: float = 0.95,
    ridge: float = 1e-6,
) -> pd.DataFrame:
    """
    Computes Mahalanobis distance per tower between:
      x = [median(B within r_med), median(H within r_med)]
      mu = [q95(B within r_pot),  q95(H within r_pot)]
    Sigma estimated from [B,H] samples within r_pot, masked by circle.
    """
    m_med = circular_mask(r_med_px)
    m_pot = circular_mask(r_pot_px)

    rows = []
    for _, tr in towers_px.iterrows():
        tid = tr["tower_id"]
        cy = int(tr["row"])
        cx = int(tr["col"])

        # Tower neighborhood (median within 1 km equivalent)
        Bw = extract_window(B, cy, cx, r_med_px)[m_med]
        Hw = extract_window(H, cy, cx, r_med_px)[m_med]
        Bw = Bw[np.isfinite(Bw)]
        Hw = Hw[np.isfinite(Hw)]
        xB = np.nanmedian(Bw) if Bw.size else np.nan
        xH = np.nanmedian(Hw) if Hw.size else np.nan

        # Potential neighborhood (q95 within 5 km equivalent)
        Bp = extract_window(B, cy, cx, r_pot_px)[m_pot]
        Hp = extract_window(H, cy, cx, r_pot_px)[m_pot]
        # Keep paired finite samples for covariance
        paired = np.isfinite(Bp) & np.isfinite(Hp)
        Bp_f = Bp[paired].astype(np.float64)
        Hp_f = Hp[paired].astype(np.float64)

        muB = np.nanquantile(Bp_f, q_pot) if Bp_f.size else np.nan
        muH = np.nanquantile(Hp_f, q_pot) if Hp_f.size else np.nan

        # Sigma from local samples (Option A)
        if Bp_f.size >= 10:
            X = np.vstack([Bp_f, Hp_f]).T  # (n,2)
            Sigma = np.cov(X, rowvar=False)
            Sigma = Sigma + ridge * np.eye(2)  # stabilize
            try:
                invS = np.linalg.inv(Sigma)
                d = np.array([xB - muB, xH - muH], dtype=np.float64)
                Dm = float(np.sqrt(d.T @ invS @ d)) if np.all(np.isfinite(d)) else np.nan
            except np.linalg.LinAlgError:
                Dm = np.nan
        else:
            Sigma = np.full((2,2), np.nan)
            Dm = np.nan

        rows.append({
            "tower_id": tid,
            "B_med_rmed": xB,
            "H_med_rmed": xH,
            "B_q95_rpot": muB,
            "H_q95_rpot": muH,
            "mah_dist": Dm,
            "n_cov": int(Bp_f.size),
            "Sigma_00": Sigma[0,0] if np.isfinite(Sigma).all() else np.nan,
            "Sigma_01": Sigma[0,1] if np.isfinite(Sigma).all() else np.nan,
            "Sigma_11": Sigma[1,1] if np.isfinite(Sigma).all() else np.nan,
        })

    return pd.DataFrame(rows)


import xarray as xr
import numpy as np

def biomass_trend_ols(B: xr.DataArray) -> xr.DataArray:
    """
    B: DataArray with dims ('time','y','x') and time coord as years (int) or datetime.
    Returns slope in biomass units per year.
    """
    # Convert time to numeric years
    if np.issubdtype(B.time.dtype, np.datetime64):
        years = xr.DataArray(B["time"].dt.year.astype(np.float32), dims=["time"], coords={"time": B.time})
    else:
        years = xr.DataArray(B["time"].astype(np.float32), dims=["time"], coords={"time": B.time})

    t = years
    t0 = t - t.mean("time")

    B0 = B - B.mean("time")

    cov = (t0 * B0).mean("time", skipna=True)
    var = (t0 * t0).mean("time")

    slope = (cov / var).rename("B_slope_ols")
    return slope

def height_site_index(H: xr.DataArray, ref_year: int = 2020, alpha_years: float = 10.0) -> xr.Dataset:
    """
    H: DataArray(time,y,x), canopy height 2000-2020.
    Returns:
      H_ref: height at ref_year (or nearest)
      H_slope: OLS slope (m/yr)
      site_index: H_ref + alpha_years * H_slope
    """
    # numeric years
    if np.issubdtype(H.time.dtype, np.datetime64):
        years = H["time"].dt.year
    else:
        years = H["time"]

    # reference height (nearest year)
    ref_idx = int(np.argmin(np.abs(years.values.astype(int) - ref_year)))
    H_ref = H.isel(time=ref_idx).rename(f"H_{int(years.values[ref_idx])}")

    # slope
    H_slope = biomass_trend_ols(H).rename("H_slope_ols")  # reuse OLS code

    SI = (H_ref + alpha_years * H_slope).rename(f"site_index_a{alpha_years:g}")

    return xr.Dataset({"H_ref": H_ref, "H_slope": H_slope, "site_index": SI})


import os
import numpy as np
import pandas as pd
import geopandas as gpd
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
    B2020, H2020,
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
        H_ctx_da = _open_crop_da(H2020, _bbox(geom_ctx))

        # Mask to polygons (or bbox fallback)
        B_core_vals = _mask_by_polygon(_open_crop_da(B2020, _bbox(geom_core)), geom_core)
        H_core_vals = _mask_by_polygon(_open_crop_da(H2020, _bbox(geom_core)), geom_core)
        B_ctx_vals  = _mask_by_polygon(B_ctx_da, geom_ctx)
        H_ctx_vals  = _mask_by_polygon(H_ctx_da, geom_ctx)

        # Context stats (independent!)
        b_ctx = np.asarray(B_ctx_vals).ravel()
        b_ctx = b_ctx[np.isfinite(b_ctx)]
        h_ctx = np.asarray(H_ctx_vals).ravel()
        h_ctx = h_ctx[np.isfinite(h_ctx)]

        muB = float(np.nanquantile(b_ctx, q_pot)) if b_ctx.size else np.nan
        muH = float(np.nanquantile(h_ctx, q_pot)) if h_ctx.size else np.nan

        if robust_sigma:
            # robust sigma via MAD (median absolute deviation)
            # sigma ≈ 1.4826 * MAD
            if b_ctx.size:
                madB = np.nanmedian(np.abs(b_ctx - np.nanmedian(b_ctx)))
                sigB = float(1.4826 * madB)
            else:
                sigB = np.nan
            if h_ctx.size:
                madH = np.nanmedian(np.abs(h_ctx - np.nanmedian(h_ctx)))
                sigH = float(1.4826 * madH)
            else:
                sigH = np.nan
        else:
            sigB = float(np.nanstd(b_ctx)) if b_ctx.size else np.nan
            sigH = float(np.nanstd(h_ctx)) if h_ctx.size else np.nan

        # Per-pixel 1D Mahalanobis distances in the core
        dB = one_dim_mahalanobis_distances(B_core_vals, muB, sigB, eps=eps)
        dH = one_dim_mahalanobis_distances(H_core_vals, muH, sigH, eps=eps)

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
        sH = summarize(dH)

        rows.append({
            "SITE_ID": site_id,
            # context stats
            "B_q95_ctx": muB, "B_sigma_ctx": sigB, "n_ctx_B": int(b_ctx.size),
            "H_q95_ctx": muH, "H_sigma_ctx": sigH, "n_ctx_H": int(h_ctx.size),
            # core distance summaries
            "B_MD_median": sB["median"], "B_MD_mean": sB["mean"], "B_MD_p90": sB["p90"], "B_MD_max": sB["max"], "n_core_B": sB["n"],
            "H_MD_median": sH["median"], "H_MD_mean": sH["mean"], "H_MD_p90": sH["p90"], "H_MD_max": sH["max"], "n_core_H": sH["n"],
        })

    return pd.DataFrame(rows)


provider = ZarrProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

# 1) Load rasters
height = provider.open_dataset(
                    collection_id="POTAPOV_HEIGHT",
                    version="1.0") 
# height = subset(
#     height,
#     geometry=geometry)["canopy_height"]

# Biomass time series: choose one source
B = provider.open_dataset(
                    collection_id="CCI_BIOMASS",
                    version="6.0")
# B = subset(
#     B,
#     geometry=geometry)["aboveground_biomass"] 

# Disturbance: binary annual
# dist = provider.open_dataset(
#                     collection_id="EFDA",
#                     version="2.1.1") 
# dist = subset(
#     dist,
#     geometry=geometry)["disturbance_occurence"]


# B2020, H2020 as numpy arrays shape (y,x)
# towers_px: DataFrame with tower_id,row,col (you can compute row/col via rasterio index if you have geoms)
import glob
roi_paths = sorted(glob.glob("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/*.geojson"))

df_dm = site_1d_mahalanobis_BH(
    roi_paths= roi_paths,
    B2020=B.sel(time='2020-01-01')['aboveground_biomass'],
    H2020=height.sel(time='2020-01-01')['canopy_height']
)

# B_2007_2023: xr.DataArray(time,y,x)
B_slope = biomass_trend_ols(B)


# H_2000_2020: xr.DataArray(time,y,x) in meters
ds_si = height_site_index(height, ref_year=2020, alpha_years=10.0)


# 2) Reproject everything to target_crs and align grids

# Reproject biomass & disturbance year-by-year to avoid huge memory spikes
# (If B and dist already share the same projected grid, skip this.)
Bp_list = []
for t in B.time.values:
    Bp_list.append(B.sel(time=t).expand_dims(time=[t]))
Bp = xr.concat(Bp_list, dim="time").rename("B")

# 3) Biomass potential (5 km upper quantile) for each year (or pick a reference year)
# If you want a "static" potential map, use the max-year biomass or a median over stable years first.
# Here: compute potential for each year (expensive). Alternative: compute potential on mean(B) or max(B).
# Start simple: potential on multi-year median biomass.
B_med = Bp.median("time", skipna=True).rename("B_med")
pot_path = os.path.join(CFG["out_dir"], "B_pot_q95_5km.tif")
B_pot = block_process_moving_quantile(
    src=B_med,
    q=CFG["q_potential"],
    radius_m=CFG["radius_potential_m"],
    out_path=pot_path,
    tile_size_px=CFG["tile_size_px"],
).rename("B_pot")

# 4) Deficit (distance to steady-state proxy)
# Deficit per year
B_def = compute_deficit(Bp, B_pot).rename("B_deficit")

# 5) Optional: height potential + deficit
H_pot_path = os.path.join(CFG["out_dir"], "H_pot_q95_5km.tif")
H_pot = block_process_moving_quantile(
    src=height_p.rename("H"),
    q=CFG["q_potential"],
    radius_m=CFG["radius_potential_m"],
    out_path=H_pot_path,
    tile_size_px=CFG["tile_size_px"],
).rename("H_pot")
H_def = compute_deficit(height_p.rename("H"), H_pot).rename("H_deficit")

# 6) Allometric residual BH (fit using median biomass to reduce noise)
a, b = fit_allometry_loglog(B_med, height_p.rename("H"))
BH_res = allometric_residual(B_med, height_p.rename("H"), a=a, b=b)

# 7) Disturbance legacy metrics
years = xr.DataArray(Bp.time.values.astype(np.int32), dims=["time"], coords={"time": Bp.time})

# 8) Texture metrics (pick a smaller radius, e.g., 1 km or 2 km, for heterogeneity)
B_tex_std = local_texture_std(B_med, radius_m=1000).rename("B_tex_std_1km")
H_tex_std = local_texture_std(height_p.rename("H"), radius_m=1000).rename("H_tex_std_1km")
B_grad = gradient_magnitude(B_med).rename("B_gradmag")
H_grad = gradient_magnitude(height_p.rename("H")).rename("H_gradmag")

# 9) Biomass trend 2007–2023 (OLS slope per pixel)
B_slope_ols = ols_slope_per_pixel(Bp, years)

# 10) Save raster outputs (GeoTIFFs for 2D, Zarr for time stacks)
# 2D maps
for da, name in [
    (B_pot, "B_pot_q95_5km"),
    (H_pot, "H_pot_q95_5km"),
    (H_def, "H_deficit"),
    (BH_res, "BH_resid"),
    (B_tex_std, "B_tex_std_1km"),
    (H_tex_std, "H_tex_std_1km"),
    (B_grad, "B_gradmag"),
    (H_grad, "H_gradmag"),
    (B_slope_ols, "B_slope_ols"),
]:
    outp = os.path.join(CFG["out_dir"], f"{name}.tif")
    da.rio.to_raster(outp, compress="deflate")

# Time stacks -> Zarr (better than GeoTIFF for 3D)
B_def.to_dataset(name="B_deficit").to_zarr(os.path.join(CFG["out_dir"], "B_deficit.zarr"), mode="w")

# 11) Flux tower 1km median biomass (table)
towers = gpd.read_file(PATHS["towers_file"])
# Ensure geometry exists
if towers.geometry is None or towers.geometry.is_empty.all():
    # if you have lon/lat columns:
    towers = gpd.GeoDataFrame(
        towers,
        geometry=gpd.points_from_xy(towers["lon"], towers["lat"]),
        crs="EPSG:4326"
    )

# Use a representative biomass raster for tower context: e.g., median biomass GeoTIFF
B_med_path = os.path.join(CFG["out_dir"], "B_med.tif")
B_med.rio.to_raster(B_med_path, compress="deflate")

tower_stats = tower_buffer_stats(
    raster_path=B_med_path,
    towers=towers,
    radius_m=CFG["radius_tower_m"],
    value_name="B_med_1km",
)
tower_csv = os.path.join(CFG["out_dir"], "tower_B_med_1km.csv")
tower_stats.to_csv(tower_csv, index=False)

print("Done. Outputs in:", CFG["out_dir"])
print("Allometry log(B)=a+b*log(H):", (a, b))
print("Tower stats:", tower_csv)
