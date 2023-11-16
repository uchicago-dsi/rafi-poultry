"""Contains functions to match the sales volume data of processing plants 
from Infogroup 2022 data to the FSIS dataset, based on address and location. 
"""

from tqdm import tqdm as tqdm_progress
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path
from constants import (CLEANED_MATCHED_PLANTS_FPATH, 
                       CLEANED_NETS_FPATH, 
                       CLEANED_FSIS_PROCESSORS_FPATH, 
)

def address_match(nets_path: Path, 
                        fsis_path: Path, 
                        fuzz_ratio: float=75, 
                        num_threads: int=4):
    """Takes a cleaned FSIS and NETS dataset. Outputs a new dataset that combines the 
    NETS parent corporation and sales volume data with the base FSIS dataset

    Args:
        fsis_path: relative path to the clean data folder with the 
            cleaned new fsis data.
        nets_path: relative path to the clean data folder with the 
            cleaned new nets data.
        fuzz_ratio: float; minimum "fuzziness" (or similarity) score 
            to accept that two strings are "the same"; default of 60
        num_threads: int; number of simultaneous threads to run using
            multi-threading on the fuzzy matching

    Returns:
        FSIS dataset including the NETS Parent Company and Sales columns.

    """

    fsis_df = pd.read_csv(fsis_path)
    nets_df = pd.read_csv(nets_path)

    fsis_df["Parent Corporation"] = np.NaN
    fsis_df["Sales Volume (Location)"] = np.NaN

    def standardize_address(address):
        replacements = {
            "circle": "cir",
            "drive": "dr",
            "avenue": "ave",
            "parkway": "pkwy",
            "road": "rd",
            "street": "st",
        }
        address = address.lower()
        for old, new in replacements.items():
            address = address.replace(old, new)
        return address

    # Extract the part of the address before the first comma: only want street address to match NETS
    fsis_df["Short Address"] = fsis_df["Full Address"].apply(lambda x: x.split(',')[0])

    # Apply standardization to FSIS short addresses
    fsis_df["Short Address"] = fsis_df["Short Address"].apply(standardize_address)

    def find_match(i, fsis_df, nets_df):
        fsis_address = fsis_df.at[i, "Short Address"].lower()
        for k, nets in nets_df.iterrows():
            nets_address = nets["ADDRESS"]
            if fuzz.token_sort_ratio(nets_address, fsis_address) > fuzz_ratio:
                return i, {
                    "Parent Corporation": nets["PARENT COMPANY"],
                    "Sales Volume (Location)": nets["SALESHERE"]
                }
        return i, {}

    # Iterating over each row in fsis_df and finding matches
    for i in tqdm_progress(fsis_df.index, desc="Matching Addresses"):
        _, result = find_match(i, fsis_df, nets_df)
        if result:
            fsis_df.at[i, "Parent Corporation"] = result["Parent Corporation"]
            fsis_df.at[i, "Sales Volume (Location)"] = result["Sales Volume (Location)"]

    return fsis_df


def loc_match(no_match: pd.DataFrame, 
              pp_nets: pd.DataFrame, 
              pp_sales: pd.DataFrame, 
              threshold: float) -> (pd.DataFrame, pd.DataFrame):
    """Match NETS plants to the remaining unmatched FSIS plants 
    after running address_match based on longitude/latitude 
    to add parent company and sales volume data to each poultry plant from FSIS. 
    Requires user input when a match is found.

    Args:
        no_match: Filtered DataFrame that contains the unmatched poultry plants 
            after running address_match.
        pp_nets: NETS dataset loaded as a DataFrame.
        pp_sales: DataFrame returned by address_match, which contains 
            FSIS poultry plants matched with sales volume.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        NETS DataFrame (pp_nets) and DataFrame with sales volume data 
        filled in for location matches (pp_sales).

    """
    no_match_nulls = no_match[no_match["Parent Corporation"].isna()]
    for index, row in no_match_nulls.iterrows():
        target_point = (row["latitude"], row["longitude"])
        for _, nets in pp_nets.iterrows():
            candidate_point = nets["LATITUDE"], nets["LONGITUDE"]
            distance = haversine(
                target_point[1], 
                target_point[0], 
                candidate_point[1], 
                candidate_point[0]
            )
            if distance <= threshold:
                if (
                    fuzz.token_sort_ratio(
                        row["Establishment Name"].upper(), nets["COMPANY"]
                    )
                    > 90
                ):
                    pp_sales.loc[index, "Sales Volume (Location)"] = nets[
                        "SALESHERE"
                    ]
                    pp_sales.loc[index, "Parent Corporation"] = nets[
                        "PARENT COMPANY"
                    ]
                    break

    return pp_sales


def save_all_matches(nets_path: Path, 
                     fsis_path: Path, 
                     threshold: float=5) -> None:
    """Executes match function.


    Args:
        nets_path: relative path to the raw data folder 
            with the NETS dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        N/A, saves updated CSV to the cleaned data folder.
    """
    address_matches = address_match(nets_path, fsis_path)
    no_match = address_matches[address_matches["Parent Corporation"].isna()]
    
    nets = pd.read_csv(nets_path)
    pp_sales = loc_match(no_match, nets, address_matches, threshold)
    pp_sales = pp_sales.dropna(subset=["Parent Corporation"])
    pp_sales.to_csv(CLEANED_MATCHED_PLANTS_FPATH)