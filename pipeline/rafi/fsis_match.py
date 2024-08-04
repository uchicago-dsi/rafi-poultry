"""Matches FSIS plants to NETS records using geospatial and string matching"""

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

#  TODO: this should maybe come from the config file
from constants import (
    CLEAN_DIR,
    RAW_DIR,
)
from fuzzywuzzy import fuzz
from shapely.geometry import Point
from tqdm import tqdm

from rafi.utils import save_file

# Enable pandas progress bars for apply functions
tqdm.pandas()

# TODO: move this to constants
# This is used for string matching
FSIS2NETS_CORPS = {
    "House of Raeford Farms of LA": "Raeford Farms Louisiana",
    "Mar-Jac Poultry-AL": "MARSHALL DURBIN FOOD CORP",
    "Mar-Jac Poultry-MS": "MARSHALL DURBIN FOOD CORP",
    "Perdue Foods, LLC": "PERDUE FARMS INC",
    "Cargill Meat Solutions": "CARGILL INCORPORATED",
}

EXCLUDE_CORPS = {
    "Butterball",
    "Jennie-O",
    "Kraft Heinz",
    "West Liberty",
    "Dakota Provisions",
    "Cooper Farms",
    "Farbest Foods",
    "Hillshire",
    "Plainville",
}
EXCLUDE_STRINGS_NETS = {
    "turkey",
    "cattle",
    "hatchery",
    "beef",
    "pig",
    "dlisted",
    "hog",
    "livestock exch",
    "pork",
    "saw sharpening",
    "livestock auction",
    "darling ingredients",
    "wehrmann genetics",
    "back road trucking",
}
TURKEY_PLANT_IDS = {
    "P850",  # Prestage
    "P18",  # Cargill
    "M13289+P963",  # Cargill
    "P286",  # Perdue
    "M89A+P9147",  # Hillshire
    "M18909+P157",  # Foster
}
KEEP_PLANT_IDS = {
    "P7374"  # Puerto Rico plant
}
CORP2PARENT = {
    "Tyson": "Tyson",
    "JBS": "JBS",
    "Cargill": "Cargill",
    "Foster Farms": "Foster Farms",
    "Peco Foods": "Peco Foods",
    "Sechler": "Sechler Family Foods",
    "Raeford": "House of Raeford",
    "Koch Foods": "Koch Foods",
    "Perdue": "Perdue",
    "Fieldale": "Fieldale Farms Corporation",
    "Amick": "Amick",
    "George's": "George's",
    "Ozark": "George's",
    "Mar-Jac": "Mar-Jac",
    "Harim": "Harim Group",
    "Costco": "Costco",
    "Aterian": "Aterian Investment Partners",
    "Pilgrim's Pride": "Pilgrim's Pride (JBS)",
    "To-Ricos": "Pilgrim's Pride (JBS)",
    "Mountaire": "Mountaire",
    "Bachoco": "Bachoco OK Foods",
    "Wayne Farms": "Wayne-Sanderson (Cargill)",
    "Hillshire": "Hillshire",
    "Case Farms": "Case Farms",
    "Foster": "Foster Poultry Farms",
    "Sanderson": "Wayne-Sanderson (Cargill)",
    "Harrison": "Harrison Poultry",
    "Farbest": "Farbest Foods",
    "Keystone": "Tyson",
    "Simmons": "Simmons Prepared Foods",
    "JCG": "Cagles",
    "Norman": "Norman W. Fries",
    # Other corps?
    "Soulshine": "Soulshine Farms",
    "Lincoln": "Lincoln Premium Poultry",
    "Prestage": "Prestage Foods",
    "Pitman": "Pitman Farms",
    "Plainville": "Plainville Brands",
    "Tip Top": "Tip Top Poultry",
    "Agri Star": "Agri Star Meat & Poultry",
    "Bell & Evans": "Bell & Evans",
    "Gerber": "Gerber Poultry",
    "Empire Kosher": "Empire Kosher Poultry",
    # Excluded corps
    "Kraft Heinz": "Kraft Heinz",
    "West Liberty": "West Liberty Foods",
    "Dakota": "Dakota Provisions",
    "Butterball": "Butterball",
    "Jennie-O": "Jennie-O",
    "Cooper": "Cooper Farms Processing",
}


# TODO: Move to utils?
def map_to_corporation(name, corp_mapping=CORP2PARENT):
    for key in corp_mapping:
        if key.lower() in name.lower():
            return corp_mapping[key]
    return "Other"


# merged["parent_corp_manual"] = merged["establishment_name_fsis"].apply(map_to_corporation)


def clean_fsis(
    df_fsis: pd.DataFrame,
    df_fsis_demo: pd.DataFrame,
    exclude_corps: set = EXCLUDE_CORPS,
    exclude_plant_ids: set = TURKEY_PLANT_IDS,
    keep_plant_ids: set = KEEP_PLANT_IDS,
) -> pd.DataFrame:
    """Cleans the FSIS data by dropping rows with missing activities, filtering for poultry slaughter and large size, and formatting DUNS numbers.

    Args:
        df_fsis: The FSIS DataFrame to clean.
        df_fsis_demo: The FSIS demographic DataFrame.
        exclude_corps: Set of corporations to exclude. These are known to be turkey, hatcheries, etc.
        exclude_plant_ids: Set of Plant IDs to exclude
        keep_plant_ids: Set of Plant IDs to keep (even if they are excluded by some criteria).

    Returns:
        The cleaned FSIS DataFrame.
    """
    df_fsis = df_fsis.merge(df_fsis_demo, on="establishment_number", how="left", suffixes=("", "_right"))
    dupe_cols = [col for col in df_fsis.columns if col.endswith("_right")]
    df_fsis = df_fsis.drop(columns=dupe_cols)

    # TODO: If we do exclude turkey processing, we'd do it here - ie processing_only_species == "Turkey"
    df_fsis = df_fsis[df_fsis["poultry_slaughter"] == "Yes"]
    df_fsis = df_fsis[~df_fsis["establishment_name"].str.contains("|".join(exclude_corps), case=False)]
    df_fsis["parent_corp_manual"] = df_fsis["establishment_name"].apply(map_to_corporation)

    df_fsis_clean = df_fsis.copy()

    # df_keep_plants = df_fsis_clean[df_fsis_clean["establishment_number"].isin(keep_plant_ids)]
    df_fsis_clean = df_fsis_clean[~df_fsis_clean["establishment_number"].isin(exclude_plant_ids)]

    df_fsis_clean = df_fsis_clean[df_fsis_clean["size"] == "Large"]
    # Note: Include plants not classified as large if they are part of a parent corporation that has large plants
    df_fsis_other_plants = df_fsis[
        (
            df_fsis["parent_corp_manual"].isin(set(df_fsis_clean["parent_corp_manual"].unique()))
            & (df_fsis["size"] != "Large")
        )
    ]

    df_fsis_clean = pd.concat([df_fsis_clean, df_fsis_other_plants]).drop_duplicates()

    df_fsis_clean["duns_number"] = df_fsis_clean["duns_number"].str.replace("-", "")
    df_fsis_clean["matched"] = False

    return df_fsis_clean


def clean_nets(
    df_nets: pd.DataFrame,
    exclude_strings: set = EXCLUDE_STRINGS_NETS,
    most_recent_year: int = 22,
) -> pd.DataFrame:
    """Cleans the NETS data by dropping rows containing excluded strings.

    Args:
        df_nets: The NETS DataFrame to clean.
        exclude_strings: Set of strings to exclude. Defaults to EXCLUDE_STRINGS_NETS.
        most_recent_year: The most recent year of NAICS data for filtering closed businesses

    Returns:
        The cleaned NETS DataFrame.
    """
    most_recent_year_col = f"Sales{most_recent_year}"
    df_nets = df_nets[~(df_nets[most_recent_year_col].isna())]
    exclude_pattern = "|".join(exclude_strings)
    df_nets = df_nets[
        ~df_nets["Company"].str.contains(exclude_pattern, case=False)
        & ~df_nets["TradeName"].str.contains(exclude_pattern, case=False)
    ]
    return df_nets


def get_geospatial_matches(row: pd.Series, gdf_child: gpd.GeoDataFrame, buffer: int = 1000) -> pd.Series:
    """Finds geospatial matches for a given row in the FSIS DataFrame within a specified buffer distance.

    Args:
        row: The row of the FSIS DataFrame.
        gdf_child: The GeoDataFrame of NETS records.
        buffer: The buffer distance in meters. Defaults to 1000.

    Returns:
        The row with added geospatial match information.
    """
    # TODO: wait...where do I use the buffer?
    # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
    # Then check whether they intersect with the buffered geometry
    possible_matches_index = list(gdf_child.sindex.intersection(row["buffered"].bounds))
    possible_matches = gdf_child.iloc[possible_matches_index]
    spatial_match_index = possible_matches[possible_matches.geometry.intersects(row["buffered"])].index.to_list()
    spatial_match = len(spatial_match_index) > 0
    # Handle unmatched plants — save -1 so they still show up in merge later
    row["spatial_match_index"] = spatial_match_index if spatial_match else [-1]
    row["spatial_match"] = spatial_match
    return row


def spatial_index_match(row: pd.Series, gdf_child: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Finds all spatial matches for a given row in the FSIS DataFrame.

    Args:
        row: The row of the FSIS DataFrame.
        gdf_child: The GeoDataFrame of NETS records.

    Returns:
        The GeoDataFrame of possible matches.
    """
    # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
    # Then check whether they intersect with the buffered geometry
    possible_matches_index = list(gdf_child.sindex.intersection(row["buffered"].bounds))
    possible_matches = gdf_child.iloc[possible_matches_index]
    spatial_matches = possible_matches[possible_matches.geometry.intersects(row["buffered"])]
    return spatial_matches


def get_string_matches(
    row: pd.Series,
    company_threshold: float = 60,
    address_threshold: float = 70,
) -> pd.Series:
    """Finds string matches for a given row in the FSIS DataFrame based on company and address similarity.

    Args:
        row: The row of the FSIS DataFrame.
        company_threshold: The threshold for company name matching.
        address_threshold: The threshold for address matching.

    Returns:
        The row with added string match information.
    """
    # Return if no matched NETS record
    if pd.isna(row["Company"]):
        return row

    row["company_match"] = (
        fuzz.token_sort_ratio(row["establishment_name"].upper(), row["Company"].upper()) > company_threshold
    )
    row["address_match"] = fuzz.token_sort_ratio(row["street"].upper(), row["Address"].upper()) > address_threshold
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
    row["matched"] = row["company_match"] or row["address_match"] or row["establishment_name"]
    return row


def fsis_match(
    gdf_fsis: gpd.GeoDataFrame, gdf_nets: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame]:
    """Matches FSIS plants to NETS records using geospatial and string matching.

    Args:
        gdf_fsis: The GeoDataFrame of FSIS plants.
        gdf_nets: The GeoDataFrame of NETS records.

    Returns:
        The matched GeoDataFrame, unmatched DataFrame, and full match DataFrame.
    """
    # Note: rows are filtered geospatially so can set address and company threshold somewhat low
    gdf_nets = gdf_nets.to_crs(9822)
    gdf_fsis = gdf_fsis.to_crs(9822)
    buffer = 1000  # TODO...
    gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(buffer)

    print("Getting geospatial matches...")
    gdf_fsis = gdf_fsis.progress_apply(lambda row: get_geospatial_matches(row, gdf_nets), axis=1)

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

    # Note: Roundabout way of doing this to prevent fragmented DataFrame warning
    duns_match = pd.DataFrame({"duns_match": merged["duns_number"] == merged["DunsNumber"]})
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

    # TODO: Move to config/constants
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

    # TODO: Move to config/constants
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
        "EmpHere",
        "spatial_match",
        "company_match",
        "address_match",
        "alt_name_match",
        "duns_match",
        "match_score",
    ]

    merged = merged.sort_values(
        by=["establishment_name_fsis", "street_fsis", "match_score", "sales_here_nets"],
        ascending=[True, True, False, False],
    )

    merged["sales_per_emp"] = merged["sales_here_nets"] / merged["EmpHere"]

    # Note: HQ is direct NETS data, parent is manual RAFI mapping
    # TODO: What should we do with Tip Top issue?
    hq_sales_per_emp = merged.groupby("hq_company_nets")["sales_per_emp"].median()
    parent_sales_per_emp = merged.groupby("parent_corp_manual")["sales_per_emp"].median()

    # Select top match for each plant, handling ties by max sales
    output = merged.groupby(["establishment_name_fsis", "street_fsis"], as_index=False).first()

    def calculate_sales(row, hq_sales_per_emp, parent_sales_per_emp, overall_median_sales, employee_threshold=500):
        """TODO: Add more info

        FSIS large plants have minimum of 500 employees
        TODO: Puerto Rico plant is smaller...how to handle?
        """
        # If employees are larger than threshold, use NETS sales data
        if row["EmpHere"] > employee_threshold:
            row["display_sales"] = row["sales_here_nets"]
        # Otherwise, assume 500 employees and use average sales for parent corporation
        else:
            hq_company_nets = row["hq_company_nets"]
            parent_corp_manual = row["parent_corp_manual"]
            if hq_company_nets in hq_sales_per_emp and hq_company_nets != "DLISTED":
                sales_per_emp = hq_sales_per_emp[hq_company_nets]
            else:
                sales_per_emp = parent_sales_per_emp[parent_corp_manual]
            # TODO: Add a threshold here...if it's more than...something then use the overall median sales?
            row["display_sales"] = employee_threshold * sales_per_emp

        # Handle missing sales data
        if pd.isna(row["display_sales"]):
            row["display_sales"] = overall_median_sales  # TODO: Is this ok?
        return row

    overall_median_sales = output["sales_here_nets"].median()

    # Calculate display sales data
    output = output.apply(
        lambda row: calculate_sales(row, hq_sales_per_emp, parent_sales_per_emp, overall_median_sales), axis=1
    )

    # Save unmatched plants separately for review
    unmatched = output[output.match_score == 0]
    unmatched = unmatched[KEEP_COLS]

    output_geojson = output.copy()
    output_geojson["geometry"] = output.apply(lambda row: Point(row["longitude_fsis"], row["latitude_fsis"]), axis=1)

    GEOJSON_RENAME_COLS = {
        "parent_corp_manual": "Parent Corporation",
        "establishment_name_fsis": "Establishment Name",
        "street_fsis": "Address",
        "city_fsis": "City",
        "state_fsis": "State",
        "zip_fsis": "Zip",
        "size_fsis": "Size",
        "display_sales": "Sales",
        "EmpHere": "Employees (NETS)",
        "sales_here_nets": "Sales (NETS)",
        "sales_per_emp": "Sales Per Employee",
    }
    output_geojson = output_geojson.rename(columns=GEOJSON_RENAME_COLS)

    GEOJSON_COLS = list(GEOJSON_RENAME_COLS.values()) + ["geometry"]
    output_geojson = gpd.GeoDataFrame(output_geojson, geometry=output_geojson.geometry)
    # Note: Remove ZIP+4 from ZIP code when present
    output_geojson["Zip"] = output_geojson["Zip"].str.replace(r"-\d{4}$", "", regex=True)
    output_geojson = output_geojson[GEOJSON_COLS]

    # TODO: Has to be a better way...
    full_match = merged[KEEP_COLS]
    final_matched_plants = output[KEEP_COLS]

    return output_geojson, unmatched, full_match, final_matched_plants


if __name__ == "__main__":
    RUN_DIR = CLEAN_DIR / f"fsis_match_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    Path.mkdir(RUN_DIR, exist_ok=True, parents=True)

    current_dir = Path(__file__).parent
    config_file = current_dir / "config_filepaths.yaml"

    with Path.open(config_file) as file:
        config = yaml.safe_load(file)

    FSIS_PATH = RAW_DIR / config["input"]["fsis"]
    FSIS_DEMO_PATH = RAW_DIR / config["input"]["fsis_demo"]
    NETS_PATH = RAW_DIR / "nets" / config["input"]["nets"]
    NETS_NAICS_PATH = RAW_DIR / "nets" / config["input"]["nets_naics"]

    # TODO: Make a function for this
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

    # TODO: and this...
    df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
    df_fsis_demo = pd.read_csv(FSIS_DEMO_PATH)
    df_fsis = clean_fsis(df_fsis, df_fsis_demo)

    gdf_fsis = gpd.GeoDataFrame(
        df_fsis,
        geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
        crs=4326,
    )

    gdf_fsis, unmatched, full_match, final_matched_plants = fsis_match(gdf_fsis, gdf_nets)

    save_file(
        gdf_fsis,
        RUN_DIR / "plants.csv",
        file_format="csv",
    )

    save_file(
        gdf_fsis,
        RUN_DIR / "plants.geojson",
        file_format="geojson",
    )

    save_file(
        unmatched,
        RUN_DIR / "unmatched.csv",
        file_format="csv",
    )

    save_file(full_match, RUN_DIR / "full_match.csv", file_format="csv", index=True)

    save_file(
        final_matched_plants,
        RUN_DIR / "final_matched_plants.csv",
        file_format="csv",
    )
