"""Pydantic schema for product configuration validation.

Validates product config dicts at build time to catch typos,
missing fields, and type errors early.
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator

SPDX_PATTERN = re.compile(r"^[\w\-\.+]+$")


class ProviderConfig(BaseModel):
    name: str
    roles: List[str] = []
    url: Optional[str] = None


class LinkConfig(BaseModel):
    rel: str
    href: str
    type: Optional[str] = None
    title: Optional[str] = None


class RasterBandConfig(BaseModel):
    data_type: str
    nodata: Any
    statistics: Optional[Dict[str, Any]] = None


class ItemAssetConfig(BaseModel):
    title: str
    description: str
    roles: List[str]
    type: str


class GeometryConfig(BaseModel):
    type: str
    coordinates: Any


class SummariesConfig(BaseModel, extra="allow"):
    variables: List[str]
    units_by_variable: Optional[Dict[str, str]] = None
    data_format: Optional[List[str]] = None


class ProductConfig(BaseModel, extra="allow"):
    """Schema for a product configuration dict.

    Validates all required fields and their types. Extra fields
    (regions, resolutions, version_notes, etc.) are allowed.
    """

    id: str
    title: str
    description: str
    bbox: List[float]
    geometry: GeometryConfig
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    collection_href: str
    base_path: str
    license: str
    providers: List[ProviderConfig]
    keywords: List[str]
    links: List[LinkConfig]
    stac_extensions: List[str]
    summaries: SummariesConfig
    item_assets: Dict[str, ItemAssetConfig]
    raster_bands: Dict[str, RasterBandConfig]

    @field_validator("bbox")
    @classmethod
    def bbox_has_four_elements(cls, v: List[float]) -> List[float]:
        if len(v) != 4:
            raise ValueError(f"bbox must have 4 elements, got {len(v)}")
        west, south, east, north = v
        if west > east:
            raise ValueError(f"bbox west ({west}) > east ({east})")
        if south > north:
            raise ValueError(f"bbox south ({south}) > north ({north})")
        return v

    @field_validator("license")
    @classmethod
    def license_is_spdx(cls, v: str) -> str:
        if not SPDX_PATTERN.match(v):
            raise ValueError(
                f"license '{v}' is not a valid SPDX identifier "
                f"(must match ^[\\w\\-\\.+]+$)"
            )
        return v

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("keywords must not be empty")
        return v

    @model_validator(mode="after")
    def links_have_cite_as(self) -> "ProductConfig":
        rels = {link.rel for link in self.links}
        if "cite-as" not in rels:
            raise ValueError(
                f"Product '{self.id}' has no 'cite-as' link. "
                f"Add a DOI or citation link."
            )
        return self

    @model_validator(mode="after")
    def raster_bands_match_variables(self) -> "ProductConfig":
        variables = set(self.summaries.variables)
        band_names = set(self.raster_bands.keys())
        missing = variables - band_names
        if missing:
            raise ValueError(
                f"Product '{self.id}': variables {sorted(missing)} "
                f"are in summaries but missing from raster_bands"
            )
        return self

    @model_validator(mode="after")
    def temporal_order(self) -> "ProductConfig":
        if self.start_datetime > self.end_datetime:
            raise ValueError(f"Product '{self.id}': start_datetime > end_datetime")
        return self


def validate_product_config(cfg: dict) -> ProductConfig:
    """Validate a product config dict. Raises ValidationError on failure."""
    return ProductConfig.model_validate(cfg)
