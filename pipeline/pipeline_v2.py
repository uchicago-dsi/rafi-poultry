import pandas as pd
import geopandas as gpd
from pathlib import Path
from fuzzywuzzy import fuzz
from datetime import datetime
import os
import requests
from tqdm import tqdm
from typing import List, Tuple
from shapely.geometry import Polygon, Point
import numpy as np
import argparse

from fsis_match import fsis_match
from get_plant_isochrones import get_plant_isochrones
from calculate_captured_areas import calculate_captured_areas
from filter_barns import filter_barns

# TODO: constants & config
# maybe load the states globally since these get use in multiple files and the main pipeline?

current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/"
DATA_DIR_RAW = DATA_DIR / "raw/"
DATA_DIR_CLEAN = DATA_DIR / "clean/"
RUN_DIR = (
    DATA_DIR_CLEAN / f"full_pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
)
os.makedirs(RUN_DIR, exist_ok=True)

# TODO: set filename in config for data files
FSIS_PATH = DATA_DIR_RAW / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
NETS_PATH = DATA_DIR_RAW / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
NETS_NAICS_PATH = DATA_DIR_RAW / "nets" / "NAICS2022_RAFI.csv"


def clean_fsis(df):
    df = df.dropna(subset=["activities"])
    df = df[df.activities.str.lower().str.contains("poultry slaughter")]
    df = df[df["size"] == "Large"]
    df["duns_number"] = df["duns_number"].str.replace("-", "")
    df["matched"] = False
    return df


def pipeline(gdf_fsis, gdf_nets):
    # TODO: What about saving intermediate files? Go through and figure out how to save these (if at all)
    gdf_fsis = fsis_match(gdf_fsis, gdf_nets)
    gdf_fsis = get_plant_isochrones(gdf_fsis)
    gdf_single_corp, gdf_two_corps, gdf_three_plus_corps = calculate_captured_areas(
        gdf_fsis
    )

    # TODO: move the I/O out of here also...
    FILENAME = "../data/raw/full-usa-3-13-2021_filtered_deduplicated.gpkg"
    gdf_barns = gpd.read_file(FILENAME)

    # TODO: filepaths, load files, what do we want to do...
    # TODO: add something to skip filtering for testing
    gdf_barns = filter_barns(gdf_barns)

    return gdf_fsis, gdf_single_corp, gdf_two_corps, gdf_three_plus_corps, gdf_barns


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_test", action="store_true")
    args = parser.parse_args()
    smoke_test = args.smoke_test

    # TODO: how should I handle file I/O stuff
    nets_path = NETS_PATH
    nets_naics_path = NETS_NAICS_PATH
    fsis_path = FSIS_PATH

    # TODO: should maybe put these in functions also
    print("Loading data...")
    df_nets = pd.read_csv(
        nets_path,
        sep="\t",
        encoding="latin-1",
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets_naics = pd.read_csv(
        nets_naics_path,
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")
    gdf_nets = gpd.GeoDataFrame(
        df_nets,
        geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude),
        crs=4326,
    )

    df_fsis = pd.read_csv(fsis_path, dtype={"duns_number": str})
    df_fsis = clean_fsis(df_fsis)

    gdf_fsis = gpd.GeoDataFrame(
        df_fsis,
        geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
        crs=4326,
    )

    if smoke_test:
        gdf_fsis = gdf_fsis.sample(10)

    gdf_fsis, gdf_single_corp, gdf_two_corps, gdf_three_plus_corps, gdf_barns = (
        pipeline(gdf_fsis, gdf_nets)
    )

    gdf_fsis = gdf_fsis.drop("isochrone", axis=1)
    gdf_fsis.to_file(
        RUN_DIR / "plants.geojson",
        driver="GeoJSON",
    )
    gdf_single_corp.to_file(
        RUN_DIR / "single_corp.geojson",
        driver="GeoJSON",
    )
    gdf_two_corps.to_file(
        RUN_DIR / "two_corps.geojson",
        driver="GeoJSON",
    )
    gdf_three_plus_corps.to_file(RUN_DIR / "three_plus_corps.geojson", driver="GeoJSON")
    gdf_barns.to_file(RUN_DIR / "barns.geojson", driver="GeoJSON")
