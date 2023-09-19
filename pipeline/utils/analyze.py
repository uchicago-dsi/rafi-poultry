"""Contains analysis scripts to calculate HHI and parent corporation 
captured area for a given dataset, as well as join farm data 
from multiple sources together.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from pipeline.constants import RAW_COUNTERGLOW_FPATH

here = Path(__file__).resolve().parent


def HHI(fsis_sales: pd.DataFrame):
    """
    Calculcate the HHI for a selection of states/regions that are input into it

    Args:
        fsis_sales (dataframe): the data that we are calculating the index for

    Returns:
        hhi (float): the calculated index
    """

    # creates a list of the vaious parent corporations
    parent_corps = list(fsis_sales["Parent Corporation"].unique())

    sales_dict = {}
    # total sales volume of entire selection
    industry_total = sum(fsis_sales["Sales Volume (Location)"])

    for corp in parent_corps:
        # total sales for a specific corporation
        total_sales = sum(
            fsis_sales[fsis_sales["Parent Corporation"] == corp][
                "Sales Volume (Location)"
            ]
        )
        # calculate percentage -> total sales of the specific corp / industry total
        percentage = total_sales / industry_total
        # place the new value in the dictionary
        sales_dict[corp] = percentage * 100

    hhi = 0
    # loop through each value in the dict, square each of them, and then add them
    for value in sales_dict.values():
        hhi += value**2

    return hhi


def calculate_captured_area(path: Path):  # pass in geojson path
    """
    Calculates the captured areas as a percentage.
    Dict Keys: single capture, double capture, triple capture
    Values: the percentage that coordinates with the key


    Args:
        path (filepath): file path to the geojson file

    Returns:
        areas (dict): the dictionary containing the keys/values
            of percentage of area captures
    """

    areas = {
        1: 0,
        2: 0,
        3: 0,
    }

    df = gpd.read_file(path)  # read in file and convert to a dataframe
    total_area = sum(df["area"])  # sum up all areas

    for key in areas.keys():
        # sum of the area that match with the dict keys (1, 2, 3)
        # which is single, double, or triple capture
        integrator_area = sum(df[df["corporate_access"] == key]["area"])
        percent_captured = (
            integrator_area / total_area
        ) * 100  # calculate the percentage
        areas[key] = percent_captured  # add to the dictionary

    return areas


def farm_count():
    """
    Function In Progress: For now, takes in three files:
    1. infogroup-sic-code-selects.csv: infogroup data from specific SIC Codes
    2. Counterglow+Facility+List+Complete.csv: all counterglow data
    3. matched_farms: downloaded data from state gov't epa websties

    Args:
        None

    Returns:
        does not return anything. outputs a file in folder
    """

    # Infogroup Clean
    # load file
    infogroup_df = pd.read_csv(here.parent / "data/raw/infogroup-sic-code-selects.csv")
    # list of columns to drop
    drop_list = [
        "Unnamed: 0.1",
        "Unnamed: 0",
        "ZIP4",
        "LOCATION EMPLOYEE SIZE CODE",
        "LOCATION SALES VOLUME CODE",
        "PRIMARY SIC CODE",
        "SIC6_DESCRIPTIONS",
        "PRIMARY NAICS CODE",
        "NAICS8 DESCRIPTIONS",
        "SIC CODE",
        "SIC6_DESCRIPTIONS (SIC)",
        "SIC CODE 1",
        "SIC6_DESCRIPTIONS (SIC1)",
        "SIC CODE 2",
        "SIC6_DESCRIPTIONS(SIC2)",
        "SIC CODE 3",
        "SIC6_DESCRIPTIONS(SIC3)",
        "SIC CODE 4",
        "SIC6_DESCRIPTIONS(SIC4)",
        "MATCH CODE",
        "CBSA CODE",
        "CBSA LEVEL",
        "CSA CODE",
        "FIPS CODE",
        "IDCODE",
        "CENSUS BLOCK",
        "CENSUS BLOCK",
        "POPULATION CODE",
        "PARENT ACTUAL SALES VOLUME",
        "PARENT EMPLOYEE SIZE CODE",
        "SUBSIDIARY NUMBER",
        "PARENT NUMBER",
        "PARENT ACTUAL EMPLOYEE SIZE",
        "YEAR ESTABLISHED",
        "OFFICE SIZE CODE",
        "COMPANY HOLDING STATUS",
        "ABI",
        "BUSINESS STATUS CODE",
        "INDUSTRY SPECIFIC FIRST BYTE",
        "EMPLOYEE SIZE (5) - LOCATION",
        "SALES VOLUME (9) - LOCATION",
        "ARCHIVE VERSION YEAR",
        "YELLOW PAGE CODE",
        "PARENT SALES VOLUME CODE",
        "SITE NUMBER",
        "ADDRESS TYPE INDICATOR",
        "COUNTY CODE",
        "AREA CODE",
        "CENSUS TRACT",
    ]
    infogroup_df.drop(drop_list, axis=1, inplace=True)

    # Counterglow data
    # read in file
    counterglow_df = pd.read_csv(RAW_COUNTERGLOW_FPATH)
    # upper case all column names
    counterglow_df.rename(
        columns={col: col.upper() for col in counterglow_df.columns}, inplace=True
    )
    # rename some columns to match others
    counterglow_df.rename(
        columns={
            "LAT": "LATITUDE",
            "LAT.1": "LONGITUDE",
            "ADDRESS": "ADDRESS LINE 1",
            "NAME": "COMPANY",
        },
        inplace=True,
    )
    counterglow_df["ZIPCODE"] = ""  # create this missing column

    drop_list = [
        "PHONE NUMBER",
        "DESCRIPTION",
        "REGION",
        "NUMBER OF ANIMALS",
        "WEBSITE URL",
        "FARM TYPE",
        "CONTRACTED TO",
        "SUBURB/CITY",
        "COUNTY",
        "POSTCODE",
    ]
    counterglow_df.drop(drop_list, axis=1, inplace=True)
    # reorder columns
    counterglow_df = counterglow_df[
        [
            "COMPANY",
            "ADDRESS LINE 1",
            "CITY",
            "STATE",
            "ZIPCODE",
            "LATITUDE",
            "LONGITUDE",
            "BUSINESS/COMPANY NAME",
            "POSTAL ADDRESS",
            "FACILITY NAME",
            "FULL ADDRESS",
        ]
    ]

    # matched_farms cafo
    # load in data
    cafos_df = pd.read_csv(here.parent / "data/matched_farms.csv")
    # rename columns to match other dataframes
    cafos_df.rename(
        columns={col: col.upper() for col in cafos_df.columns}, inplace=True
    )
    cafos_df.rename(
        columns={
            "NAME": "COMPANY",
            "LAT": "LATITUDE",
            "LONG": "LONGITUDE",
            "ADDRESS": "ADDRESS LINE 1",
        },
        inplace=True,
    )
    cafos_df["ZIPCODE"] = ""  # create columns taht are currently missing
    cafos_df["CITY"] = ""
    # drop columns
    drop_list = [
        "UNNAMED: 0",
        "PERMIT",
        "SOURCE",
        "FUZZY NAME/EXACT LOCATION",
        "LOCATION MATCH",
    ]
    cafos_df.drop(drop_list, axis=1, inplace=True)
    # reorder columns to match other dataframes
    cafos_df = cafos_df[
        [
            "COMPANY",
            "ADDRESS LINE 1",
            "CITY",
            "STATE",
            "ZIPCODE",
            "LATITUDE",
            "LONGITUDE",
            "EXACT NAME MATCH",
            "FUZZY NAME",
            "EXACT NAME/LOCATION",
        ]
    ]

    # join all the dataframes
    concat_df = pd.concat([infogroup_df, counterglow_df, cafos_df], join="outer")

    concat_df.to_csv(here.parent / "data/raw/combined_farm_data.csv")
