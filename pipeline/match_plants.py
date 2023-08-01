"""Contains functions to match the sales volume data of processing plants from Infogroup 2022 data
to the FSIS dataset, based on address and location. 
"""

import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path

here = Path(__file__).resolve().parent


def address_match(infogroup_path, fsis_path, fuzz_ratio=75):
    """Filters FSIS dataset for poultry processing plants,
    then match 2022 Infogroup plants to FSIS plants based on address
    to add sales volume data to each poultry plant from FSIS.

    Args:
        infogroup_2022_path: relative path to the raw data folder with the 2022 Infogroup dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        fuzz_ratio: float; minimum "fuzziness" (or similarity) score to accept that two strings are "the same"
                default of 75

    Returns:
        DataFrame with sales volume data filled in for address matches.

    """
    infogroup = pd.read_csv(infogroup_path)
    df_filtered = infogroup[infogroup["ARCHIVE VERSION YEAR"] == 2022]
    df_filtered["Full Address"] = (
        df_filtered["ADDRESS LINE 1"]
        + ", "
        + df_filtered["CITY"]
        + ", "
        + df_filtered["STATE"]
        + " "
        + df_filtered["ZIPCODE"].astype(int).astype(str)
    )
    df_filtered["Full Address"] = df_filtered["Full Address"].astype(str)

    df_fsis = pd.read_csv(fsis_path, index_col=0)
    df_poultry = df_fsis[df_fsis["Animals Processed"].str.contains("Chicken")].copy()
    df_poultry["Sales Volume (Location)"] = np.NaN
    df_poultry["Sales Volume (Location)"] = np.NaN

    for i, fsis in df_poultry.iterrows():
        fsis_address = fsis["Full Address"].lower()
        for k, infogroup in df_filtered.iterrows():
            infogroup_address = infogroup["Full Address"].lower()
            if fuzz.token_sort_ratio(infogroup_address, fsis_address) > fuzz_ratio:
                df_poultry.loc[i, "Sales Volume (Location)"] = infogroup[
                    "SALES VOLUME (9) - LOCATION"
                ]
                break

    return df_poultry


def loc_match(no_match, pp_2022, pp_sales, threshold):
    """Match 2022 Infogroup plants to the remaining unmatched FSIS plants after running
    address_match based on longitude/latitude to add sales volume data
    to each poultry plant from FSIS. Requires user input when a match is found.

    Args:
        no_match: Filtered DataFrame that contains the unmatched poultry plants after running address_match.
        pp_2022: 2022 Infogroup dataset loaded as a DataFrame.
        pp_sales: DataFrame returned by address_match, which contains FSIS poultry plants matched with sales volume.
        threshold: threshold for maximum distance possible to be considered a match.

    Returns:
        2022 Infogroup DataFrame (pp_2022) and
        DataFrame with sales volume data filled in for location matches (pp_sales).

    """
    no_match_nulls = no_match[no_match["Sales Volume (Location)"].isna()]
    for index, row in no_match_nulls.iterrows():
        target_point = (row["latitude"], row["longitude"])
        for j, infogroup in pp_2022.iterrows():
            candidate_point = infogroup["LATITUDE"], infogroup["LONGITUDE"]
            distance = haversine(
                target_point[1], target_point[0], candidate_point[1], candidate_point[0]
            )
            if distance <= threshold:
                if (
                    fuzz.token_sort_ratio(
                        row["Establishment Name"].upper(), infogroup["COMPANY"]
                    )
                    > 90
                ):
                    pp_sales.loc[index, "Sales Volume (Location)"] = infogroup[
                        "SALES VOLUME (9) - LOCATION"
                    ]
                    break
    return pp_2022, pp_sales


def fill_remaining_nulls(pp_sales):
    """Fills in sales volume for all remaining unmatched plants after running loc_match function
    with the median of the sales volume of all matched plants so far for each plant,
    based on its respective parent corporation.

    Args:
        pp_sales: DataFrame returned by loc_match, which contains FSIS poultry plants matched with sales volume.

    Returns:
        DataFrame with all sales volume data filled in.

    """
    median = (
        pp_sales.groupby(["Parent Corporation"])["Sales Volume (Location)"]
        .median()
        .reset_index()
    )
    median_sales = pp_sales["Sales Volume (Location)"].median()

    median["Sales Volume (Location)"] = median["Sales Volume (Location)"].fillna(
        median_sales
    )
    median["Sales Volume (Location)"] = median["Sales Volume (Location)"].replace(
        0, median_sales
    )

    parent_dict = dict(zip(median["Parent Corporation"], median["Sales Volume (Location)"]))

    pp_sales_updated = pp_sales.copy()

    for index, row in pp_sales_updated.iterrows():
        if np.isnan(row["Sales Volume (Location)"]):
            parent = row["Parent Corporation"]
            pp_sales_updated.loc[index, "Sales Volume (Location)"] = parent_dict[parent]

    return pp_sales_updated


def save_all_matches(infogroup_path, fsis_path, threshold):
    """Executes all three matching helper functions and saves final fully updated sales volume DataFrame
    as a CSV.

    Args:
        infogroup_2022_path: relative path to the raw data folder with the 2022 Infogroup dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        threshold: threshold for maximum distance possible to be considered a match.

    Returns:
        N/A, saves updated CSV to the cleaned data folder.
    """
    address_matches = address_match(infogroup_path, fsis_path, 75)
    no_match = address_matches[address_matches["Sales Volume (Location)"].isna()]

    infogroup = pd.read_csv(infogroup_path)
    pp_2022 = infogroup[infogroup["ARCHIVE VERSION YEAR"] == 2022]
    pp_2022, pp_sales = loc_match(no_match, pp_2022, address_matches, threshold)

    pp_sales_updated = fill_remaining_nulls(pp_sales)
    pp_sales_updated.to_csv(here.parent / "data/clean/cleaned_matched_plants.csv")


if __name__ == "__main__":
    save_all_matches(
        here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv",
        here.parent / "data/raw/fsis-processors-with-location.csv",
        5,
    )
