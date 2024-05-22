"""Contains functions for creating a US map with markers for poultry processing 
    plants and isochrones representing area captured by the plants' parent 
    corporations.
"""

import pandas as pd
from pandas import DataFrame
import numpy as np
import requests
import folium
import geopandas as gpd
from tqdm import tqdm
import shapely
from shapely.geometry import Polygon
from pyproj import Geod
from typing import List, Dict, Tuple
from constants import (
    ISOCHRONES_WITH_PARENT_CORP_FPATH,
    US_STATES_FPATH,
    ALL_STATES_GEOJSON_FPATH,
    CLEANED_MATCHED_PLANTS_FPATH,
    WGS84,
    USA_LAT,
    USA_LNG,
)
import os
from pathlib import Path
from tqdm import tqdm

tqdm.pandas()

current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/"
DATA_DIR_RAW = DATA_DIR / "raw/"
DATA_DIR_CLEAN = DATA_DIR / "clean/"

empty_color = lambda x: {"fillColor": "00"}  # empty
one_plant_color = lambda x: {"fillColor": "#ED7117"}  # carrot
two_plant_color = lambda x: {"fillColor": "#ED7117"}  # carrot
three_plant_color = lambda x: {"fillColor": "#9F2B68"}  # amaranth

abb2state = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


# def get_isochrones(
#     coords: List[Tuple[float, float]], driving_dist_miles: float, token: str
# ) -> pd.DataFrame:
#     """Adds plant isochrones to fsis dataframe; captures area that is within
#             an x mile radius of the plant. 90 percent of all birds were
#             produced on farms within 60 miles of the plant, according to 2011
#             ARMS data.

#     Args:
#         coords: list of tuples; lat and long for all processing plants.
#         driving_dist_miles: int; radius of captured area (in driving distance).
#         token: str; API token to access mapbox.

#     Returns:
#         list of plant isochrones

#     """

#     ENDPOINT = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
#     DRIVING_DISTANCE_METERS = str(
#         int(driving_dist_miles * 1609.34)
#     )  # turns miles into meters

#     isochrones = []
#     for lat, lng in tqdm(coords, desc="Mapbox Isochrones"):
#         # add driving radius isochrone to map
#         url = (
#             ENDPOINT
#             + str(lng)
#             + ","
#             + str(lat)
#             + "?"
#             + "contours_meters="
#             + DRIVING_DISTANCE_METERS
#             + "&access_token="
#             + token
#         )
#         response = requests.get(url)
#         if not response.ok:
#             raise Exception(
#                 f"Within the isochrone helper function, unable to \
#                                 access mapbox url using API token. Response \
#                                 had status code {response.status_code}. \
#                                 Error message was {response.text}"
#             )

#         isochrone = Polygon(response.json()["features"][0]["geometry"]["coordinates"])
#         isochrones.append(isochrone)

#     return isochrones


# def add_plants(
#     df_map: pd.DataFrame,
#     # parent_dict: Dict[str, Polygon],
# ) -> None:
#     """Take geo_df and adds the plant isochrones to the map as well as sorts
#         the isochrones by parent corporation.

#     Args:
#         df_map: dataframe; geo_df that contains plant isochrones.
#         parent_dict: empty dictionary; gets filled with parent company names and
#             geoshapes.
#         chrones: empty list; gets filled with one isochrone for each parent
#             company.
#         m: folium map; base to add plants to.

#     Returns:
#         n/a; updates parent_dict, chrones, and m.

#     """

#     chrones = []
#     parent_dict = {}

#     for _, row in df_map.iterrows():
#         isochrone = row["Isochrone Cleaned"]
#         corp = row["Parent Corporation"]

#         # sorting by parent corp
#         if corp in parent_dict:
#             parent_dict[corp].append(isochrone)
#         else:
#             parent_dict[corp] = [isochrone]

#     for key in parent_dict:
#         chrone = shapely.unary_union(parent_dict[key])
#         chrones.append(chrone)

#     return chrones, parent_dict


def get_single_plant_access(
    isochrones: List[Polygon],
) -> None:
    """Adds a layer containing areas that have access to one plant to
        country-wide visualization

    Args:
        chrones: list; isochrones, one for each parent corporation.
        single_shapely: empty list; gets filled with isochrones of areas that
            have access to only one plant.
        parent_dict: dictionary; parent corporation names/geoshapes.
        m: folium map; base to add single-capture areas to.

    Returns:
        TODO
        n/a, updates m.

    """
    single_plant_access = []

    for index, isochrone in tqdm(
        enumerate(isochrones), desc="Calculate single plant capture..."
    ):
        other_plant_access = shapely.unary_union(
            isochrones[:index] + isochrones[index + 1 :]
        )
        this_plant_access = shapely.difference(isochrone, other_plant_access)
        single_plant_access.append(this_plant_access)

    return single_plant_access


def get_two_and_three_plant_access(
    isochrones: List[Polygon],
    single_plant_access: List[Polygon],
) -> None:
    """Adds 2 layers to country-wide visualization
        - One containing areas that have access to two plants
        - One containing areas that have access to three+ plants

    Args:
        chrones: list; isochrones, one for each parent corporation.
        single_shapely: list; isochrones of areas that have access to only one
            plant.
        two_shapely: empty list; gets filled with isochrones of areas that have
            access to two plants.
        three_shapely: empty list; gets filled with one isochrone of all areas
            that have access to three+ plants.
        m: folium map; base to add two and three capture areas to.

    Returns:
        n/a, updates m.

    """

    # TODO: what is the deal with three_combined?
    two_shapely = []
    three_shapely = []
    three_combined = []

    everything = shapely.unary_union(isochrones)
    single_plant_combined = shapely.unary_union(single_plant_access)
    two_plus_access = shapely.difference(everything, single_plant_combined)

    two_plus_access_isochrones = []
    for isochrone in tqdm(isochrones, desc="Calculating 2+ plant intersections"):
        if isochrone.intersection(two_plus_access):
            two_plus_access_isochrones.append(isochrone)

    breakpoint()

    # TODO: Clean this up but...
    # We are iterating through all of the individual plant isochrones that we know are part of the two_plus_access
    # Then, we do pairwise comparisons between each plant isochrone to see if they intersect
    # If they do intersect, then we create a new isochrone that is the union of the two intersecting isochrones
    # We know that this area has access to two plants
    # I think I should probaly use a spatial union to do this...
    for i in tqdm(
        range(len(two_plus_access_isochrones)), desc="Two and three plant capture"
    ):
        for j in range(i + 1, len(two_plus_access_isochrones)):
            plant_1 = two_plus_access_isochrones[i]
            plant_2 = two_plus_access_isochrones[j]

            # check if there's an intersection between the areas
            if not plant_1.intersection(plant_2):
                continue
            else:
                two_plant_area = shapely.unary_union([plant_1, plant_2])

            # exclude first plant
            other_plants = two_plus_access_isochrones[:i]
            # exclude second plant
            other_plants += two_plus_access_isochrones[i + 1 : j]
            other_plants += two_plus_access_isochrones[j + 1 :]

            # find the area where there's only two plants
            others_combined = shapely.unary_union(other_plants)
            captured_area = shapely.difference(
                two_plant_area, others_combined
            )  # returns part of geom a that doesn't intersect with geom b
            # remove the area that is captured by only one of the plants
            captured_area = shapely.difference(captured_area, single_plant_combined)
            if captured_area:
                two_shapely.append(captured_area)

    two_plants_combined = shapely.unary_union(two_shapely)
    three_shapely = shapely.difference(everything, single_plant_combined)
    three_shapely = shapely.difference(
        three_shapely.buffer(0), two_plants_combined.buffer(0)
    )
    three_combined.append(three_shapely)

    return two_shapely, three_combined


def save_map(
    single: List[Polygon],
    two: List[Polygon],
    three: List[Polygon],
    parent_dict: Dict[str, Polygon],
) -> None:
    """Saves country-wide plant capture area map as geojson.

    Args:
        single: list; isochrones of areas that have access to only one plant.
        two: list; isochrones of areas that have access to two plants.
        three: list; isochrones of areas that have access to three+ plants.
        parent_dict: dictionary; contains parent corporations.

    Returns:
        n/a.

    """
    tqdm.write("Saving country-wide geojson...")

    one_df = gpd.GeoDataFrame(
        {
            "Plant Access": [1] * len(single),
            "Parent Corporation": list(parent_dict.keys()),
            "Geometry": single,
        }
    )
    two_df = gpd.GeoDataFrame(
        {
            "Plant Access": [2] * len(two),
            "Parent Corporation": [None] * len(two),
            "Geometry": two,
        }
    )
    three_df = gpd.GeoDataFrame(
        {
            "Plant Access": [3] * len(three),
            "Parent Corporation": [None] * len(three),
            "Geometry": three,
        }
    )

    full_df = gpd.GeoDataFrame(pd.concat([one_df, two_df, three_df], ignore_index=True))
    full_df = full_df.set_geometry("Geometry")
    full_df.to_file(ISOCHRONES_WITH_PARENT_CORP_FPATH, driver="GeoJSON")


def state_level_geojson(
    df: pd.DataFrame, single: List[Polygon], two: List[Polygon], three: List[Polygon]
) -> None:
    """Assembles state-specific map of plant access, exports to data/clean as
        a geojson

    # TODO: These are bad arg names — fix this
    Args:
        df: dataframe; contains all plant isochrones, raw and simplified.
        single: list; isochrones of areas that have access to only one plant.
        two: list; isochrones of areas that have access to two plants.
        three: list; one isochrone of all areas that have access to three+
            plants.

    Returns:
        n/a.

    """
    us_states = gpd.read_file(US_STATES_FPATH).set_crs(WGS84)

    corp_dfs = []
    for corp in df["Parent Corporation"].unique():
        new_df = df[df["Parent Corporation"] == corp]
        corp_dfs.append(new_df)

    states = df.State.unique()

    corps_joined = []
    for corp_df in corp_dfs:
        corp_geomtery = corp_df["Isochrone Cleaned"].unary_union
        corp_data = {
            "parent_corporation": corp_df.iloc[0]["Parent Corporation"],
            "geometry": corp_geomtery,
        }
        corps_joined.append(corp_data)

    df_corps_joined = gpd.GeoDataFrame(corps_joined)

    corp_state_geojsons = []
    single_plant_combined = shapely.unary_union(single)
    two_plants_combined = shapely.unary_union(two)

    tqdm.write("Saving state-level GeoJSON...")
    for _, corp in df_corps_joined.iterrows():
        for state in states:
            state_name = abb2state[state]
            state_geometry = us_states[us_states["NAME"] == state_name][
                "geometry"
            ].to_crs(WGS84)

            one_plant = (
                shapely.intersection(single_plant_combined, state_geometry)
                .set_crs(WGS84)
                .iloc[0]
            )
            one_plant_one_corp_one_state = shapely.intersection(
                one_plant, corp.geometry
            )

            if one_plant_one_corp_one_state:
                geod = Geod(ellps="WGS84")
                area = abs(
                    geod.geometry_area_perimeter(one_plant_one_corp_one_state)[0]
                ) * (0.000621371**2)

                one_plant_one_state_data = {
                    "state": state_name,
                    "geometry": one_plant_one_corp_one_state,
                    "parent_corporation": corp.parent_corporation,
                    "area": area,
                    "corporate_access": 1,
                }

                corp_state_geojsons.append(one_plant_one_state_data)

    for state in states:
        state_name = abb2state[state]
        state_geometry = us_states[us_states["NAME"] == state_name]["geometry"].to_crs(
            WGS84
        )

        two_plants = (
            shapely.intersection(two_plants_combined, state_geometry)
            .set_crs(WGS84)
            .iloc[0]
        )
        three_plants = (
            shapely.intersection(three, state_geometry).set_crs(WGS84).iloc[0]
        )

        if two_plants:
            geod = Geod(ellps="WGS84")
            two_area = abs(geod.geometry_area_perimeter(two_plants)[0]) * (
                0.000621371**2
            )

            two_plants_one_state_data = {
                "state": state_name,
                "geometry": two_plants,
                "parent_corporation": np.nan,
                "area": two_area,
                "corporate_access": 2,
            }

            corp_state_geojsons.append(two_plants_one_state_data)

        if three_plants:
            geod = Geod(ellps="WGS84")
            three_area = abs(geod.geometry_area_perimeter(three_plants)[0]) * (
                0.000621371**2
            )

            three_plants_one_state_data = {
                "state": state_name,
                "geometry": three_plants,
                "parent_corporation": np.nan,
                "area": three_area,
                "corporate_access": 3,
            }

            corp_state_geojsons.append(three_plants_one_state_data)

    df_corp_state = gpd.GeoDataFrame(corp_state_geojsons)
    df_corp_state = df_corp_state.sort_values(by="state")

    return df_corp_state
    # df_corp_state.to_file(
    #     ALL_STATES_GEOJSON_FPATH,
    #     driver="GeoJSON",
    # )


def full_script(
    df_matched_plants: DataFrame, token: str, distance: float = 60
) -> folium.Map:
    """Loads in cleaned data, adds isochrones based on passed radius,
        calculates areas that have access to 1, 2, and 3+ plants, and plots
        them on a country-wide map and a state-level map

    Args:
        TODO: Update docstring
        token: str; API token to access mapbox.
        distance: float; radius of plant isochrones based on driving distance,
            in miles; default is 60 miles.

    Returns:
        country-wide map, outputs two html files.

    """

    # TODO: should probably move this stuff out of this script and into the main pipeline
    df_map = make_geo_df(df_matched_plants, distance, token)
    # TODO: It seems like the parent dict isn't actually used???
    # It gets passed to one of the functions but the other one just does it???
    chrones, parent_dict = add_plants(df_map)

    single_shapely = single_plant_cap(chrones)
    two_shapely, three_combined = two_and_three_plant_cap(chrones, single_shapely)

    # TODO: This is actually the full country. Rename this function.
    # Should probably return the object also and then save it later?
    # Or do we even need this at all? I think the one with state info is what we actually need?
    # save_map(single_shapely, two_shapely, three_combined, parent_dict)

    # assemble state-specific capture map
    df_corp_state = state_level_geojson(
        df_map, single_shapely, two_shapely, three_combined
    )

    return df_corp_state


# TODO: Set up filepaths
def calculate_captured_areas(
    gdf_fsis, corp_col="Parent Corporation", chrone_col="isochrone"
):
    # TODO: a bunch of this should be done elsewhere probably
    gdf_states = gpd.read_file(US_STATES_FPATH).set_crs(WGS84)
    gdf_states = gdf_states.drop(["GEO_ID", "STATE", "LSAD", "CENSUSAREA"], axis=1)
    gdf_states = gdf_states.rename(columns={"NAME": "state"})

    gdf_fsis = gdf_fsis.set_crs(WGS84).set_geometry("isochrone")
    simplify = 0.01
    chrone_col_simplified = f"{chrone_col}_simplified"
    gdf_fsis[chrone_col_simplified] = gdf_fsis[chrone_col].simplify(simplify)

    # TODO: Is "Matched_Company" what we actually want? Review the FSIS matching code
    # Dissolve by parent corporation so we are calcualting access on a corporation level
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
    # We need to explicitly calculate the geometry of the intersection
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
    # This is using the index for the corporations so reset the index so each intersection has a unique index
    intersections_filtered = intersections_filtered.reset_index()

    # Calculate single plant access area
    print("Calculating single plant access...")
    multi_corp_access_area = intersections_filtered["intersection_geometry"].unary_union
    # Take the difference between each corporate area and the area with access to more than one plant
    # This is the area that has access to only one corporation
    gdf_single_corp["Captured Area"] = gdf_single_corp[chrone_col].progress_apply(
        lambda x: x.difference(multi_corp_access_area)
    )
    gdf_single_corp = gdf_single_corp.set_geometry("Captured Area")

    # TODO: move the file saving stuff
    gdf_single_corp = gpd.overlay(gdf_states, gdf_single_corp, how="intersection")
    gdf_single_corp = gdf_single_corp.drop("isochrone", axis=1)
    gdf_single_corp.to_file("single_corp_access.geojson", driver="GeoJSON")

    # Calculate the area that has access to two or more plants
    # Join intersections with corporate areas — we will groupby the number of corporate areas
    # that are in an intersection
    print("Calculating multi plant access...")
    corporate_access_join = gpd.sjoin(
        intersections_filtered, gdf_single_corp, how="left", predicate="intersects"
    )
    overlap_count = corporate_access_join.groupby(corporate_access_join.index).size()
    # Filter for intersections that have access to exactly two corporations
    # We know, then, that these areas must be all of the spots with exactly two plant access
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

    # TODO: Move file saving
    print("Saving files...")
    gdf_two_corps.to_file("two_corp_access.geojson", driver="GeoJSON")

    gdf_three_plus_corps = gpd.GeoDataFrame(
        geometry=[three_plus_corp_access_area], crs=WGS84
    )
    gdf_three_plus_corps = gpd.overlay(gdf_states, gdf_three_plus_corps)

    gdf_three_plus_corps.to_file("three_plus_corp_access.geojson", driver="GeoJSON")

    return (
        gdf_single_corp,
        gdf_two_corps,
        gdf_three_plus_corps,
    )


if __name__ == "__main__":
    # TODO: add file reading management, args, whatever
    GDF_FSIS_PATH = (
        DATA_DIR_CLEAN
        / "clean_fsis_isochrones_2024-05-22_00-50-25"
        / "plants_with_isochrones.geojson"
    )
    gdf_fsis = gpd.read_file(GDF_FSIS_PATH)

    # Note: rename "geometry" to match the expected from of GDF passed to function
    gdf_fsis["isochrone"] = gdf_fsis["geometry"]
    calculate_captured_areas(gdf_fsis)
