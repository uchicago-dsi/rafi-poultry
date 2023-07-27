"""Contains all cleaning functions for the FSIS, Counterglow, Infogroup, and state CAFO permit datasets.
"""

import pandas as pd
import numpy as np
import glob
import json
from pathlib import Path

here = Path(__file__).resolve().parent

ABI_dict = dict({np.nan: 'None', 7537913.0: 'Tyson Foods Inc', 0.0: 'None', 987289857.0: 'JBS USA',
                7516065.0: 'Hormel Foods Corp',  453614844.0: 'Cargil Inc', 9564816.0: 'Foster Farms',
                441416815.0: 'Sanderson Farms Inc', 517549762.0: 'Koch Foods Inc', 835874538.0: 'Mountaire Corp', 
                7529217.0: 'Perdue Farms Inc', 433353331.0: 'Continental Grain Co', 513523.0: 'House of Raeford Farms Inc', 
                436136139.0: "Pilgrim's Pride Corp", 512392.0: "George's Inc", 431481290.0: 'Cal-main Foods Inc', 
                7509045.0: "Conagra Brands Inc", 7534076.0: "Simmons Foods Inc", 531052413.0: "Peco Foods Inc",  
                1941509.0: "UNKNOWN"})


def clean_FSIS(filepath):
    """Filters the FSIS dataset for large poultry processing plants. 

    Args:
        filepath: relative path to the raw data folder with the FSIS dataset.

    Returns:
        N/A, writes cleaned dataset into the clean data folder.

    """
    df = pd.read_csv(filepath)
    df_chickens = df[df['Animals Processed'].str.contains('Chicken')]
    df_large_chickens = df_chickens.loc[df_chickens.Size == "Large"]

    df_large_chickens.to_csv(here.parent / "data/clean/cleaned_fsis_processors.csv")

    return



def clean_infogroup(filepath):
    """Cleans the infogroup files, combines them into one large master df.

    Args:
        filepath: absolute path to folder that contains all infogroup files 

    Returns:
        n/a, puts cleaned df into the data/clean folder

    """

    path = Path(filepath)
    all_years_df = pd.DataFrame()
    dfs = []

    for name in path.iterdir():
        df = pd.read_csv(name)
        df.columns = map(str.upper, df.columns)
        dfs.append(df)

    all_years_df = pd.concat(dfs, ignore_index=True)
    all_years_df = all_years_df.sort_values(by='ARCHIVE VERSION YEAR').reset_index(drop=True)

    cols = ['YEAR ESTABLISHED', 'YEAR 1ST APPEARED', 'PARENT NUMBER']
    
    for x in cols:
        all_years_df[x] = all_years_df[x].fillna(0)
        all_years_df[x] = all_years_df[x].apply(np.int64)

    all_years_df['PARENT NAME'] = all_years_df['PARENT NUMBER'].map(ABI_dict)
    all_years_df['PARENT NAME'] = all_years_df['PARENT NAME'].fillna('Small Biz')

    master = all_years_df[['COMPANY', 'ADDRESS LINE 1', 'CITY', 'STATE', 'ZIPCODE', 'PRIMARY SIC CODE', 
                    'ARCHIVE VERSION YEAR', 'YEAR ESTABLISHED', 'ABI', 'SALES VOLUME (9) - LOCATION', 'COMPANY HOLDING STATUS', 
                    'PARENT NUMBER', 'PARENT NAME', 'LATITUDE', 'LONGITUDE', 'YEAR 1ST APPEARED']]


    master = master.dropna(subset = ['COMPANY', 'LATITUDE', 'LONGITUDE'])

    master.to_csv(here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv")

    return



def clean_counterglow(filepath):
    """Cleans the Counterglow dataset by standardizing CAFO name and column formatting.

    Args:
        filepath: relative path to the raw data folder with the Counterglow dataset.

    Returns:
        N/A, writes cleaned Counterglow dataset to the clean data folder.

    """
    df = pd.read_csv(filepath)
    df["Name"] = df["Name"].astype(str, copy=False).apply(lambda x : x.upper())
    df = df.rename(columns={"Lat": "Latitude", "Lat.1": "Longitude"})

    df.to_csv(here.parent / "data/clean/cleaned_counterglow_facility_list.csv")

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
    data_dir = Path(data_dir)
    config_fpath = Path(config_fpath)
    # Open configuration file
    with open(config_fpath) as f:
        config = json.load(f)

    # Iterate through each configured data source
    final_df = None
    for source in config:

        # Create file path to data source
        fpath = data_dir.joinpath(source['file_name'])

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
        final_df = df if final_df is None else pd.concat([df, final_df], ignore_index=True)

    final_df.to_csv(here.parent / "data/clean/cleaned_matched_farms.csv")


if __name__ == "__main__":
    clean_infogroup(here.parent / "data/raw/infogroup")
    clean_FSIS(here.parent / "data/raw/fsis-processors-with-location.csv")