"""Contains functions for creating geojsons for mapping based on farm data.
"""

import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path
from constants import abb2state, COUNTERGLOW_GEOJSON_FPATH

def create_counterglow_geojson(cg_path: str, 
                                states_geojson_path: str) -> None:
    """Filters the Counterglow dataset for only poultry 
    and generates Counterglow GeoJSON based on plant access data 
    from all_states_with_parent_corporation_by_corp.geojson, 
    the file output by calculate_captured_areas.py
    
    Args:
        cg_path: relative path to the clean data folder with the 
            Counterglow dataset.
        states_geojson_path: relative path to 
            all_states_with_parent_corporation_by_corp.geojson. 

    Returns:
        N/A, writes cleaned Counterglow GeoJSON to the clean data folder.
    
    """
    df = pd.read_csv(cg_path)
    df_poultry = df[(df["Farm Type"] == "Chickens (Meat)") | 
                    (df["Farm Type"] == "Chickens & Other Birds (Meat)")]
    df_states = gpd.read_file(states_geojson_path)

    list_of_farms = []
    for state in df_poultry.State.unique():
        for _, farm in df_poultry[df_poultry.State == state].iterrows():
            pt = Point(farm["Longitude"], farm["Latitude"])
            for _, area in df_states[df_states.state == abb2state[state]
                                     ].iterrows():
                if area.geometry.contains(pt):
                    farm_data = {
                        "state": abb2state[state],
                        "geometry": pt,
                        "address": farm.Address,
                        "company": farm["Business/company name"],
                        "plant_access": area.corporate_access
                    }
                    list_of_farms.append(farm_data)
    
    contained_poultry_farms = gpd.GeoDataFrame(list_of_farms)
    contained_poultry_farms.to_file(COUNTERGLOW_GEOJSON_FPATH, driver="GeoJSON")