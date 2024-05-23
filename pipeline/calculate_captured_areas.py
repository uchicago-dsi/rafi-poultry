# TODO:...
"""Contains functions for creating a US map with markers for poultry processing 
    plants and isochrones representing area captured by the plants' parent 
    corporations.
"""

import pandas as pd
import geopandas as gpd
from tqdm import tqdm
from typing import List, Dict, Tuple
from constants import (
    US_STATES_FPATH,
    WGS84,
    CLEAN_DIR,
)
import os
from datetime import datetime

tqdm.pandas()


def calculate_captured_areas(
    gdf_fsis, corp_col="Parent Corporation", chrone_col="isochrone"
):
    gdf_fsis = gdf_fsis.drop("geometry", axis=1).set_geometry(chrone_col).set_crs(WGS84)

    # TODO: a bunch of this should be done elsewhere probably...load this from constants?
    gdf_states = gpd.read_file(US_STATES_FPATH).set_crs(WGS84)
    gdf_states = gdf_states.drop(["GEO_ID", "STATE", "LSAD", "CENSUSAREA"], axis=1)
    gdf_states = gdf_states.rename(columns={"NAME": "state"})

    # Dissolve by parent corporation to calculate access on a corporation (not plant) level
    gdf_single_corp = gdf_fsis.dissolve(by=corp_col).reset_index()[
        [corp_col, chrone_col]
    ]

    # Self join to find intersections in corporate access
    intersections = gpd.sjoin(
        gdf_single_corp, gdf_single_corp, how="inner", predicate="intersects"
    )
    # Each area will overlap with itself, so remove those
    intersections_filtered = (
        intersections[intersections.index != intersections["index_right"]]
        .copy()
        .to_crs(WGS84)
    )
    # We need to explicitly calculate the geometry of the intersection after matching
    print("Calculating intersections...")
    intersections_filtered["intersection_geometry"] = (
        intersections_filtered.progress_apply(
            lambda row: gdf_single_corp.at[row.name, chrone_col].intersection(
                gdf_single_corp.at[row["index_right"], chrone_col]
            ),
            axis=1,
        )
    )
    intersections_filtered = intersections_filtered.set_geometry(
        "intersection_geometry"
    ).set_crs(WGS84)
    intersections_filtered = intersections_filtered[
        [f"{corp_col}_left", f"{corp_col}_right", "intersection_geometry"]
    ]
    # This is still using the index for the corporations - reset so each intersection has a unique index
    intersections_filtered = intersections_filtered.reset_index()

    print("Calculating single plant access...")
    multi_corp_access_area = intersections_filtered["intersection_geometry"].unary_union
    # Take the difference between each corporate area and the area with access to more than one plant
    # This is the area that has access to only one corporation
    gdf_single_corp["Captured Area"] = gdf_single_corp[chrone_col].progress_apply(
        lambda x: x.difference(multi_corp_access_area)
    )
    gdf_single_corp = gdf_single_corp.set_geometry("Captured Area")

    gdf_single_corp = gpd.overlay(gdf_states, gdf_single_corp, how="intersection")
    gdf_single_corp["plant_access"] = 1
    gdf_single_corp = gdf_single_corp.drop("isochrone", axis=1)

    # Calculate the area that has access to two or more plants
    # Join intersections with corporate areas — we will groupby the number of corporate areas
    # that are in an intersection
    print("Calculating multi plant access...")
    corporate_access_join = gpd.sjoin(
        intersections_filtered, gdf_single_corp, how="left", predicate="intersects"
    )
    overlap_count = corporate_access_join.groupby(corporate_access_join.index).size()

    # Filter for intersections that have access to exactly two corporations
    # We know that these areas must be all of the spots with exactly two plant access
    two_corp_access_indeces = overlap_count[overlap_count == 2]
    two_corp_access_isochrones = intersections_filtered[
        intersections_filtered.index.isin(two_corp_access_indeces.index)
    ]
    two_corp_access_area = two_corp_access_isochrones[
        "intersection_geometry"
    ].unary_union

    # Remove the two plant access area from everything else
    # Remainder must have access to 3+ plants
    three_plus_corp_access_area = multi_corp_access_area - two_corp_access_area

    gdf_two_corps = gpd.GeoDataFrame(geometry=[two_corp_access_area], crs=WGS84)
    gdf_two_corps = gpd.overlay(gdf_states, gdf_two_corps)
    gdf_two_corps["plant_access"] = 2

    gdf_three_plus_corps = gpd.GeoDataFrame(
        geometry=[three_plus_corp_access_area], crs=WGS84
    )
    gdf_three_plus_corps = gpd.overlay(gdf_states, gdf_three_plus_corps)
    gdf_three_plus_corps["plant_access"] = 3

    isochrones = gpd.GeoDataFrame(
        pd.concat(
            [gdf_single_corp, gdf_two_corps, gdf_three_plus_corps], ignore_index=True
        )
    )

    return isochrones


if __name__ == "__main__":
    RUN_DIR = (
        CLEAN_DIR / f"captured_areas_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    os.makedirs(RUN_DIR, exist_ok=True)

    # TODO: is there a better way to do this?
    GDF_FSIS_PATH = CLEAN_DIR / "_clean_run" / "plants_with_isochrones.geojson"
    gdf_fsis = gpd.read_file(GDF_FSIS_PATH)

    # Note: rename "geometry" to match the expected from of GDF passed to function
    gdf_fsis["isochrone"] = gdf_fsis["geometry"]
    isochrones = calculate_captured_areas(gdf_fsis)

    isochrones.to_file(RUN_DIR / "isochrones.geojson", driver="GeoJSON")
