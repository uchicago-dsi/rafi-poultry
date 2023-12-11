"""Contains all cleaning functions for the FSIS, Counterglow, Infogroup, 
and state CAFO permit datasets.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from geopy.geocoders import MapBox
import os
from constants import (
    CLEANED_COUNTERGLOW_FPATH,
    CLEANED_CAFO_POULTRY_FPATH,
    SMOKE_TEST_FPATH,
)


def clean_FSIS(filepath1: Path, filepath2: Path, save_path: Path) -> None:
    """Filters the FSIS dataset for large poultry processing plants.

    Args:
        filepath1: relative path to the raw FSIS MPI dataset.
        filepath2: relative path to the raw FSIS dataset.
        save_path: the path to save filtered FSIS dataset.

    Returns:
        N/A, writes cleaned dataset into the clean data folder.

    """
    if not os.getenv("INSIDE_DOCKER"):
        from dotenv import load_dotenv

        load_dotenv()

    df_with_address = pd.read_excel(filepath1)
    df_with_size = pd.read_excel(filepath2, skiprows=3)

    # only keep the columns we need
    df_with_size = df_with_size[["EstNumber", "Size", "Chicken\nSlaughter"]]

    # merge two dataframes
    df_FSIS = pd.merge(df_with_address, df_with_size, on="EstNumber")

    df_FSIS["Full Address"] = (
        df_FSIS["Street"]
        + ","
        + df_FSIS["City"]
        + ","
        + df_FSIS["State"]
        + " "
        + df_FSIS["Zip"].astype(str)
    )

    # drop unnecessary columns
    df_FSIS = df_FSIS.drop(columns=["Street", "Zip"])

    # preprocessing: only keep large chicken slaughter
    # chicken_slaughter = Yes; Activities include Poultry
    df_chicken = df_FSIS[
        df_FSIS["Activities"].str.contains("Poultry")
        | (df_FSIS["Chicken\nSlaughter"] == "Yes")
    ]
    # keep the large size
    df_large_chickens = df_chicken.loc[df_chicken.Size == "Large"]
    # Iterate through the DataFrame and geocode each address

    # geocoding
    access_token = os.getenv("MAPBOX_API")

    # Initialize the MapBox geocoder with your access token
    geolocator = MapBox(api_key=access_token)
    df_large_chickens["latitude"] = None
    df_large_chickens["longitude"] = None

    for index, row in df_large_chickens.iterrows():
        location = geolocator.geocode(row["Full Address"])
        if location:
            df_large_chickens.at[index, "latitude"] = location.latitude
            df_large_chickens.at[index, "longitude"] = location.longitude

    # Renaming of certain columns to fix compatability
    df_large_chickens = df_large_chickens.rename(
        columns={"Company": "Establishment Name"}
    )
    # Save df_FSIS to raw folder
    df_large_chickens.to_csv(save_path)


def filter_infogroup(
    filename: str, search_str: str, chunksize: int = 10000
) -> pd.DataFrame:
    """Filters the Infogroup file for a specific string (ie. "chicken"),
    meant as a helper function for clean_infogroup.

    Args:
        filename: path to specific file to be filtered
        search_str: SIC code (as a string) to search columns for
        chunksize: integer representing how many rows the function processes
        at a time.

    Returns:
        N/A, puts cleaned df into the data/clean folder

    """
    search_cols = [
        "PRIMARY SIC CODE",
        "SIC CODE 1",
        "SIC CODE 2",
        "SIC CODE 3",
        "SIC CODE 4",
    ]

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

    return filtered_df


def clean_infogroup(
    filepath: Path,
    ABI_dict: dict,
    SIC_CODE: str,
    save_path: Path,
    filtering: bool = False,
) -> None:
    """Cleans the infogroup files, combines them into one large master df.

    Args:
        filepath: absolute path to folder that contains all infogroup files
        ABI_dict: dictionary of all parent ABI's and their name as a str
        SIC_CODE: SIC code to filter the dataframes on
        filtering: boolean, true if infogroup files are in their rawest form
            and need to be filtered

    Returns:
        N/A, puts cleaned df into the data/clean folder

    """
    all_years_df = pd.DataFrame()
    dfs = []

    for name in filepath.iterdir():
        if name == Path(SMOKE_TEST_FPATH):
            pass
        else:
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

    cols = ["YEAR ESTABLISHED", "PARENT NUMBER"]

    for x in cols:
        all_years_df[x] = all_years_df[x].fillna(0)
        all_years_df[x] = all_years_df[x].apply(np.int64)

    all_years_df["PARENT NAME"] = (
        all_years_df["PARENT NUMBER"].replace({np.nan: None}).astype(str).map(ABI_dict)
    )
    all_years_df["PARENT NAME"] = all_years_df["PARENT NAME"].fillna("Small Biz")

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
        ]
    ]

    master = master.dropna(subset=["COMPANY", "LATITUDE", "LONGITUDE"])

    master.to_csv(save_path)


def filter_NETS(
    NETS_fpath: str, NAICS_fpath: str, NAICS_lookup_fpath: str, search_str: str
) -> pd.DataFrame:
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

    df = pd.read_csv(NETS_fpath, sep="\t", encoding="latin-1", low_memory=False)
    df = df.dropna(subset=["SIC22"])
    # read raw NAICS
    naics = pd.read_csv(NAICS_fpath)
    naics_lookup = pd.read_csv(NAICS_lookup_fpath)
    # Filtering naics
    naics = naics[["DunsNumber", "NAICS22"]]
    # Filtering naics lookup
    naics_lookup = naics_lookup[["NAICS22 Code", "NAICS22 Text"]]

    # Merging naics and nets
    df = df.merge(naics, how="left", on="DunsNumber")
    df = df.merge(naics_lookup, how="left", left_on="NAICS22", right_on="NAICS22 Code")
    df = df.drop(columns=["NAICS22 Code"])

    search_cols = ["SIC22", "NAICS22"]

    df.columns = map(str.upper, df.columns)
    rows_to_keep = df[
        df[search_cols].apply(
            lambda r: r.astype(str).str.contains(search_str, case=False).any(),
            axis=1,
        )
    ]
    return rows_to_keep


def clean_NETS(
    NETS_fpath: str,
    NAICS_fpath: str,
    save_path: str,
    cols_to_keep: list,
    NAICS_lookup_fpath: str,
    SIC_code: str,
    filtering: bool = False,
) -> None:
    """Cleans the NETS files, combines them into one large master df.

    Args:
        # TODO: what is the NAICS lookup path?
        filepath: absolute path to folder that contains all infogroup files
        SIC_code: SIC code to filter the dataframes on
        save_path: path to save cleaned df to
        cols_to_keep: list of columns to keep in the final df
        filtering: boolean, true if infogroup files are in their rawest form
            and need to be filtered

    Returns:
        N/A, puts cleaned df into the data/clean folder

    """
    # TODO: I don't like this. load the thing then do something with it
    if filtering:
        df = filter_NETS(NETS_fpath, NAICS_fpath, NAICS_lookup_fpath, SIC_code)
    else:
        df = pd.read_csv(NETS_fpath, sep="\t", encoding="latin-1", low_memory=False)

    df = df.reset_index(drop=True)

    master = df[cols_to_keep]

    # TODO: this should probably be somewhere else/abstracted
    master.rename(
        columns={
            "FIRSTYEAR": "YEAR ESTABLISHED",
            "HQCOMPANY": "PARENT COMPANY",
            "HQDUNS": "PARENT DUNS",
        },
        inplace=True,
    )
    master.to_csv(save_path)


def clean_counterglow(filepath: Path) -> None:
    """Cleans the Counterglow dataset by standardizing facility name
    and column formatting.

    Args:
        filepath: relative path to the raw data folder
            with the Counterglow dataset.

    Returns:
        N/A, writes cleaned Counterglow dataset to the clean data folder.

    """
    df = pd.read_csv(filepath)
    df["Name"] = df["Name"].astype(str, copy=False).apply(lambda x: x.upper())
    df = df.rename(columns={"Lat": "Latitude", "Lat.1": "Longitude"})

    df.to_csv(CLEANED_COUNTERGLOW_FPATH)


def clean_cafo(data_dir: Path, config_fpath: Path) -> None:
    """Merges state level CAFO permit data (taken from gov't websites)
    into one CSV with columns for name, address, longitude/latitude, and state.
    Column names in each dataset are mapped to standardized format
    in accompanying farm_source.json file. Rows in complete dataset are
    left blank if no information is available, and raw CSVs may need to be
    standardized/filtered by hand first.

    Args:
        data_dir: filepath to raw data subfolder "cafo"
            that contains the state permit data.
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
