import pandas as pd
import numpy as np
import geopandas as gpd

"""Contains functions for analyzing market consolidation: 
- HHI: calculates HHI for all parent corporations in given dataframe
- calculateCapturedArea: calculates the captured areas as a percentage.
"""

def HHI(fsis_sales):
    """
    Calculcate the HHI for a selection of states/regions that are input into it 

    Args:
        fsis_sales (dataframe): the data that we are interesting in to calculate the index for

    Returns:
        hhi (float): the calculated index
    """

    # creates a list of the vaious parent corporations
    parent_corps = list(fsis_sales["Parent Corporation"].unique())

    sales_dict = {}
    industry_total = sum(fsis_sales["Sales Volume (Location)"]) # total sales volume of entire selection

    for corp in parent_corps:
        # total sales for a specific corporation
        total_sales = sum(fsis_sales[fsis_sales["Parent Corporation"]==corp]["Sales Volume (Location)"])
        # calculate percentage -> total sales of the specific corp / industry total
        percentage = total_sales/industry_total
        # place the new value in the dictionary
        sales_dict[corp] = percentage*100

    hhi = 0
    # loop through each value in the dict, square each of them, and then add them
    for value in sales_dict.values():
        hhi += value**2
    
    return hhi


def calculateCapturedArea(path): # pass in geojson path
    """
    Calculates the captured areas as a percentage.
    Dict Keys: single capture, double capture, triple capture
         Values: the percentage that coordinates with the key   


    Args:
        path (filepath): file path to the geojson file

    Returns:
        areas (dict): the dictionary containing the keys/values of percentage of area captures
    """

    areas = {
        1: 0,
        2: 0,
        3: 0,
    }

    df = gpd.read_file(path) # read in file and convert to a dataframe
    total_area = sum(df["area"]) # sum up all areas

    for key in areas.keys():
        # sum of the area that match with the dict keys (1, 2, 3) which is single, double, or triple capture
        integrator_area = sum(df[df["corporate_access"]==key]["area"])
        percent_captured = (integrator_area/total_area)*100 # calculate the percentage
        areas[key] = percent_captured # add to the dictionary
    
    return areas


## In Process: farm_count. this will take in the farm data then figure out what percentage only have 
# access to one integrator, two integrators, etc. based upon the selected area
def farm_count():
    pass