"""Contains functions to match the sales volume data of processing plants 
from Infogroup 2022 data to the FSIS dataset, based on address and location. 
"""

from tqdm import tqdm
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path
from constants import (
    CLEANED_MATCHED_PLANTS_FPATH,
)


def address_match(
    nets_path: Path,
    fsis_path: Path,
    fuzz_ratio: float = 75,
    tier2_ratio: float = 60,
):
    """
    Processes and matches FSIS dataset with the NETS dataset based on address and company information.
    It employs a tiered fuzzy matching approach to maximize the number of accurate matches.

    The first tier matches based on the street address with a higher fuzziness threshold.
    If no match is found, the second tier attempts to match based on the company name combined
    with city and state at a specified fuzziness threshold.

    Args:
        fsis_path (Path): Relative path to the clean data folder with the cleaned FSIS data.
        nets_path (Path): Relative path to the clean data folder with the cleaned NETS data.
        fuzz_ratio (float): Minimum fuzziness score for the primary matching; default is 75.
        tier2_ratio (float): Fuzziness score for the secondary tier of matching; default is 60.
        num_threads (int): Number of threads for parallel processing; currently not implemented.

    Returns:
        tuple: A tuple containing two DataFrames. The first DataFrame includes the FSIS dataset with added
        NETS Parent Company and Sales columns where matches were found. The second DataFrame contains
        FSIS entries that didn't match any NETS entry and require further processing or location-based matching.
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
    fsis_df["Short Address"] = fsis_df["Full Address"].apply(lambda x: x.split(",")[0])

    # Apply standardization to FSIS short addresses
    fsis_df["Short Address"] = fsis_df["Short Address"].apply(standardize_address)

    def find_match(i, fsis_df, nets_df):
        fsis_address = fsis_df.at[i, "Short Address"].lower()
        fsis_company = fsis_df.at[i, "Establishment Name"].upper()
        fsis_city_state = f"{fsis_df.at[i, 'City']}, {fsis_df.at[i, 'State']}"

        for k, nets in nets_df.iterrows():
            nets_address = nets["ADDRESS"].lower()
            nets_company = nets["COMPANY"].upper()
            nets_city_state = f"{nets['CITY']}, {nets['STATE']}"

            # Tier 1: High fuzzy match threshold for address
            if fuzz.token_sort_ratio(nets_address, fsis_address) > fuzz_ratio:
                return i, {
                    "Parent Corporation": nets["PARENT COMPANY"],
                    "Sales Volume (Location)": nets["SALESHERE"],
                }

            # Tier 2: High fuzzy match threshold for company name and lower threshold for city and state
            if (
                fuzz.token_sort_ratio(nets_company, fsis_company) > fuzz_ratio
                and fuzz.token_sort_ratio(nets_city_state, fsis_city_state)
                > tier2_ratio
            ):
                return i, {
                    "Parent Corporation": nets["PARENT COMPANY"],
                    "Sales Volume (Location)": nets["SALESHERE"],
                }

        return i, {}

    matched_count = 0
    for i in tqdm(fsis_df.index, desc="Matching Addresses"):
        _, result = find_match(i, fsis_df, nets_df)
        if result:
            matched_count += 1
            fsis_df.at[i, "Parent Corporation"] = result["Parent Corporation"]
            fsis_df.at[i, "Sales Volume (Location)"] = result["Sales Volume (Location)"]

    tqdm.write(f"Total plants matched: {matched_count}")
    return fsis_df, fsis_df[fsis_df["Parent Corporation"].isna()]


def loc_match(no_match: pd.DataFrame, pp_nets: pd.DataFrame, threshold: float):
    """Match NETS plants to the remaining unmatched FSIS plants
    after running address_match based on longitude/latitude
    to add parent company and sales volume data to each poultry plant from FSIS.
    Requires user input when a match is found.

    Args:
        no_match: Filtered DataFrame that contains the unmatched poultry plants
            after running address_match.
        pp_nets: NETS dataset loaded as a DataFrame.
        threshold: threshold for maximum distance possible
            to be considered a match.

    Returns:
        DataFrame with sales volume data filled in for location matches.

    """
    matched_loc_df = pd.DataFrame()
    for index, row in tqdm(
        no_match.iterrows(), total=no_match.shape[0], desc="Matching by Location"
    ):
        target_point = (row["latitude"], row["longitude"])
        for _, nets in pp_nets.iterrows():
            candidate_point = (nets["LATITUDE"], nets["LONGITUDE"])
            distance = haversine(
                target_point[1], target_point[0], candidate_point[1], candidate_point[0]
            )
            if distance <= threshold:
                if (
                    fuzz.token_sort_ratio(
                        row["Establishment Name"].upper(), nets["COMPANY"]
                    )
                    > 90
                ):
                    matched_loc_df = matched_loc_df.append(row)
                    matched_loc_df.at[index, "Sales Volume (Location)"] = nets[
                        "SALESHERE"
                    ]
                    matched_loc_df.at[index, "Parent Corporation"] = nets[
                        "PARENT COMPANY"
                    ]
                    break

    tqdm.write(f"Additional plants matched by location: {matched_loc_df.shape[0]}")
    return matched_loc_df


def save_all_matches(
    nets_path: Path,
    fsis_path: Path,
    output_fpath: Path = CLEANED_MATCHED_PLANTS_FPATH,
    threshold: float = 5,
) -> None:
    """Executes match function.


    Args:
        nets_path: relative path to the raw data folder
            with the NETS dataset.
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        output_fpath: path where the output csv will be saved
        threshold: threshold for maximum distance possible
            to be considered a match.

    Returns:
        N/A, saves updated CSV to the cleaned data folder.
    """
    address_matches, no_match = address_match(nets_path, fsis_path)
    loc_matches = loc_match(no_match, pd.read_csv(nets_path), threshold)

    final_matches = pd.concat([address_matches, loc_matches]).drop_duplicates()
    final_matches = final_matches.dropna(subset=["Parent Corporation"])
    final_matches.to_csv(output_fpath)
