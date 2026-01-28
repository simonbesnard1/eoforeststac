import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd

from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset
import matplotlib as mpl


params = {
    # font
    "font.family": "serif",
    # 'font.serif': 'Times', #'cmr10',
    "font.size": 16,
    # axes
    "axes.titlesize": 12,
    "axes.labelsize": 12,
    "axes.linewidth": 0.5,
    # ticks
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "xtick.major.width": 0.3,
    "ytick.major.width": 0.3,
    "xtick.minor.width": 0.3,
    "ytick.minor.width": 0.3,
    # legend
    "legend.fontsize": 14,
    # tex
    "text.usetex": True,
}

mpl.rcParams.update(params)


def pick_main_variable(ds):
    """
    Heuristic to pick a representative variable for plotting.
    Prefers 2D/3D spatial variables, ignores coords & std layers.
    """
    for name, da in ds.data_vars.items():
        if {"latitude", "longitude"}.issubset(da.dims):
            if not name.endswith("_std"):
                return name
    # fallback
    return list(ds.data_vars)[0]


def plot_all_collections_for_roi(
    provider: ZarrProvider,
    roi_geometry,
    *,
    time=None,
    ncols: int = 3,
):
    """
    Plot one representative layer per collection for a given ROI.
    """

    # ---------------------------------------------------------
    # Discover collections
    # ---------------------------------------------------------
    collections = provider.list_collections()
    collections = sorted(collections, key=lambda c: c.id)

    datasets = []

    for col in collections:
        col_id = col.id

        # list items (= versions)
        items = provider.list_items(col_id)
        if not items:
            continue

        # pick latest version (lexicographic works for your catalog)
        versions = sorted(i.id.replace(f"{col_id}_v", "") for i in items)
        version = versions[-1]

        print(f"Opening {col_id} v{version}")

        try:
            ds = provider.open_dataset(
                collection_id=col_id,
                version=version,
            )

            ds_sel = subset(
                ds,
                geometry=roi_geometry,
                time=time,
            )

            var = pick_main_variable(ds_sel)
            datasets.append((col_id, version, var, ds_sel[var]))

        except Exception as e:
            print(f"⚠️ Skipping {col_id}: {e}")

    if not datasets:
        raise RuntimeError("No datasets could be loaded for plotting.")

    # ---------------------------------------------------------
    # Plotting
    # ---------------------------------------------------------
    n = len(datasets)
    ncols = min(ncols, n)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(7 * ncols, 5 * nrows),
        constrained_layout=True,
    )

    axes = np.atleast_1d(axes).ravel()

    for ax, (col_id, version, var, da) in zip(axes, datasets):
        time_note = ""

        # reduce members if present (robust default)
        if "members" in da.dims:
            da = da.median("members")
            time_note += " (members-median)"

        # reduce time if needed
        if "time" in da.dims:
            if da.sizes["time"] == 1:
                da_plot = da.isel(time=0)
            else:
                da_plot = da.mean("time")
                time_note += " (time-mean)"
        else:
            da_plot = da

        da_plot.plot(
            ax=ax,
            add_colorbar=True,
        )

        ax.set_title(f"{col_id} v{version}\n{var}{time_note}", fontsize=18)
        ax.set_xlabel("")
        ax.set_ylabel("")

    for ax in axes[len(datasets) :]:
        ax.axis("off")

    plt.savefig("/home/simon/Documents/fig1_v3.png", dpi=300)


provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi_gdf = gpd.read_file(
    "/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/DE-Hai.geojson"
)
geom = roi_gdf.to_crs("EPSG:4326").geometry.union_all()

plot_all_collections_for_roi(
    provider,
    geom,
    time=("2000-01-01", "2022-12-31"),
)
