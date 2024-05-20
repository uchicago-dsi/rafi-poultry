import pandas as pd
import geopandas as gpd
from pathlib import Path
from fuzzywuzzy import fuzz
from datetime import datetime
import os


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

    row["spatial_match"] = True

    joined_spatial_matches = pd.merge(row.to_frame().T, spatial_matches, how="cross")

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
    gdf_fsis = gdf_fsis.apply(lambda row: get_geospatial_match(row, gdf_nets), axis=1)

    ordered_columns = df_fsis.columns.to_list() + df_nets.columns.to_list()
    misc_columns = [col for col in gdf_fsis.columns if col not in ordered_columns]
    ordered_columns += misc_columns

    gdf_fsis[gdf_fsis.matched][ordered_columns].to_csv(
        RUN_DIR / "fsis_nets_matches.csv", index=False
    )
    gdf_fsis[~gdf_fsis.matched][ordered_columns].to_csv(
        RUN_DIR / "fsis_nets_unmatched.csv", index=False
    )

    # TODO: Decide which columns to keep for web file
    KEEP_COLS = []
