import pandas as pd
import geopandas as gpd
from datetime import datetime
import os
from typing import List, Tuple
import argparse

from fsis_match import fsis_match
from get_plant_isochrones import get_plant_isochrones
from calculate_captured_areas import calculate_captured_areas
from filter_barns import filter_barns, save_barns
from constants import RAW_DIR, CLEAN_DIR


def clean_fsis(df):
    df = df.dropna(subset=["activities"])
    df = df[df.activities.str.lower().str.contains("poultry slaughter")]
    df = df[df["size"] == "Large"]
    df["duns_number"] = df["duns_number"].str.replace("-", "")
    df["matched"] = False
    return df


def pipeline(gdf_fsis, gdf_nets, gdf_barns, smoke_test=False):
    gdf_fsis = fsis_match(gdf_fsis, gdf_nets)
    gdf_fsis_isochrones = get_plant_isochrones(gdf_fsis)
    gdf_isochrones = calculate_captured_areas(gdf_fsis_isochrones)
    # TODO: maybe add something to skip filtering for testing
    gdf_barns = filter_barns(gdf_barns, gdf_isochrones, smoke_test=smoke_test)
    return gdf_fsis, gdf_fsis_isochrones, gdf_isochrones, gdf_barns


if __name__ == "__main__":
    RUN_DIR = (
        CLEAN_DIR / f"full_pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    os.makedirs(RUN_DIR, exist_ok=True)

    # TODO: set filename in config for data files
    FSIS_PATH = RAW_DIR / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
    NETS_PATH = RAW_DIR / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
    NETS_NAICS_PATH = RAW_DIR / "nets" / "NAICS2022_RAFI.csv"
    BARNS_PATH = RAW_DIR / "full-usa-3-13-2021_filtered_deduplicated.gpkg"

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_test", action="store_true")
    args = parser.parse_args()

    smoke_test = args.smoke_test

    # TODO: should maybe put these in functions also
    print("Loading data...")
    df_nets = pd.read_csv(
        NETS_PATH,
        sep="\t",
        encoding="latin-1",
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets_naics = pd.read_csv(
        NETS_NAICS_PATH,
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")
    gdf_nets = gpd.GeoDataFrame(
        df_nets,
        geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude),
        crs=4326,
    )

    df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
    df_fsis = clean_fsis(df_fsis)

    gdf_fsis = gpd.GeoDataFrame(
        df_fsis,
        geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
        crs=4326,
    )

    if smoke_test:
        gdf_fsis = gdf_fsis.sample(30)

    gdf_barns = gpd.read_file(BARNS_PATH)

    gdf_fsis, gdf_fsis_isochrones, gdf_isochrones, gdf_barns = pipeline(
        gdf_fsis, gdf_nets, gdf_barns, smoke_test
    )

    # TODO: maybe add a function to save these
    gdf_fsis.to_file(
        RUN_DIR / "plants.geojson",
        driver="GeoJSON",
    )
    gdf_fsis_isochrones.to_file(
        RUN_DIR / "plants_with_isochrones.geojson",
        driver="GeoJSON",
    )

    # Note: Handles saving barns as geojson and gzip
    save_barns(gdf_barns, RUN_DIR / "barns.geojson")
