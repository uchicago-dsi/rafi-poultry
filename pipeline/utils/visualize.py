"""Contains functions for creating a map of CAFOs in a state, color coded by their source, 
based on data from Counterglow and state permits websites.
"""

import pandas as pd
import numpy as np
import folium
from pathlib import Path


def colored_maps(infogroup_path: Path, year: int):
    USA_LAT = 37.0902
    USA_LNG = -95.7129

    # assigning each parent corp a unique color
    dict_place = dict(
        {
            "Tyson Foods Inc": "green",
            "JBS USA": "red",
            "Sanderson Farms Inc": "pink",
            "Hormel Foods Corp": "cadetblue",
            "Koch Foods Inc": "beige",
        }
    )

    # coloring all other parent corporations gray
    placeholder = [
        "None",
        "Pilgrim's Pride Corp",
        "Cargil Inc",
        "Mountaire Corp",
        "Foster Farms",
        "Perdue Farms Inc",
        "Continental Grain Co",
        "George's Inc",
        "House of Raeford Farms Inc",
        "Cal-main Foods Inc",
        "Conagra Brands Inc",
        "UNKNOWN",
        "Simmons Foods Inc",
        "Peco Foods Inc",
    ]
    dict_place2 = dict.fromkeys(placeholder, "lightgray")

    col_dict = {**dict_place, **dict_place2}

    master = pd.read_csv(infogroup_path, index=False).reset_index(drop=True)
    df = master.loc[master["ARCHIVE VERSION YEAR"] == year]
    map_name = folium.Map(location=[USA_LAT, USA_LNG], zoom_start=4)
    df["COLOR"] = df["PARENT NAME"].map(col_dict)

    for _, location_info in df.iterrows():
        folium.Marker(
            [location_info["LATITUDE"], location_info["LONGITUDE"]],
            popup=location_info["PARENT NAME"],
            icon=folium.Icon(color=location_info["COLOR"]),
        ).add_to(map_name)

    return map_name


def add_points(state_map: folium.Map, state_df: pd.DataFrame, color: str):
    """Adds markers to a given state map based on location to represent farms.

    Args:
        state_map: map to add markers to
        state_df: DataFrame containing the farms and locations 
            to be added to the map
        color: color for the markers as a string

    Returns:
        N/A, adds points to existing map

    """
    for _, location_info in state_df.iterrows():
        folium.Marker(
            [location_info["lat"], location_info["long"]],
            popup=location_info["name"],
            icon=folium.Icon(color=color),
        ).add_to(state_map)


def map_state(match_df_path: Path, unmatched_df_path: Path, state: str):
    """Creates a map of CAFOs in a given state.

    Args:
        match_df_path: file path to dataset of matched farms between Counterglow
            and state permit data
        unmatched_df_path: file path to dataset of unmatched farms between 
            Counterglow and state permit data
        state: state abbreviation for the state the map is for

    Returns:
        Map of the state with markers in different colors to represent farms 
        in state permit data, Counterglow, or both.

    """
    match_df = pd.read_csv(match_df_path)
    unmatched_df = pd.read_csv(unmatched_df_path)
    state_map = folium.Map(
        location=[match_df.lat.mean(), match_df.long.mean()],
        zoom_start=7,
        control_scale=True,
    )

    match_state = match_df[match_df["state"] == state]
    unmatched_state = unmatched_df[unmatched_df["state"] == state]

    add_points(state_map, match_state, "green") 
    # adding points that matched on both
    add_points(
        state_map, unmatched_state[unmatched_state["source"] != "Counterglow"], 
        "blue")  # adding points unique to permit dataset

    cg_unique = unmatched_df[unmatched_df["source"] == "Counterglow"]
    add_points(
        state_map, cg_unique[cg_unique["state"] == state], "red"
    )  # adding points unique to Counterglow

    return state_map