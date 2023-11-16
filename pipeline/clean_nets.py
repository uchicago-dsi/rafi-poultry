import pandas as pd
import numpy as np
import json
from pathlib import Path
from constants import (
    RAW_NETS,
    RAW_NAICS,
    RAW_NAICS_LOOKUP,
    CLEANED_NETS_FPATH,
    COLUMNS_TO_KEEP,
)
# # change columns to keep to upper case
# COLUMNS_TO_KEEP = ['DUNSNUMBER', 'COMPANY', 'ADDRESS', 'CITY', 'STATE','FIRSTYEAR',
#                       'ZIPCODE', 'HQCOMPANY', 'HQDUNS', 'SIC22', 'INDUSTRY', 'SALESHERE',
#                       'SALESHEREC', 'SALESGROWTH', 'NAICS22', 'NAICS22 TEXT', 'LATITUDE', 'LONGITUDE']
def filter_NETS(NETS_fpath: str, 
                NAICS_fpath: str,
                NAICS_lookup_fpath: str,
                search_str: str) -> pd.DataFrame:
    """Filters the NETS file for a specific industry (ie. "chicken"), 
    meant as a helper function for NETS.

    Args:
        filename: path to NETS file to be filtered
        search_str: SIC code (as a string) to search columns for
        chunksize: integer representing how many rows the function processes
        at a time. 

    Returns:
        N/A, puts cleaned df into the data/clean folder

    """
    # read raw NETS

    df = pd.read_csv(NETS_fpath, sep="\t", encoding='latin-1', low_memory=False)
    df = df.dropna(subset=['SIC22'])
    # read raw NAICS
    naics = pd.read_csv(NAICS_fpath)
    naics_lookup = pd.read_csv(NAICS_lookup_fpath)
    # Filtering naics
    naics = naics[['DunsNumber', 'NAICS22']]
    # Filtering naics lookup
    naics_lookup = naics_lookup[['NAICS22 Code', 'NAICS22 Text']]

    # Merging naics and nets
    df = df.merge(naics, how='left', on='DunsNumber')
    df = df.merge(naics_lookup, how='left',
                            left_on='NAICS22',
                            right_on='NAICS22 Code')
    df = df.drop(columns=['NAICS22 Code'])

    search_cols = [
        "SIC22",
        "NAICS22"
    ]

    df.columns = map(str.upper, df.columns)
    rows_to_keep = df[
    df[search_cols].apply(
                lambda r: r.astype(str).str.contains(search_str, 
                                                     case=False).any(),
                axis=1,
            )
        ]
    return rows_to_keep

def clean_NETS(NETS_fpath: str, 
                NAICS_fpath: str,
                NAICS_lookup_fpath: str,
                SIC_CODE: str, 
                save_path: str,
                colums_to_keep: list,
                filtering: bool = False) -> None:
    """Cleans the infogroup files, combines them into one large master df.

    Args:
        filepath: absolute path to folder that contains all infogroup files
        SIC_CODE: SIC code to filter the dataframes on
        save_path: path to save cleaned df to
        colums_to_keep: list of columns to keep in the final df
        filtering: boolean, true if infogroup files are in their rawest form 
            and need to be filtered

    Returns:
        N/A, puts cleaned df into the data/clean folder

    """
    if filtering:
        df = filter_NETS(NETS_fpath, NAICS_fpath, NAICS_lookup_fpath, SIC_CODE)
    else:
        df = pd.read_csv(NETS_fpath, sep="\t", encoding='latin-1', low_memory=False)

    df = df.reset_index(drop=True)
    
    master = df[colums_to_keep]

    master.rename(columns={"FIRSTYEAR": "YEAR ESTABLISHED",
                        "HQCOMPANY": "PARENT COMPANY",
                        "HQDUNS": "PARENT DUNS"}, inplace=True)
    master.to_csv(save_path)

# clean_NETS(RAW_NETS_FPATH,
#                 '2015', 
#                 CLEANED_NETS_FPATH,
#                 COLUMNS_TO_KEEP,
#                 True)