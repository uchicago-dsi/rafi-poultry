"""Run full pipeline for RAFI project."""

import argparse
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from calculate_captured_areas import calculate_captured_areas
from constants import CLEAN_DIR, RAW_DIR
from filter_barns import filter_barns
from fsis_match import clean_fsis, clean_nets, fsis_match
from get_plant_isochrones import get_plant_isochrones

from rafi.utils import save_file


def pipeline(
    gdf_fsis: gpd.GeoDataFrame,
    gdf_nets: gpd.GeoDataFrame,
    gdf_barns: gpd.GeoDataFrame,
    smoke_test: bool = False,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Runs the full pipeline for the RAFI project.

    Args:
        gdf_fsis: GeoDataFrame of FSIS plants.
        gdf_nets: GeoDataFrame of NETS data.
        gdf_barns: GeoDataFrame of barns data.
        smoke_test: Boolean flag to run a smoke test with a smaller dataset.

    Returns:
        A tuple of GeoDataFrames: (gdf_fsis, gdf_fsis_isochrones, gdf_isochrones, gdf_barns).
    """
    # TODO: Do I want to also return and save intermediate files?
    gdf_fsis, _, _ = fsis_match(gdf_fsis, gdf_nets)
    gdf_fsis_isochrones = get_plant_isochrones(gdf_fsis)
    gdf_isochrones = calculate_captured_areas(gdf_fsis_isochrones)
    # TODO: maybe add something to skip filtering for testing
    gdf_barns = filter_barns(gdf_barns, gdf_isochrones, smoke_test=smoke_test)
    return gdf_fsis, gdf_fsis_isochrones, gdf_isochrones, gdf_barns


if __name__ == "__main__":
    RUN_DIR = (
        CLEAN_DIR / f"full_pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    Path.mkdir(RUN_DIR, exist_ok=True, parents=True)

    # TODO: set filename in config for data files
    FSIS_PATH = RAW_DIR / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
    NETS_PATH = RAW_DIR / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
    NETS_NAICS_PATH = RAW_DIR / "nets" / "NAICS2022_RAFI.csv"
    BARNS_PATH = RAW_DIR / "full-usa-3-13-2021_filtered_deduplicated.gpkg"

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_test", action="store_true")
    args = parser.parse_args()

    SMOKE_TEST = args.smoke_test

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
    df_nets = df_nets.merge(df_nets_naics, on="DunsNumber", how="left")
    df_nets = clean_nets(df_nets)
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

    if SMOKE_TEST:
        gdf_fsis = gdf_fsis.sample(30)

    gdf_barns = gpd.read_file(BARNS_PATH)

    gdf_fsis, gdf_fsis_isochrones, gdf_isochrones, gdf_barns = pipeline(
        gdf_fsis, gdf_nets, gdf_barns, SMOKE_TEST
    )

    save_file(gdf_fsis, RUN_DIR / "plants.geojson")
    save_file(gdf_isochrones, RUN_DIR / "isochrones.geojson", gzip_file=True)
    save_file(
        gdf_fsis_isochrones, RUN_DIR / "plants_with_isochrones.geojson", gzip_file=True
    )
    save_file(gdf_barns, RUN_DIR / "barns.geojson", gzip_file=True)
