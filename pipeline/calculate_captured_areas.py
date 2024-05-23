# TODO:...
"""Contains functions for creating a US map with markers for poultry processing 
    plants and isochrones representing area captured by the plants' parent 
    corporations.
"""

import pandas as pd
import geopandas as gpd
from tqdm import tqdm
from typing import List, Dict, Tuple
from constants import WGS84, CLEAN_DIR, GDF_STATES, STATE2ABBREV
import os
from datetime import datetime

tqdm.pandas()


def calculate_captured_areas(
    gdf_fsis,
    corp_col="Parent Corporation",
    chrone_col="isochrone",
    access_col="corp_access",
):
    # gdf_fsis = gdf_fsis.drop("geometry", axis=1).set_geometry(chrone_col).set_crs(WGS84)
    gdf_fsis = gdf_fsis.set_geometry(chrone_col).set_crs(WGS84)

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

    gdf_single_corp = gpd.overlay(GDF_STATES, gdf_single_corp, how="intersection")
    gdf_single_corp[access_col] = 1
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
    gdf_two_corps = gpd.overlay(GDF_STATES, gdf_two_corps)
    gdf_two_corps[access_col] = 2

    gdf_three_plus_corps = gpd.GeoDataFrame(
        geometry=[three_plus_corp_access_area], crs=WGS84
    )
    gdf_three_plus_corps = gpd.overlay(GDF_STATES, gdf_three_plus_corps)
    gdf_three_plus_corps[access_col] = 3

    isochrones = gpd.GeoDataFrame(
        pd.concat(
            [gdf_single_corp, gdf_two_corps, gdf_three_plus_corps], ignore_index=True
        )
    )

    isochrones["state"] = isochrones["state"].map(STATE2ABBREV)

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

    print(f"Saving to {RUN_DIR}/isochrones.geojson")
    isochrones.to_file(RUN_DIR / "isochrones.geojson", driver="GeoJSON")
