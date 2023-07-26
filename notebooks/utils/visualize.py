import pandas as pd
import numpy as np
import folium


def add_points(state_map, state_df, color):
    """Adds markers to a given state map based on location to represent farms.

    Args:
        state_map: map to add markers to
        state_df: DataFrame containing the farms and locations to be added to the map
        color: color for the markers as a string

    Returns:
        N/A, adds points to existing map

    """
    for index, location_info in state_df.iterrows():
        folium.Marker([location_info["lat"], location_info["long"]],\
            popup=location_info["name"], icon=folium.Icon(color=color)).add_to(state_map)


def map_state(match_df_path, unmatched_df_path, state):
    """Creates a map of CAFOs in a given state.

    Args:
        match_df_path: file path (string) to dataset of matched farms between Counterglow and state permit data
        unmatched_df_path: file path (string) to dataset of unmatched farms between Counterglow and state permit data
        state: state abbreviation for the state the map is for

    Returns:
        Map of the state with markers in different colors to represent farms in state permit data, Counterglow, or both.

    """
    match_df = pd.read_csv(match_df_path)
    unmatched_df = pd.read_csv(unmatched_df_path)
    state_map = folium.Map(location=[match_df.lat.mean(), match_df.long.mean()], zoom_start=7, control_scale=True)

    match_state = match_df[match_df["state"]==state]
    unmatched_state = unmatched_df[unmatched_df["state"]==state]
    
    add_points(state_map, match_state, "green") # adding points that matched on both
    add_points(state_map, unmatched_state[unmatched_state["source"]!="Counterglow"], "blue") # adding points unique to permit dataset
    
    cg_unique = unmatched_df[unmatched_df["source"]=="Counterglow"]
    add_points(state_map, cg_unique[cg_unique["state"]==state], "red") # adding points unique to Counterglow 

    return state_map

if __name__ == "__main__":
    match_df = pd.read_csv("../data/clean/matched_farms.csv")
    states = match_df["state"].unique().tolist()

    for state in states:
        path = "../html/cafo_poultry_eda_" + "state" + ".html"
        map_state("../data/clean/matched_farms.csv", "../data/clean/unmatched_farms.csv", state).save(path)