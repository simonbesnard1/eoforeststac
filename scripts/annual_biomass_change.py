import numpy as np
import xarray as xr
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


def biomass_change_gross_net(
    B: xr.DataArray,
    smooth_window: int = 5,
    center: bool = True,
    min_periods: int | None = None,
    per_year: bool = True,
) -> xr.Dataset:
    """
    Compute smoothed biomass change metrics per pixel:
      - net_change: sum(dB) over time
      - gross_gain: sum(max(dB,0))
      - gross_loss: sum(max(-dB,0))
    where dB is the first difference of the SMOOTHED series.

    Parameters
    ----------
    B : xr.DataArray
        dims: ('time', ...). time can be int years or datetime.
    smooth_window : int
        Rolling window length in timesteps (years).
    center : bool
        Centered rolling window. True is usually nicer for trends.
    min_periods : int | None
        Minimum observations required in rolling window.
        If None: uses smooth_window.
    per_year : bool
        If True, return mean annual values (divide by number of year-steps).
        Net change stays as total unless you also want per-year net rate.

    Returns
    -------
    xr.Dataset with:
      B_smooth, dB, net_change, gross_gain, gross_loss,
      gain_rate, loss_rate, net_rate (optional)
    """
    if "time" not in B.dims:
        raise ValueError("B must have a 'time' dimension.")

    if min_periods is None:
        min_periods = smooth_window

    # 1) Smooth
    B_smooth = (
        B.rolling(time=smooth_window, center=center, min_periods=min_periods)
        .mean()
        .rename("B_smooth")
    )

    # 2) First difference (year-to-year change)
    dB = B_smooth.diff("time").rename("dB")

    # 3) Gross components
    gains = xr.where(dB > 0, dB, 0.0)
    losses = xr.where(dB < 0, -dB, 0.0)

    gross_gain = gains.sum("time", skipna=True).rename("gross_gain")
    gross_loss = losses.sum("time", skipna=True).rename("gross_loss")
    net_change = dB.sum("time", skipna=True).rename("net_change")

    ds = xr.Dataset(
        {
            "B_smooth": B_smooth,
            "dB": dB,
            "net_change": net_change,
            "gross_gain": gross_gain,
            "gross_loss": gross_loss,
        }
    )

    # Convert to annualized rates if requested
    n_steps = dB.sizes["time"]  # e.g., 2023-2007 => 16 steps
    if per_year and n_steps > 0:
        ds["gain_rate"] = (gross_gain / n_steps).rename("gain_rate")
        ds["loss_rate"] = (gross_loss / n_steps).rename("loss_rate")
        ds["net_rate"] = (net_change / n_steps).rename("net_rate")

    return ds


def biomass_change_gross_net_savgol(
    B: xr.DataArray,
    window_length: int = 7,  # must be odd
    polyorder: int = 1,
    per_year: bool = True,
) -> xr.Dataset:
    """
    Savitzky–Golay smooth then compute first differences and gross/net.
    """
    try:
        from scipy.signal import savgol_filter
    except Exception as e:
        raise ImportError("scipy is required for Savitzky–Golay smoothing") from e

    if window_length % 2 == 0:
        raise ValueError("window_length must be odd.")
    if window_length < polyorder + 2:
        raise ValueError("window_length too small for chosen polyorder.")

    def _savgol_1d(x):
        # x is 1D array over time
        if np.all(~np.isfinite(x)):
            return x
        # Fill NaNs by linear interpolation to avoid filter explosion
        t = np.arange(x.size)
        good = np.isfinite(x)
        if good.sum() < window_length:
            return x  # not enough data
        x_f = x.copy()
        x_f[~good] = np.interp(t[~good], t[good], x[good])
        return savgol_filter(
            x_f, window_length=window_length, polyorder=polyorder, mode="interp"
        )

    B_smooth = xr.apply_ufunc(
        _savgol_1d,
        B,
        input_core_dims=[["time"]],
        output_core_dims=[["time"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[B.dtype],
    ).rename("B_smooth")

    dB = B_smooth.diff("time").rename("dB")

    gains = xr.where(dB > 0, dB, 0.0)
    losses = xr.where(dB < 0, -dB, 0.0)

    gross_gain = gains.sum("time", skipna=True).rename("gross_gain")
    gross_loss = losses.sum("time", skipna=True).rename("gross_loss")
    net_change = dB.sum("time", skipna=True).rename("net_change")

    ds = xr.Dataset(
        {
            "B_smooth": B_smooth,
            "dB": dB,
            "net_change": net_change,
            "gross_gain": gross_gain,
            "gross_loss": gross_loss,
        }
    )

    n_steps = dB.sizes["time"]
    if per_year and n_steps > 0:
        ds["gain_rate"] = (gross_gain / n_steps).rename("gain_rate")
        ds["loss_rate"] = (gross_loss / n_steps).rename("loss_rate")
        ds["net_rate"] = (net_change / n_steps).rename("net_rate")
    return ds


provider = ZarrProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file(
    "/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/DE-Hai.geojson"
)
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)

ds_biomass = subset(ds, geometry=geometry)  # optional


# B: DataArray(time,y,x) for 2007–2023
ds_change = biomass_change_gross_net(
    ds_biomass["aboveground_biomass"], smooth_window=3, center=True
)

# Maps:
net = ds_change["net_change"]
gain = ds_change["gross_gain"]
loss = ds_change["gross_loss"]

# Annualized:
net_rate = ds_change["net_rate"]
changes_ = biomass_change_gross_net_savgol(
    ds_biomass["aboveground_biomass"].chunk(dict(time=-1)), window_length=3
)


# %% Plotting
import matplotlib.pyplot as plt


def plot_4_maps(
    net, gain, loss, net_rate, titles=None, out_png=None, robust=True, q=(0.02, 0.98)
):
    """
    Plot net/gain/loss/net_rate in a 2x2 panel with robust color limits.
    Each panel gets its own scaling (recommended).
    """
    if titles is None:
        titles = [
            "Net change (sum dB)",
            "Net rate (per year)",
            "Gross gains (sum max(dB,0))",
            "Gross losses (sum max(-dB,0))",
        ]

    fig, axs = plt.subplots(2, 2, figsize=(12.6, 8.8), constrained_layout=True)
    panels = [
        (net, titles[0]),
        (gain, titles[1]),
        (loss, titles[2]),
        (net_rate, titles[3]),
    ]

    for ax, (da, title) in zip(axs.ravel(), panels):
        vmin = vmax = None
        if robust:
            a = da.values
            a = a[np.isfinite(a)]
            if a.size:
                vmin, vmax = np.quantile(a, q)

        da.plot.imshow(ax=ax, add_colorbar=True, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=16, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=12)

    if out_png:
        plt.savefig(out_png, dpi=220, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


plot_4_maps(net, net_rate, gain, loss, out_png="assets/biomass_change_overview.png")
