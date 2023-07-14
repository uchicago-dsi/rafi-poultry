import pandas as pd
import numpy as np
import glob



def clean_FSIS(filepath):
    """Example function with PEP 484 type annotations.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    """
    df = pd.read_csv(filepath)
    df_chickens = df[df['Animals Processed'].str.contains('Chicken')]
    df_large_chickens = df_chickens.loc[df_chickens.Size == "Large"]

    df_large_chickens.to_csv("../data/clean/cleaned_fsis_processors.csv")



def clean_infogroup(filepath):
    """Cleans the infogroup files, combines them into one large master df.

    Args:
        filepath: path to folder that contains all infogroup files 

    Returns:
        n/a, puts cleaned df into the data/clean folder

    """

    print("HELLO")
    all_years_df = pd.DataFrame()

    files = glob.glob(filepath, recursive=True)
    print("HEY")

    for name in files:
        print("HI")
        df = pd.read_csv(name)
        df.columns = map(str.upper, df.columns)
        alL_years_df = pd.concat([all_years_df, df], ignore_index=True)

    cols = ['YEAR ESTABLISHED', 'YEAR 1ST APPEARED', 'COMPANY HOLDING STATUS', 'PARENT NUMBER']
    
    for name in cols:
        all_years_df[name] = all_years_df[name].fillna(0)
        all_years_df[name] = all_years_df[name].apply(np.int64)

    all_years_df.to_csv("../data/clean/cleaned_infogroup_plants_all_time.csv")



def clean_counterglow(filepath):
    """Example function with PEP 484 type annotations.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    """

    df = pd.read_csv(filepath)
    df["Name"] = df["Name"].astype(str, copy=False).apply(lambda x : x.upper())

    df.to_csv("../data/clean/cleaned_counterglow_facility_list.csv")



def clean_cafo(filepath):
    """Example function with PEP 484 type annotations.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    """
