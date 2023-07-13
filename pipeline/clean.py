import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import folium
import geopandas as gpd
import shapely
from shapely.geometry import Polygon
import glob



def clean_FSIS():
    df = pd.read_csv("../data/raw/fsis-processors-with-location.csv")
    df_chickens = df[df['Animals Processed'].str.contains('Chicken')]
    df_large_chickens = df_chickens.loc[df_chickens.Size == "Large"]

    df_large_chickens.to_csv("../data/clean/cleaned_fsis_processors.csv")



def clean_infogroup():

    all_years_df = pd.DataFrame()

    directory = "../data/raw/infogroups"

    for filename in glob.glob(directory + "/*.csv"):
        df = pd.read_csv(filename)
        df.columns = map(str.upper, df.columns)
        alL_years_df = pd.concat([all_years_df, df], ignore_index=True)

    all_years_df.to_csv("../data/clean/cleaned_infogroup_plants_all_time.csv")



def clean_counterglow():

    df = pd.read_csv("../data/raw/Counterglow+Facility+List+Complete.csv")
    df["Name"] = df["Name"].astype(str, copy=False).apply(lambda x : x.upper())

    df.to_csv("../data/clean/cleaned_counterglow_facility_list.csv")



def clean_cafo(filepath)
