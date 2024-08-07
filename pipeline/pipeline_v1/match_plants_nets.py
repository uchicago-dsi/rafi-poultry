"""Contains functions to match the sales volume data of processing plants 
from NETS data to the FSIS dataset, based on address and location. 
"""

from tqdm import tqdm
import pandas as pd
from pandas import DataFrame
import numpy as np
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path
from constants import (
    CLEANED_MATCHED_PLANTS_FPATH,
)


def address_match(
    df_nets: DataFrame,
    df_fsis: DataFrame,
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
        # TODO: Fix the docstring here
        fsis_path (DataFrame): Relative path to the clean data folder with the cleaned FSIS data.
        nets_path (DataFrame): Relative path to the clean data folder with the cleaned NETS data.
        fuzz_ratio (float): Minimum fuzziness score for the primary matching; default is 75.
        tier2_ratio (float): Fuzziness score for the secondary tier of matching; default is 60.
        num_threads (int): Number of threads for parallel processing; currently not implemented.

    Returns:
        tuple: A tuple containing two DataFrames. The first DataFrame includes the FSIS dataset with added
        NETS Parent Company and Sales columns where matches were found. The second DataFrame contains
        FSIS entries that didn't match any NETS entry and require further processing or location-based matching.
    """

    df_nets["Parent Corporation"] = np.NaN
    df_fsis["Sales Volume (Location)"] = np.NaN

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
    df_fsis["Short Address"] = df_fsis["Full Address"].apply(lambda x: x.split(",")[0])

    # Apply standardization to FSIS short addresses
    df_fsis["Short Address"] = df_fsis["Short Address"].apply(standardize_address)

    # TODO: Review this carefully to see why we are missing matches
    def find_match(i, df_fsis, df_nets):
        fsis_address = df_fsis.at[i, "Short Address"].lower()
        fsis_company = df_fsis.at[i, "Establishment Name"].upper()
        fsis_city_state = f"{df_fsis.at[i, 'City']}, {df_fsis.at[i, 'State']}"

        for k, nets in df_nets.iterrows():
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
    for i in tqdm(df_fsis.index, desc="Matching Addresses"):
        _, result = find_match(i, df_fsis, df_nets)
        if result:
            matched_count += 1
            df_fsis.at[i, "Parent Corporation"] = result["Parent Corporation"]
            df_fsis.at[i, "Sales Volume (Location)"] = result["Sales Volume (Location)"]

    tqdm.write(f"Total plants matched: {matched_count}")
    return df_fsis, df_fsis[df_fsis["Parent Corporation"].isna()]


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


def match_plants(
    df_nets: DataFrame,
    df_fsis: DataFrame,
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
    address_matches, no_match = address_match(df_nets, df_fsis)
    loc_matches = loc_match(no_match, df_nets, threshold)

    final_matches = pd.concat([address_matches, loc_matches]).drop_duplicates()
    final_matches = final_matches.dropna(subset=["Parent Corporation"])
    return final_matches


if __name__ == "__main__":
    FSIS_PATH = Path("data/raw/MPI_Directory_by_Establishment_Name_29_04_24.csv")
    df_fsis = pd.read_csv(FSIS_PATH)

    # TODO: This is to extract activities... remove later
    df_fsis = df_fsis.dropna(subset=["activities"])
    activities = set()
    for activity_string in df_fsis.activities.unique():
        activity_list = activity_string.split(";")
        for activity in activity_list:
            activities.add(activity.strip())

    df_fsis = df_fsis[df_fsis.activities.str.lower().str.contains("poultry processing")]

    df_nets = pd.read_csv(
        "data/raw/nets/NETSData2022_RAFI(WithAddresses).txt",
        sep="\t",
        encoding="latin-1",
        low_memory=False,
    )

    df_nets_naics = pd.read_csv(
        "data/raw/nets/NAICS2022_RAFI.csv",
        low_memory=False,
    )

    df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")
    df_nets["DunsNumber"] = df_nets["DunsNumber"].astype(str)

    df = pd.merge(
        df_fsis, df_nets, left_on="duns_number", right_on="DunsNumber", how="left"
    )

    # TODO: We only want companies that were open in 2022
