"""Get FSIS plant isochrones using the Mapbox API"""

import argparse
import os
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import requests
from constants import CLEAN_DIR
from shapely.geometry import Polygon
from tqdm import tqdm

from pipeline.rafi.utils import save_file

# TODO: uh...
MAPBOX_KEY = os.getenv("MAPBOX_API")


tqdm.pandas()


def get_isochrone(
    row: gpd.GeoSeries, driving_dist_miles: int, token: str, timeout: int = 60
) -> gpd.GeoSeries:
    """Adds plant isochrones to fsis dataframe; captures area that is within an x mile radius of the plant. 90 percent of all birds were produced on farms within 60 miles of the plant, according to 2011 ARMS data.

    Args:
        row: GeoSeries containing plant location data.
        driving_dist_miles: Radius of captured area (in driving distance) in miles.
        token: API token to access mapbox.
        timeout: Time in seconds before request times out.

    Returns:
        GeoSeries with added isochrone geometry.
    """
    ENDPOINT = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
    DRIVING_DISTANCE_METERS = str(
        int(driving_dist_miles * 1609.34)
    )  # turns miles into meters

    lat = row["geometry"].y
    lng = row["geometry"].x
    url = (
        ENDPOINT
        + str(lng)
        + ","
        + str(lat)
        + "?"
        + "contours_meters="
        + DRIVING_DISTANCE_METERS
        + "&access_token="
        + token
    )
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as e:
        raise Exception(
            f"Request to Mapbox API timed out after {timeout} seconds."
        ) from e
    if not response.ok:
        raise Exception(
            f"Within the isochrone helper function, unable to \
                            access mapbox url using API token. Response \
                            had status code {response.status_code}. \
                            Error message was {response.text}"
        )

    # Note: use buffer(0) to clean up invalid geometries
    isochrone = Polygon(
        response.json()["features"][0]["geometry"]["coordinates"]
    ).buffer(0)
    row["isochrone"] = isochrone
    return row


def get_plant_isochrones(
    gdf_fsis: gpd.GeoDataFrame, dist: int = 60, token: str = MAPBOX_KEY
) -> gpd.GeoDataFrame:
    """Retrieves isochrones for each plant in the given GeoDataFrame.

    Args:
        gdf_fsis: GeoDataFrame containing plant location data.
        dist: Radius of captured area (in driving distance) in miles.
        token: API token to access mapbox.

    Returns:
        GeoDataFrame with isochrone geometries.
    """
    print("Getting isochrones...")
    gdf_fsis = gdf_fsis.progress_apply(
        lambda row: get_isochrone(row, dist, MAPBOX_KEY), axis=1
    )
    gdf_fsis = gdf_fsis.drop("geometry", axis=1).set_geometry("isochrone")
    return gdf_fsis


if __name__ == "__main__":
    RUN_DIR = (
        CLEAN_DIR / f"fsis_isochrones_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    Path.mkdir(RUN_DIR, exist_ok=True, parents=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_test", action="store_true")

    args = parser.parse_args()

    SMOKE_TEST = args.smoke_test

    # TODO: do this better...maybe an arg or set up a dir with files I can use?
    fsis_path = CLEAN_DIR / "_clean_run" / "plants.geojson"
    gdf_fsis = gpd.read_file(fsis_path)

    if SMOKE_TEST:
        gdf_fsis = gdf_fsis.iloc[:10]

    gdf_fsis_isochrones = get_plant_isochrones(gdf_fsis)

    save_file(
        gdf_fsis_isochrones, RUN_DIR / "plants_with_isochrones.geojson", gzip_file=True
    )
