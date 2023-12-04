"""Contains functions to match the sales volume data of processing plants 
from Infogroup 2022 data to the FSIS dataset, based on address and location. 
"""

import pandas as pd
import numpy as np
from tqdm import tqdm
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path
from constants import (CLEANED_MATCHED_PLANTS_FPATH, 
                       CLEANED_INFOGROUP_FPATH, 
                       CLEANED_FSIS_PROCESSORS_FPATH,
)

def address_match(infogroup_path: Path, 
                  fsis_path: Path, 
                  fuzz_ratio: float=75) -> pd.DataFrame:
    """Takes a cleaned FSIS and Infogroup dataset. Outputs a new dataset that combines the 
    Infogroup and sales volume data with the base FSIS dataset

    Args:
        infogroup_2022_path: relative path to the raw data folder with the 
            2022 Infogroup dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        fuzz_ratio: float; minimum "fuzziness" (or similarity) score 
            to accept that two strings are "the same"; default of 75

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
    
    df_poultry = pd.read_csv(fsis_path, index_col=0)
    df_poultry["Sales Volume (Location)"] = np.NaN
    df_poultry["Sales Volume (Location)"] = np.NaN

    for i, fsis in tqdm(df_poultry.iterrows(), total=len(df_poultry)):
        fsis_address = fsis["Full Address"].lower()
        for k, infogroup in df_filtered.iterrows():
            infogroup_address = infogroup["Full Address"].lower()
            if fuzz.token_sort_ratio(infogroup_address, fsis_address) > fuzz_ratio:
                df_poultry.loc[i, "Sales Volume (Location)"] = infogroup[
                    "SALES VOLUME (9) - LOCATION"
                ]
                break

    return df_poultry


def loc_match(no_match: pd.DataFrame, 
              pp_2022: pd.DataFrame, 
              pp_sales: pd.DataFrame, 
              threshold: float) -> (pd.DataFrame, pd.DataFrame):
    """Match 2022 Infogroup plants to the remaining unmatched FSIS plants 
    after running address_match based on longitude/latitude 
    to add sales volume data to each poultry plant from FSIS. 
    Requires user input when a match is found.

    Args:
        no_match: Filtered DataFrame that contains the unmatched poultry plants 
            after running address_match.
        pp_2022: 2022 Infogroup dataset loaded as a DataFrame.
        pp_sales: DataFrame returned by address_match, which contains 
            FSIS poultry plants matched with sales volume.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        2022 Infogroup DataFrame (pp_2022) and DataFrame with sales volume data 
        filled in for location matches (pp_sales).

    """
    no_match_nulls = no_match[no_match["Sales Volume (Location)"].isna()]
    for index, row in no_match_nulls.iterrows():
        target_point = (row["latitude"], row["longitude"])
        for _, infogroup in pp_2022.iterrows():
            candidate_point = infogroup["LATITUDE"], infogroup["LONGITUDE"]
            distance = haversine(
                target_point[1], 
                target_point[0], 
                candidate_point[1], 
                candidate_point[0]
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


def save_all_matches(infogroup_path: Path, 
                     fsis_path: Path, 
                     threshold: float=5) -> None:
    """Executes all three matching helper functions and saves final fully 
    updated sales volume DataFrame as a CSV.

    Args:
        infogroup_2022_path: relative path to the raw data folder 
            with the 2022 Infogroup dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        N/A, saves updated CSV to the cleaned data folder.
    """
    address_matches = address_match(infogroup_path, fsis_path, 75)
    no_match = address_matches[address_matches["Sales Volume (Location)"].isna()]
    
    infogroup = pd.read_csv(infogroup_path)
    pp_2022 = infogroup[infogroup["ARCHIVE VERSION YEAR"] == 2022]
    pp_2022, pp_sales = loc_match(no_match, pp_2022, address_matches, threshold)
    
    pp_sales = pp_sales.dropna(subset=["Parent Corporation"])
    pp_sales.to_csv(CLEANED_MATCHED_PLANTS_FPATH)