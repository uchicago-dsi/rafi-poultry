import pandas as pd
import geopandas as gpd
from pathlib import Path
from fuzzywuzzy import fuzz
from datetime import datetime
import os
import requests
from tqdm import tqdm
from typing import List, Tuple
from shapely.geometry import Polygon
import numpy as np
import argparse

from constants import CLEAN_DIR, RAW_DIR
from utils import save_file

# TODO: uh...
MAPBOX_KEY = os.getenv("MAPBOX_API")


tqdm.pandas()


def get_isochrone(row, driving_dist_miles: int, token: str):
    """TODO: rewrite this...
    Adds plant isochrones to fsis dataframe; captures area that is within
            an x mile radius of the plant. 90 percent of all birds were
            produced on farms within 60 miles of the plant, according to 2011
            ARMS data.

    Args:
        coords: list of tuples; lat and long for all processing plants.
        driving_dist_miles: int; radius of captured area (in driving distance).
        token: str; API token to access mapbox.

    Returns:
        list of plant isochrones

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
    response = requests.get(url)
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


def get_plant_isochrones(gdf_fsis, dist=60, token=MAPBOX_KEY):
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
    os.makedirs(RUN_DIR, exist_ok=True)

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
