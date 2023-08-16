"""Contains all cleaning functions for the FSIS, Counterglow, Infogroup, and state CAFO permit datasets.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from constants import (
    CLEANED_FSIS_PROCESSORS_FPATH,
    CLEANED_INFOGROUP_FPATH,
    RAW_INFOGROUP_FPATH,
    CLEANED_COUNTERGLOW_FPATH,
    CLEANED_CAFO_POULTRY_FPATH,
)

def clean_FSIS(filepath: Path):
    """Filters the FSIS dataset for large poultry processing plants.

    Args:
        filepath: relative path to the raw data folder with the FSIS dataset.

    Returns:
        N/A, writes cleaned dataset into the clean data folder.

    """
    df = pd.read_csv(filepath)
    df_chickens = df[df["Animals Processed"].str.contains("Chicken")]
    df_large_chickens = df_chickens.loc[df_chickens.Size == "Large"]

    df_large_chickens.to_csv(CLEANED_FSIS_PROCESSORS_FPATH)

    return


def filter_infogroup(filename: str, search_str: str, chunksize: int = 10000):
    search_cols = [
        "PRIMARY SIC CODE",
        "SIC CODE 1",
        "SIC CODE 2",
        "SIC CODE 3",
        "SIC CODE 4",
    ]

    # TODO: the smoke test idea is probably useful in general - this should maybe be set as a command line argument and passed through the various functions
    smoke_test = False

    filtered_df = pd.DataFrame([])
    for df in pd.read_csv(filename, iterator=True, chunksize=chunksize):
        df.columns = map(str.upper, df.columns)
        rows_to_add = df[
            df[search_cols].apply(
                lambda r: r.astype(str).str.contains(search_str, case=False).any(),
                axis=1,
            )
        ]
        filtered_df = pd.concat([filtered_df, rows_to_add], axis=0)
        if smoke_test:
            break

    return filtered_df


def clean_infogroup(filepath: Path, ABI_dict: dict, SIC_CODE: str, filtering: bool = False):
    """Cleans the infogroup files, combines them into one large master df.

    Args:
        filepath: absolute path to folder that contains all infogroup files
        SIC_CODE: SIC code to filter the dataframes on
        filtering: boolean, true if infogroup files are in their rawest form and need to be filtered

    Returns:
        n/a, puts cleaned df into the data/clean folder

    """
    all_years_df = pd.DataFrame()
    dfs = []

    for name in filepath.iterdir():
        if filtering:
            df = filter_infogroup(name, SIC_CODE, chunksize=1000000)
            dfs.append(df)
        else:
            df = pd.read_csv(name, encoding="utf-8")
            dfs.append(df)

    all_years_df = pd.concat(dfs, ignore_index=True)
    all_years_df = all_years_df.sort_values(by="ARCHIVE VERSION YEAR").reset_index(
        drop=True
    )

    cols = ["YEAR ESTABLISHED", "YEAR 1ST APPEARED", "PARENT NUMBER"]

    for x in cols:
        all_years_df[x] = all_years_df[x].fillna(0)
        all_years_df[x] = all_years_df[x].apply(np.int64)

    all_years_df["PARENT NAME"] = (
        all_years_df["PARENT NUMBER"].replace({np.nan: None}).astype(str).map(ABI_dict)
    )
    all_years_df["PARENT NAME"] = all_years_df["PARENT NAME"].fillna("Small Biz")
    all_years_df["ABI"] = all_years_df["PARENT NUMBER"].apply(str)

    master = all_years_df[
        [
            "COMPANY",
            "ADDRESS LINE 1",
            "CITY",
            "STATE",
            "ZIPCODE",
            "PRIMARY SIC CODE",
            "ARCHIVE VERSION YEAR",
            "YEAR ESTABLISHED",
            "ABI",
            "SALES VOLUME (9) - LOCATION",
            "COMPANY HOLDING STATUS",
            "PARENT NUMBER",
            "PARENT NAME",
            "LATITUDE",
            "LONGITUDE",
            "YEAR 1ST APPEARED",
        ]
    ]

    master = master.dropna(subset=["COMPANY", "LATITUDE", "LONGITUDE"])

    master.to_csv(CLEANED_INFOGROUP_FPATH)

    return


def clean_counterglow(filepath: Path):
    """Cleans the Counterglow dataset by standardizing facility name and column formatting.

    Args:
        filepath: relative path to the raw data folder with the Counterglow dataset.

    Returns:
        N/A, writes cleaned Counterglow dataset to the clean data folder.

    """
    df = pd.read_csv(filepath)
    df["Name"] = df["Name"].astype(str, copy=False).apply(lambda x: x.upper())
    df = df.rename(columns={"Lat": "Latitude", "Lat.1": "Longitude"})

    df.to_csv(CLEANED_COUNTERGLOW_FPATH)

    return


def clean_cafo(data_dir: Path, config_fpath: Path):
    """Merges state level CAFO permit data (taken from gov't websites) into one CSV
    with columns for name, address, longitude/latitude, and state. Column names
    in each dataset are mapped to standardized format in accompanying farm_source.json file.
    Rows in complete dataset are left blank if no information is available,
    and raw CSVs may need to be standardized/filtered by hand first.

    Args:
        data_dir: filepath to raw data subfolder "cafo" that contains the state permit data.
        config_fpath: filepath to farm_source.json file.

    Returns:
        N/A, writes cleaned CAFO dataset to the clean data folder.

    """
    # Open configuration file
    with open(config_fpath) as f:
        config = json.load(f)

    # Iterate through each configured data source
    final_df = None
    for source in config:
        # Create file path to data source
        fpath = data_dir.joinpath(source["file_name"])

        # Load data source as DataFrame
        df = pd.read_csv(fpath)

        # Subset to relevant columns
        present_cols = list(filter(None, list(source["column_mapping"].values())))
        df = df[present_cols]

        # Rename columns to match standard model
        inv_dict = {v: k for k, v in source["column_mapping"].items()}
        df = df.rename(columns=inv_dict)

        # Add remaining columns
        df["state"] = source["state"]
        df["source"] = source["name"]

        # Update final DataFrame
        final_df = (
            df if final_df is None else pd.concat([df, final_df], ignore_index=True)
        )

    final_df.to_csv(CLEANED_CAFO_POULTRY_FPATH)