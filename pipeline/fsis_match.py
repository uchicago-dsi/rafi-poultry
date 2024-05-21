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


PARENT_CORPS = {
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


def get_geospatial_match(
    row, gdf_child, address_threshold=0.7, company_threshold=0.7, buffer=1000
):
    spatial_matches = spatial_index_match(row, gdf_child)

    if spatial_matches.empty:
        # No NETS record within buffered geometry, FSIS plant is unmatched so return
        return row

    # row["spatial_match"] = True
    # row["spatial_matches"] = spatial_matches

    joined_spatial_matches = pd.merge(row.to_frame().T, spatial_matches, how="cross")
    joined_spatial_matches["spatial_match"] = True
    # TODO: This is still messed up when we save it...maybe save this some other way later
    # joined_spatial_matches["spatial_matches"] = spatial_matches.to_json()
    # joined_spatial_matches["spatial_matches"] = base64.b64encode(
    #     spatial_matches.to_json().encode()
    # ).decode()

    joined_spatial_matches = joined_spatial_matches.apply(
        lambda row: get_string_matches(
            row,
            address_threshold=address_threshold,
            company_threshold=company_threshold,
        ),
        axis=1,
    )

    matches = joined_spatial_matches[joined_spatial_matches.matched]

    if matches.empty:
        # TODO: This is actually not clear to me what we want to do here...I'd like to save the spatial matches for unmatched plants
        return row
    else:
        # TODO: Do we really just want the first one?
        return matches.iloc[0]


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
    if row["establishment_name"] in PARENT_CORPS:
        alt_name_match = (
            fuzz.token_sort_ratio(
                PARENT_CORPS.get(row["establishment_name"], "").upper(),
                row["Company"].upper(),
            )
            > company_threshold
        )
    row["alt_name_match"] = alt_name_match
    row["matched"] = (
        row["company_match"] or row["address_match"] or row["establishment_name"]
    )
    return row


# def get_isochrones(
#     coords: List[Tuple[float, float]], driving_dist_miles: float, token: str
# ) -> pd.DataFrame:
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

    # Note: buffer(0) can clean up invalid geometries
    isochrone = Polygon(
        response.json()["features"][0]["geometry"]["coordinates"]
    ).buffer(0)
    row["geometry"] = isochrone
    return row


if __name__ == "__main__":
    df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
    df_fsis = clean_fsis(df_fsis)

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

    print("Matching on DUNS Number")
    df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")

    # TODO: should prob just work with GDFs the whole time...

    # Merge FSIS and NETS data on NETS data
    df_duns = pd.merge(
        df_fsis, df_nets, left_on="duns_number", right_on="DunsNumber", how="inner"
    )
    df_fsis["matched"] = df_fsis["duns_number"].isin(df_nets["DunsNumber"])

    # Convert to GDF for spatial matching
    gdf_fsis = gpd.GeoDataFrame(
        df_fsis,
        geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
        crs=4326,
    )
    gdf_nets = gpd.GeoDataFrame(
        df_nets,
        geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude),
        crs=4326,
    )

    # Note: rows are filtered geospatially so can set address and company threshold somewhat low
    # TODO: Make sure this doesn't permanently change the CRS...
    gdf_nets = gdf_nets.to_crs(9822)
    gdf_fsis = gdf_fsis.to_crs(9822)
    buffer = 1000  # TODO...
    gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(buffer)

    gdf_fsis["spatial_match"] = False
    print("Getting geospatial matches...")
    gdf_fsis = gdf_fsis.apply(lambda row: get_geospatial_match(row, gdf_nets), axis=1)

    GET_ISOCHRONES = True
    SMOKE_TEST = True
    if GET_ISOCHRONES:
        if SMOKE_TEST:
            gdf_fsis = gdf_fsis.iloc[:10]
        gdf_fsis = gdf_fsis.to_crs(4326)
        dist = 60
        MAPBOX_KEY = os.getenv("MAPBOX_API")
        # TODO: may have a problem with the crs here

        print("Getting isochrones...")
        gdf_fsis = gdf_fsis.apply(
            lambda row: get_isochrone(row, dist, MAPBOX_KEY), axis=1
        )

        # gdf_fsis["Isochrone"] = get_isochrones(lats_and_longs, dist, MAPBOX_KEY)
        # gdf_fsis = gdf_fsis.set_geometry("isochrone")

    ordered_columns = df_fsis.columns.to_list() + df_nets.columns.to_list()
    misc_columns = [
        col
        for col in gdf_fsis.columns
        if col not in ordered_columns and col != "geometry"
    ]
    ordered_columns += misc_columns

    # TODO: Redo the column order so this is easy to review:
    # duns_number	establishment_name		street	DunsNumber	Company	Address
    # include match columns near the front
    # sales

    print("Saving files...")
    gdf_fsis[gdf_fsis.matched][ordered_columns].to_csv(
        RUN_DIR / "fsis_nets_matches.csv", index=False
    )
    gdf_fsis[~gdf_fsis.matched][ordered_columns].to_csv(
        RUN_DIR / "fsis_nets_unmatched.csv", index=False
    )

    # TODO: Get average sales values for unmatched plants
    # TODO: Check for plants with 0 sales also

    # TODO: Save as GeoJSON
    # TODO: Decide which columns to keep for web file
    KEEP_COLS = []

    # Convert numpy.bool_ columns to native Python bool
    for col in gdf_fsis.select_dtypes(include=[np.bool_]).columns:
        gdf_fsis[col] = gdf_fsis[col].astype(bool)

    # Convert objects to strings to avoid dtype issues when saving as GeoJSON
    for col in gdf_fsis.select_dtypes(include=[object]).columns:
        gdf_fsis[col] = gdf_fsis[col].astype(str)

    gdf_fsis.to_file(RUN_DIR / "fsis_nets_matches.geojson", driver="GeoJSON")
