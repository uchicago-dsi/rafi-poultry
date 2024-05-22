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

# Enable pandas progress bars for apply functions
tqdm.pandas()

current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/"
DATA_DIR_RAW = DATA_DIR / "raw/"
DATA_DIR_CLEAN = DATA_DIR / "clean/"
RUN_DIR = DATA_DIR_CLEAN / f"fsis_match_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
os.makedirs(RUN_DIR, exist_ok=True)

# TODO: set filename in config for data files
FSIS_PATH = DATA_DIR_RAW / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
NETS_PATH = DATA_DIR_RAW / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
NETS_NAICS_PATH = DATA_DIR_RAW / "nets" / "NAICS2022_RAFI.csv"

# This is used for string matching
FSIS2NETS_CORPS = {
    "House of Raeford Farms of LA": "Raeford Farms Louisiana",
    "Mar-Jac Poultry-AL": "MARSHALL DURBIN FOOD CORP",
    "Mar-Jac Poultry-MS": "MARSHALL DURBIN FOOD CORP",
    "Perdue Foods, LLC": "PERDUE FARMS INC",
}


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


def fsis_match(gdf_fsis, gdf_nets):
    # Note: rows are filtered geospatially so can set address and company threshold somewhat low
    gdf_nets = gdf_nets.to_crs(9822)
    gdf_fsis = gdf_fsis.to_crs(9822)
    buffer = 1000  # TODO...
    gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(buffer)

    print("Getting geospatial matches...")
    gdf_fsis = gdf_fsis.progress_apply(
        lambda row: get_geospatial_matches(row, gdf_nets), axis=1
    )

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
        "zip": "zip_fsis",
        "activities": "activities_fsis",
        "dbas": "dbas_fsis",
        "size": "size_fsis",
        "latitude": "latitude_fsis",
        "longitude": "longitude_fsis",
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

    CORP2PARENT = {
        "Tyson": "Tyson",
        "JBS": "JBS",
        "Cargill": "Cargill",
        "Foster Farms": "Foster Farms",
        "Peco Foods": "Peco Foods",
        "Sechler": "Sechler Family Foods, Inc.",
        "Raeford": "House of Raeford",
        "Koch Foods": "Koch Foods",
        "Perdue": "Perdue",
        "Fieldale": "Fieldale Farms Corporation",
        "Amick": "Amick",
        "George's": "George's",
        "Mar-Jac": "Mar-Jac",
        "Harim": "Harim Group",
        "Costco": "Costco",
        "Aterian": "Aterian Investment Partners",
        "Pilgrim's Pride": "Pilgrim's Pride",
        "Mountaire": "Mountaire",
        "Bachoco": "Bachoco OK Foods",
        "Wayne Farms": "Wayne Farms",
        "Hillshire": "Hillshire",
        "Butterball": "Butterball",
        "Case Farms": "Case Farms",
        "Foster": "Foster Poultry Farms",
        "Sanderson": "Sanderson Farms, Inc.",
        "Harrison": "Harrison Poultry, Inc.",
        "Farbest": "Farbest Foods, Inc.",
        "Jennie-O": "Jennie-O",
        "Keystone": "Keystone",
        "Simmons": "Simmons Prepared Foods, Inc.",
        "JCG": "Cagles, Inc.",
        "Norman": "Norman W. Fries, Inc.",
    }

    def map_to_corporation(name, corp_mapping=CORP2PARENT):
        for key in corp_mapping:
            if key.lower() in name.lower():
                return corp_mapping[key]
        return "Other"

    merged["parent_corp_manual"] = merged["establishment_name_fsis"].apply(
        map_to_corporation
    )

    KEEP_COLS = [
        "duns_number_fsis",
        "duns_number_nets",
        "parent_corp_manual",
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

    # Select top match for each plant
    output = merged.groupby(["establishment_name_fsis", "street_fsis"]).head(1).copy()

    def calculate_sales(row, avg_sales):
        if pd.isna(row["sales_here_nets"]):
            row["display_sales"] = avg_sales[row["parent_corp_manual"]]
        else:
            row["display_sales"] = row["sales_here_nets"]

        # Handle zero, unreasonably low, or missing sales data
        if row["display_sales"] < 1000 or pd.isna(row["display_sales"]):
            row["display_sales"] = avg_sales[
                "Other"
            ]  # TODO: This is maybe a bad assumption since sales here are large...
        return row

    # Get average sales for each parent corporation
    avg_sales = output.groupby("parent_corp_manual")["sales_here_nets"].mean()

    # Calculate display sales data
    output = output.apply(lambda row: calculate_sales(row, avg_sales), axis=1)
    output[KEEP_COLS + ["display_sales"]].to_csv(RUN_DIR / "output.csv", index=False)

    # Save unmatched plants separately for review
    unmatched = output[output.match_score == 0]
    unmatched[KEEP_COLS].to_csv(RUN_DIR / "unmatched.csv", index=False)

    output_geojson = output.copy()
    output_geojson["geometry"] = output.apply(
        lambda row: Point(row["longitude_fsis"], row["latitude_fsis"]), axis=1
    )

    GEOJSON_RENAME_COLS = {
        "parent_corp_manual": "Parent Corporation",
        "establishment_name_fsis": "Establishment Name",
        "street_fsis": "Address",
        "city_fsis": "City",
        "state_fsis": "State",
        "zip_fsis": "Zip",
        "display_sales": "Sales",
    }
    output_geojson = output_geojson.rename(columns=GEOJSON_RENAME_COLS)

    GEOJSON_COLS = [col for col in GEOJSON_RENAME_COLS.values()] + ["geometry"]
    output_geojson = gpd.GeoDataFrame(output_geojson, geometry=output_geojson.geometry)
    output_geojson[GEOJSON_COLS].to_file(RUN_DIR / "plants.geojson", driver="GeoJSON")

    return output_geojson[GEOJSON_COLS]


if __name__ == "__main__":
    # TODO: separate saving data from the fsis_match function
    fsis_match()
    # print("Loading data...")
    # df_nets = pd.read_csv(
    #     NETS_PATH,
    #     sep="\t",
    #     encoding="latin-1",
    #     dtype={"DunsNumber": str},
    #     low_memory=False,
    # )
    # df_nets_naics = pd.read_csv(
    #     NETS_NAICS_PATH,
    #     dtype={"DunsNumber": str},
    #     low_memory=False,
    # )
    # df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")
    # gdf_nets = gpd.GeoDataFrame(
    #     df_nets,
    #     geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude),
    #     crs=4326,
    # )

    # df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
    # df_fsis = clean_fsis(df_fsis)
    # gdf_fsis = gpd.GeoDataFrame(
    #     df_fsis,
    #     geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
    #     crs=4326,
    # )

    # # Note: rows are filtered geospatially so can set address and company threshold somewhat low
    # gdf_nets = gdf_nets.to_crs(9822)
    # gdf_fsis = gdf_fsis.to_crs(9822)
    # buffer = 1000  # TODO...
    # gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(buffer)

    # print("Getting geospatial matches...")
    # gdf_fsis = gdf_fsis.progress_apply(
    #     lambda row: get_geospatial_matches(row, gdf_nets), axis=1
    # )

    # # Reset geospatial index to WGS84
    # gdf_fsis = gdf_fsis.to_crs(4326)

    # merged_spatial = gdf_fsis.explode("spatial_match_index").merge(
    #     gdf_nets,
    #     left_on="spatial_match_index",
    #     right_index=True,
    #     suffixes=("_fsis", "_nets"),
    #     how="left",
    # )

    # # TODO: do I care about duplicates here or not really?
    # merged_duns = gdf_fsis.merge(
    #     gdf_nets,
    #     left_on="duns_number",
    #     right_on="DunsNumber",
    #     how="inner",
    #     suffixes=("_fsis", "_nets"),
    # )

    # merged = pd.concat([merged_spatial, merged_duns])

    # # Fill in match columns for selecting the best match
    # merged = merged.apply(lambda row: get_string_matches(row), axis=1)

    # # Roundabout way of doing this to prevent fragmented DataFrame warning
    # duns_match = pd.DataFrame(
    #     {"duns_match": merged["duns_number"] == merged["DunsNumber"]}
    # )
    # merged = pd.concat([merged, duns_match], axis=1)
    # merged["match_score"] = (
    #     merged[
    #         [
    #             "spatial_match",
    #             "company_match",
    #             "address_match",
    #             "duns_match",
    #             "alt_name_match",
    #         ]
    #     ]
    #     .fillna(False)
    #     .sum(axis=1)
    # )

    # # Column renaming dictionary
    # RENAME_DICT = {
    #     # FSIS columns
    #     "establishment_name": "establishment_name_fsis",
    #     "duns_number": "duns_number_fsis",
    #     "street": "street_fsis",
    #     "city": "city_fsis",
    #     "state": "state_fsis",
    #     "zip": "zip_fsis",
    #     "activities": "activities_fsis",
    #     "dbas": "dbas_fsis",
    #     "size": "size_fsis",
    #     "latitude": "latitude_fsis",
    #     "longitude": "longitude_fsis",
    #     # NETS columns
    #     "DunsNumber": "duns_number_nets",
    #     "Company": "company_nets",
    #     "TradeName": "trade_name_nets",
    #     "Address": "address_nets",
    #     "City": "city_nets",
    #     "State": "state_nets",
    #     "HQDuns": "hq_duns_nets",
    #     "HQCompany": "hq_company_nets",
    #     "SalesHere": "sales_here_nets",
    # }
    # merged = merged.rename(columns=RENAME_DICT)

    # CORP2PARENT = {
    #     "Tyson": "Tyson",
    #     "JBS": "JBS",
    #     "Cargill": "Cargill",
    #     "Foster Farms": "Foster Farms",
    #     "Peco Foods": "Peco Foods",
    #     "Sechler": "Sechler Family Foods, Inc.",
    #     "Raeford": "House of Raeford",
    #     "Koch Foods": "Koch Foods",
    #     "Perdue": "Perdue",
    #     "Fieldale": "Fieldale Farms Corporation",
    #     "Amick": "Amick",
    #     "George's": "George's",
    #     "Mar-Jac": "Mar-Jac",
    #     "Harim": "Harim Group",
    #     "Costco": "Costco",
    #     "Aterian": "Aterian Investment Partners",
    #     "Pilgrim's Pride": "Pilgrim's Pride",
    #     "Mountaire": "Mountaire",
    #     "Bachoco": "Bachoco OK Foods",
    #     "Wayne Farms": "Wayne Farms",
    #     "Hillshire": "Hillshire",
    #     "Butterball": "Butterball",
    #     "Case Farms": "Case Farms",
    #     "Foster": "Foster Poultry Farms",
    #     "Sanderson": "Sanderson Farms, Inc.",
    #     "Harrison": "Harrison Poultry, Inc.",
    #     "Farbest": "Farbest Foods, Inc.",
    #     "Jennie-O": "Jennie-O",
    #     "Keystone": "Keystone",
    #     "Simmons": "Simmons Prepared Foods, Inc.",
    #     "JCG": "Cagles, Inc.",
    #     "Norman": "Norman W. Fries, Inc.",
    # }

    # def map_to_corporation(name, corp_mapping=CORP2PARENT):
    #     for key in corp_mapping:
    #         if key.lower() in name.lower():
    #             return corp_mapping[key]
    #     return "Other"

    # merged["parent_corp_manual"] = merged["establishment_name_fsis"].apply(
    #     map_to_corporation
    # )

    # KEEP_COLS = [
    #     "duns_number_fsis",
    #     "duns_number_nets",
    #     "parent_corp_manual",
    #     "establishment_name_fsis",
    #     "company_nets",
    #     "street_fsis",
    #     "address_nets",
    #     "city_fsis",
    #     "city_nets",
    #     "state_fsis",
    #     "state_nets",
    #     "activities_fsis",
    #     "dbas_fsis",
    #     "size_fsis",
    #     "trade_name_nets",
    #     "hq_duns_nets",
    #     "hq_company_nets",
    #     "sales_here_nets",
    #     "spatial_match",
    #     "company_match",
    #     "address_match",
    #     "alt_name_match",
    #     "duns_match",
    #     "match_score",
    # ]

    # print("Saving files...")
    # merged = merged.sort_values(
    #     by=["establishment_name_fsis", "street_fsis", "match_score"],
    #     ascending=[True, True, False],
    # )
    # merged[KEEP_COLS].to_csv(RUN_DIR / "merged.csv", index=False)

    # # Select top match for each plant
    # output = merged.groupby(["establishment_name_fsis", "street_fsis"]).head(1).copy()

    # def calculate_sales(row, avg_sales):
    #     if pd.isna(row["sales_here_nets"]):
    #         row["display_sales"] = avg_sales[row["parent_corp_manual"]]
    #     else:
    #         row["display_sales"] = row["sales_here_nets"]

    #     # Handle zero, unreasonably low, or missing sales data
    #     if row["display_sales"] < 1000 or pd.isna(row["display_sales"]):
    #         row["display_sales"] = avg_sales[
    #             "Other"
    #         ]  # TODO: This is maybe a bad assumption since sales here are large...
    #     return row

    # # Get average sales for each parent corporation
    # avg_sales = output.groupby("parent_corp_manual")["sales_here_nets"].mean()

    # # Calculate display sales data
    # output = output.apply(lambda row: calculate_sales(row, avg_sales), axis=1)
    # output[KEEP_COLS + ["display_sales"]].to_csv(RUN_DIR / "output.csv", index=False)

    # # Save unmatched plants separately for review
    # unmatched = output[output.match_score == 0]
    # unmatched[KEEP_COLS].to_csv(RUN_DIR / "unmatched.csv", index=False)

    # output_geojson = output.copy()
    # output_geojson["geometry"] = output.apply(
    #     lambda row: Point(row["longitude_fsis"], row["latitude_fsis"]), axis=1
    # )

    # GEOJSON_RENAME_COLS = {
    #     "parent_corp_manual": "Parent Corporation",
    #     "establishment_name_fsis": "Establishment Name",
    #     "street_fsis": "Address",
    #     "city_fsis": "City",
    #     "state_fsis": "State",
    #     "zip_fsis": "Zip",
    #     "display_sales": "Sales",
    # }
    # output_geojson = output_geojson.rename(columns=GEOJSON_RENAME_COLS)

    # GEOJSON_COLS = [col for col in GEOJSON_RENAME_COLS.values()] + ["geometry"]
    # output_geojson = gpd.GeoDataFrame(output_geojson, geometry=output_geojson.geometry)
    # output_geojson[GEOJSON_COLS].to_file(RUN_DIR / "plants.geojson", driver="GeoJSON")
