import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path

here = Path(__file__).resolve().parent

abb2state = {"AL":"Alabama",
             "AK":"Alaska",
             "AZ":"Arizona",
             "AR":"Arkansas",
             "CA":"California",
             "CO":"Colorado",
             "CT":"Connecticut",
             "DE":"Delaware",
             "FL":"Florida",
             "GA":"Georgia",
             "HI":"Hawaii",
             "ID":"Idaho",
             "IL":"Illinois",
             "IN":"Indiana",
             "IA":"Iowa",
             "KS":"Kansas",
             "KY":"Kentucky",
             "LA":"Louisiana",
             "ME":"Maine",
             "MD":"Maryland",
             "MA":"Massachusetts",
             "MI":"Michigan",
             "MN":"Minnesota",
             "MS":"Mississippi",
             "MO":"Missouri",
             "MT":"Montana",
             "NE":"Nebraska",
             "NV":"Nevada",
             "NH":"New Hampshire",
             "NJ":"New Jersey",
             "NM":"New Mexico",
             "NY":"New York",
             "NC":"North Carolina",
             "ND":"North Dakota",
             "OH":"Ohio",
             "OK":"Oklahoma",
             "OR":"Oregon",
             "PA":"Pennsylvania",
             "RI":"Rhode Island",
             "SC":"South Carolina",
             "SD":"South Dakota",
             "TN":"Tennessee",
             "TX":"Texas",
             "UT":"Utah",
             "VT":"Vermont",
             "VA":"Virginia",
             "WA":"Washington",
             "WV":"West Virginia",
             "WI":"Wisconsin",
             "WY":"Wyoming"}


def counterglow_geojson_chicken(cg_path, states_geojson_path):
    """Filters the Counterglow dataset for only poultry and generates Counterglow GeoJSON
    with plant access data from all_states_with_parent_corporation_by_corp.geojson. 

    Args:
        cg_path: relative path to the clean data folder with the Counterglow dataset.
        states_geojson_path: relative path to all_states_with_parent_corporation_by_corp.geojson. 

    Returns:
        N/A, writes cleaned Counterglow GeoJSON to the clean data folder.
    
    """
    df = pd.read_csv(cg_path)
    df_poultry = df[(df["Farm Type"] == "Chickens (Meat)") | (df["Farm Type"] == "Chickens & Other Birds (Meat)")]
    df_states = gpd.read_file(states_geojson_path)

    list_of_farms = []
    for state in df_poultry.State.unique():
        for _, farm in df_poultry[df_poultry.State == state].iterrows():
            pt = Point(farm["Longitude"], farm["Latitude"])
            for _, area in df_states[df_states.state == abb2state[state]].iterrows():
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
    contained_poultry_farms.to_file(here.parent / "data/clean/counterglow_geojson.geojson", driver="GeoJSON")