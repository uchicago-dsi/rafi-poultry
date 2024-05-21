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
import base64
import numpy as np
import argparse

current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/"
DATA_DIR_RAW = DATA_DIR / "raw/"
DATA_DIR_CLEAN = DATA_DIR / "clean/"
RUN_DIR = DATA_DIR_CLEAN / f"pipeline_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
os.makedirs(RUN_DIR, exist_ok=True)

# TODO: set filename in config for data files
FSIS_PATH = DATA_DIR_RAW / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
NETS_PATH = DATA_DIR_RAW / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
NETS_NAICS_PATH = DATA_DIR_RAW / "nets" / "NAICS2022_RAFI.csv"


FSIS2NETS_CORPS = {
    "House of Raeford Farms of LA": "Raeford Farms Louisiana",
    "Mar-Jac Poultry-AL": "MARSHALL DURBIN FOOD CORP",
    "Mar-Jac Poultry-MS": "MARSHALL DURBIN FOOD CORP",
    "Perdue Foods, LLC": "PERDUE FARMS INC",
}


def clean_fsis(df):
    df = df.dropna(subset=["activities"])
    df = df[df.activities.str.lower().str.contains("poultry slaughter")]
    df = df[df["size"] == "Large"]
    df["duns_number"] = df["duns_number"].str.replace("-", "")
    df["matched"] = False
    return df


def get_geospatial_matches(row, gdf_child, buffer=1000):
    # TODO: wait...where do I use the buffer?
    # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
    # Then check whether they intersect with the buffered geometry
    possible_matches_index = list(gdf_child.sindex.intersection(row["buffered"].bounds))
    possible_matches = gdf_child.iloc[possible_matches_index]
    spatial_match_index = possible_matches[
        possible_matches.geometry.intersects(row["buffered"])
    ].index.to_list()
    spatial_match = len(spatial_match_index) > 0
    # Handle unmatched plants — save -1 so they still show up in merge later
    row["spatial_match_index"] = spatial_match_index if spatial_match else [-1]
    row["spatial_match"] = spatial_match
    return row


def spatial_index_match(row, gdf_child):
    # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
    # Then check whether they intersect with the buffered geometry
    possible_matches_index = list(gdf_child.sindex.intersection(row["buffered"].bounds))
    possible_matches = gdf_child.iloc[possible_matches_index]
    spatial_matches = possible_matches[
        possible_matches.geometry.intersects(row["buffered"])
    ]
    return spatial_matches


def get_string_matches(row, company_threshold=0.7, address_threshold=0.7):
    # Return if no matched NETS record
    if pd.isna(row["Company"]):
        return row

    row["company_match"] = (
        fuzz.token_sort_ratio(row["establishment_name"].upper(), row["Company"].upper())
        > company_threshold
    )
    row["address_match"] = (
        fuzz.token_sort_ratio(row["street"].upper(), row["Address"].upper())
        > address_threshold
    )
    # Initialize since not all establishments are in PARENT_CORPS
    alt_name_match = False
    if row["establishment_name"] in FSIS2NETS_CORPS:
        alt_name_match = (
            fuzz.token_sort_ratio(
                FSIS2NETS_CORPS.get(row["establishment_name"], "").upper(),
                row["Company"].upper(),
            )
            > company_threshold
        )
    row["alt_name_match"] = alt_name_match
    row["matched"] = (
        row["company_match"] or row["address_match"] or row["establishment_name"]
    )
    return row


def get_isochrone(row, driving_dist_miles: int, token: str):
    """Adds plant isochrones to fsis dataframe; captures area that is within
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

    lat = row["latitude"]
    lng = row["longitude"]
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke_test", action="store_true")
    parser.add_argument("--get_isochrones", action="store_true")

    args = parser.parse_args()

    GET_ISOCHRONES = args.get_isochrones
    SMOKE_TEST = args.smoke_test

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

    if GET_ISOCHRONES:
        if SMOKE_TEST:
            gdf_fsis = gdf_fsis.iloc[:10]
        dist = 60
        MAPBOX_KEY = os.getenv("MAPBOX_API")

        print("Getting isochrones...")
        gdf_fsis = gdf_fsis.apply(
            lambda row: get_isochrone(row, dist, MAPBOX_KEY), axis=1
        )

    # Note: rows are filtered geospatially so can set address and company threshold somewhat low
    gdf_nets = gdf_nets.to_crs(9822)
    gdf_fsis = gdf_fsis.to_crs(9822)
    buffer = 1000  # TODO...
    gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(buffer)

    print("Getting geospatial matches...")
    gdf_fsis = gdf_fsis.apply(lambda row: get_geospatial_matches(row, gdf_nets), axis=1)

    # Reset geospatial index to WGS84
    gdf_fsis = gdf_fsis.to_crs(4326)

    merged_spatial = gdf_fsis.explode("spatial_match_index").merge(
        gdf_nets,
        left_on="spatial_match_index",
        right_index=True,
        suffixes=("_fsis", "_nets"),
        how="left",
    )

    # TODO: do I care about duplicates here or not really?
    merged_duns = gdf_fsis.merge(
        gdf_nets,
        left_on="duns_number",
        right_on="DunsNumber",
        how="inner",
        suffixes=("_fsis", "_nets"),
    )

    merged = pd.concat([merged_spatial, merged_duns])

    # Fill in match columns for selecting the best match
    merged = merged.apply(lambda row: get_string_matches(row), axis=1)

    # Roundabout way of doing this to prevent fragmented DataFrame warning
    duns_match = pd.DataFrame(
        {"duns_match": merged["duns_number"] == merged["DunsNumber"]}
    )
    merged = pd.concat([merged, duns_match], axis=1)
    merged["match_score"] = (
        merged[
            [
                "spatial_match",
                "company_match",
                "address_match",
                "duns_match",
                "alt_name_match",
            ]
        ]
        .fillna(False)
        .sum(axis=1)
    )

    # Column renaming dictionary
    RENAME_DICT = {
        # FSIS columns
        "establishment_name": "establishment_name_fsis",
        "duns_number": "duns_number_fsis",
        "street": "street_fsis",
        "city": "city_fsis",
        "state": "state_fsis",
        "activities": "activities_fsis",
        "dbas": "dbas_fsis",
        "size": "size_fsis",
        # NETS columns
        "DunsNumber": "duns_number_nets",
        "Company": "company_nets",
        "TradeName": "trade_name_nets",
        "Address": "address_nets",
        "City": "city_nets",
        "State": "state_nets",
        "HQDuns": "hq_duns_nets",
        "HQCompany": "hq_company_nets",
        "SalesHere": "sales_here_nets",
    }
    merged = merged.rename(columns=RENAME_DICT)

    KEEP_COLS = [
        "duns_number_fsis",
        "duns_number_nets",
        "establishment_name_fsis",
        "company_nets",
        "street_fsis",
        "address_nets",
        "city_fsis",
        "city_nets",
        "state_fsis",
        "state_nets",
        "activities_fsis",
        "dbas_fsis",
        "size_fsis",
        "trade_name_nets",
        "hq_duns_nets",
        "hq_company_nets",
        "sales_here_nets",
        "spatial_match",
        "company_match",
        "address_match",
        "alt_name_match",
        "duns_match",
        "match_score",
    ]

    print("Saving files...")
    merged = merged.sort_values(
        by=["establishment_name_fsis", "street_fsis", "match_score"],
        ascending=[True, True, False],
    )
    merged[KEEP_COLS].to_csv(RUN_DIR / "merged.csv", index=False)

    # TODO: fill in missing sales data for unmatched plants
    # TODO: check for 0 sales data plants also

    # Save fully unmatched plants
    unmatched = merged[merged.match_score == 0]
    unmatched[KEEP_COLS].to_csv(RUN_DIR / "unmatched.csv", index=False)

    # Select top match for each plant and save
    output = merged.groupby(["establishment_name_fsis", "street_fsis"]).head(1).copy()
    output[KEEP_COLS].to_csv(RUN_DIR / "output.csv", index=False)

    # TODO: Decide which columns to keep for web file
    if GET_ISOCHRONES:
        output["geometry"] = output["isochrone"]
        output = gpd.GeoDataFrame(output, geometry=output.geometry)
        GEOJSON_COLS = KEEP_COLS + ["geometry"]
        output[GEOJSON_COLS].to_file(
            RUN_DIR / "fsis_nets_matches.geojson", driver="GeoJSON"
        )
