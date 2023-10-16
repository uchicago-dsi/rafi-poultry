"""Contains functions to match the sales volume data of processing plants 
from NETS 2022 data to the FSIS dataset, based on address and location. 
"""

import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from distances import haversine
from pathlib import Path
from constants import (CLEANED_MATCHED_PLANTS_FPATH, 
                       CLEANED_INFOGROUP_FPATH, 
                       CLEANED_FSIS_PROCESSORS_FPATH,
                       CLEANED_NETS_FPATH,
                       CLEANED_MATCHED_PLANTS_NETS_FPATH
)

def address_match(nets_path: Path,
                  fsis_path: Path, 
                  fuzz_ratio: float=50) -> pd.DataFrame:
    """Filters FSIS dataset for poultry processing plants,
    then match 2022 NETS plants to FSIS plants based on address
    to add sales volume data to each poultry plant from FSIS.

    Args:
        nets_path: relative path to the cleaned data under clean
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        fuzz_ratio: float; minimum "fuzziness" (or similarity) score 
            to accept that two strings are "the same"; default of 75

    Returns:
        DataFrame with sales volume data filled in for address matches.

    """
    nets = pd.read_csv(nets_path)
    
    nets["Full Address"] = (
        nets["ADDRESS"]
        + ", "
        + nets["CITY"]
        + ", "
        + nets["STATE"]
        + " "
        + nets["ZIPCODE"].astype(int).astype(str)
    )
    nets["Full Address"] = nets["Full Address"].astype(str)

    #df_fsis = pd.read_csv(fsis_path, index_col=0)
    
    df_fsis = pd.read_csv(fsis_path)#new
    
    #df_poultry = df_fsis[df_fsis["Animals Processed"].str.contains("Chicken")].copy()
    df_poultry = df_fsis[df_fsis["Activities"].str.contains("Poultry")].copy()# new
    df_poultry["Sales Volume (Location)"] = np.NaN
    df_poultry["Sales Volume (Location)"] = np.NaN
    

    for i, fsis in df_poultry.iterrows():
        fsis_address = fsis["Full Address"].lower()
        for k, net in nets.iterrows():
            infogroup_address = net["Full Address"].lower()
            #print(f"fsis_address: {fsis_address}, infogroup_address: {infogroup_address}")
            if fuzz.token_sort_ratio(infogroup_address, fsis_address) > fuzz_ratio:
                df_poultry.loc[i, "Sales Volume (Location)"] = net[
                    "SALESHERE"
                ]
                break
            
    return df_poultry

#no_match, pp_2022, address_matches, threshold
#for info group
def loc_match(no_match: pd.DataFrame, 
              pp_2022: pd.DataFrame, 
              pp_sales: pd.DataFrame, 
              threshold: float) -> (pd.DataFrame, pd.DataFrame):
    """Match 2022 NETS plants to the remaining unmatched FSIS plants 
    after running address_match based on longitude/latitude 
    to add sales volume data to each poultry plant from FSIS. 
    Requires user input when a match is found.

    Args:
        no_match: Filtered DataFrame that contains the unmatched poultry plants 
            after running address_match.
        pp_2022: 2022 NETS dataset loaded as a DataFrame.
        pp_sales: DataFrame returned by address_match, which contains 
            FSIS poultry plants matched with sales volume.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        2022 NETS DataFrame (pp_2022) and DataFrame with sales volume data 
        filled in for location matches (pp_sales).

    """
    no_match_nulls = no_match[no_match["Sales Volume (Location)"].isna()]
    for index, row in no_match_nulls.iterrows():
        target_point = (row["Latitude"], row["Longitude"])
        for _, net in pp_2022.iterrows():
            candidate_point = (net["LATITUDE"], net["LONGITUDE"])
            distance = haversine(
                target_point[1], 
                target_point[0], 
                candidate_point[1], 
                candidate_point[0]
            )
            if distance <= threshold:
                if (
                    fuzz.token_sort_ratio(
                        row["Company"].upper(), net["COMPANY"]
                    )
                    > 90
                ):
                    pp_sales.loc[index, "Sales Volume (Location)"] = net[
                        "SALESHERE"
                    ]
                    break
    return pp_2022, pp_sales

# idk if we can use it
def fill_remaining_nulls(pp_sales: pd.DataFrame) -> pd.DataFrame:
    """Fills in sales volume for all remaining unmatched plants after running 
    loc_match function with the median of the sales volume 
    of all matched plants so far for each plant, based on 
    its respective parent corporation.

    Args:
        pp_sales: DataFrame returned by loc_match, 
            which contains FSIS poultry plants matched with sales volume.

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


def save_all_matches(nets_path: Path, 
                     fsis_path: Path, 
                     threshold: float=5) -> None:
    """Executes all three matching helper functions and saves final fully 
    updated sales volume DataFrame as a CSV.

    Args:
        nets_path: relative path to the cleaned data
        fsis_path: relative path to the raw data folder with the FSIS dataset.
        threshold: threshold for maximum distance possible 
            to be considered a match.

    Returns:
        N/A, saves updated CSV to the cleaned data folder.
    """
    address_matches = address_match(nets_path, fsis_path, 60)
    no_match = address_matches[address_matches["Sales Volume (Location)"].isna()]
    nets = pd.read_csv(nets_path)
    pp_2022 = nets

    pp_2022, pp_sales = loc_match(no_match, pp_2022, address_matches, threshold)
    #need parent corperation info in FSIS
    #pp_sales_updated = fill_remaining_nulls(pp_sales) 
    #skip the na filling
   # pp_sales_updated.to_csv(CLEANED_MATCHED_PLANTS_FPATH)
    pp_sales.to_csv(CLEANED_MATCHED_PLANTS_NETS_FPATH)
    