"""Contains functions for creating a US map with markers for poultry processing plants 
and isochrones representing area captured by the plants' parent corporations.
"""

import pandas as pd
import numpy as np
import requests
import folium
import geopandas as gpd
import shapely
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from pyproj import Geod
from typing import List, Dict, Tuple
from constants import ISOCHRONES_WITH_PARENT_CORP_FPATH, US_STATES_FPATH, ALL_STATES_GEOJSON_FPATH,\
    CLEANED_FSIS_PROCESSORS_FPATH, CLEANED_INFOGROUP_FPATH, DATA_DIR, ALBERS_EQUAL_AREA, WGS84, USA_LAT,\
    USA_LNG

single_shapely = []
two_shapely = []
three_combined = []

empty_color = lambda x: {"fillColor": "00"}  # empty
one_plant_color = lambda x: {"fillColor": "#ED7117"}  # carrot
two_plant_color = lambda x: {"fillColor": "#ED7117"}  # carrot
three_plant_color = lambda x: {"fillColor": "#9F2B68"}  # amaranth


def isochrones(coords: List[Tuple[float, float]], driving_dist_miles: float, token: str) -> pd.DataFrame :
    """Adds plant isochrones to fsis dataframe; captures area that is within an x mile radius of the plant.
            90 percent of all birds were produced on farms within 60 miles of the plant, according to 2011 ARMS data.

    Args:
        coords: list of tuples; lat and long for all processing plants.
        driving_dist_miles: int; radius of captured area (in driving distance).
        token: str; API token to access mapbox.

    Returns:
        list of plant isochrones

    """

    ENDPOINT = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
    DRIVING_DISTANCE_METERS = str(
        int(driving_dist_miles * 1609.34)
    )  # turns miles into meters

    isochrones = []
    for lat, lng in coords:

        # add driving radius isochrone to map
        url = (
            ENDPOINT
            + str(lng)
            + ","
            + str(lat)
            + "?"
            + "contours_meters="
            + DRIVING_DISTANCE_METERS
            + "&access_token="
            + token
        )
        response = requests.get(url)
        if not response.ok:
            raise Exception(f"Within the isochrone helper function, unable to access mapbox url using API token.\
                                The response had status code {response.status_code}. The error message was \
                                {response.text}")

        isochrone = Polygon(response.json()["features"][0]["geometry"]
                            ["coordinates"])
        isochrones.append(isochrone)

    return isochrones


def make_geo_df(df: pd.DataFrame, dist: float, token: str, simplify: float = 0.01) -> pd.DataFrame:
    """Adds slightly simplified isochrones to fsis dataframe.

    Args:
        df: dataframe; the cleaned fsis_df file.
        dist: float; radius of captured area (in driving distance) to be passed to isochrones function.
        token: str; API token to access mapbox.
        simplify: float; by what degree to simplify each isochrone, default is 0.01.

    Returns:
        geo_df with added column for isochrones and cleaned/simplified isochrones.

    """

    lats_and_longs = list(map(tuple, df[["latitude", "longitude"]].to_numpy()))

    df['Isochrone'] = isochrones(lats_and_longs, dist, token)
    df = (
        gpd.GeoDataFrame(df).set_geometry("Isochrone").set_crs(WGS84, inplace=True)
    )

    df["Isochrone Cleaned"] = df["Isochrone"].simplify(simplify)

    return df


def add_plants(df_map: pd.DataFrame, dict: dict, chrones: list, m: folium.Map):
    """Take geo_df and adds the plant isochrones to the map as well as sorts the isochrones by parent corporation.

    Args:
        df_map: dataframe; geo_df that contains plant isochrones.
        dict: empty dictionary; gets filled with parent company names and geoshapes.
        chrones: empty list; gets filled with one isochrone for each parent company.
        m: folium map; base to add plants to.

    Returns:
        n/a; updates dict, chrones, and m.

    """

    plants_layer = folium.map.FeatureGroup(name="Large Poultry Plants")

    for _, row in df_map.iterrows():
        lat = str(row["latitude"])
        lng = str(row["longitude"])

        # set up plant tooltip
        name = row["Establishment Name"]
        corp = row["Parent Corporation"]
        address = row["Full Address"]

        # add plant marker to map
        tooltip = folium.map.Tooltip(
            f"{name}<br>{address}<br>Parent Corporation: {corp}"
        )
        folium.Marker(location=[lat, lng], tooltip=tooltip).add_to(plants_layer)

        isochrone = row["Isochrone Cleaned"]
        corp = row["Parent Corporation"]

        # sorting by parent corp
        if corp in dict:
            dict[corp].append(isochrone)
        else:
            dict[corp] = [isochrone]

    for key in dict:
        chrone = shapely.unary_union(dict[key])
        chrones.append(chrone)

    plants_layer.add_to(m)


def single_plant_cap(chrones: list, single_shapely: list, dict: dict, m: folium.Map):
    """Adds a layer containing areas that have access to one plant to country-wide visualization

    Args:
        chrones: list; isochrones, one for each parent corporation.
        single_shapely: empty list; gets filled with isochrones of areas that have access to only one plant.
        dict: dictionary; parent corporation names/geoshapes.
        m: folium map; base to add single-capture areas to.

    Returns:
        n/a, updates m.

    """

    for index, poly in enumerate(chrones):
        others = shapely.unary_union(chrones[:index] + chrones[index + 1 :])
        single_plant = shapely.difference(poly, others)
        single_shapely.append(single_plant)

    parent_names = list(dict.keys())

    for index, poly in enumerate(single_shapely):
        corp = parent_names[index]
        title = "Only access to " + corp
        layer = folium.map.FeatureGroup(name=title)
        tooltip = folium.map.Tooltip(f"Parent Corporation: {corp}")
        folium.GeoJson(poly, tooltip=tooltip).add_to(layer)
        layer.add_to(m)

    return


def two_and_three_plant_cap(chrones: list, single_shapely: list, two_shapely: list, three_shapely: list, m: folium.Map):
    """Adds 2 layers to country-wide visualization
        - One containing areas that have access to two plants
        - One containing areas that have access to three+ plants

    Args:
        chrones: list; isochrones, one for each parent corporation.
        single_shapely: list; isochrones of areas that have access to only one plant.
        two_shapely: empty list; gets filled with isochrones of areas that have access to two plants.
        three_shapely: empty list; gets filled with one isochrone of all areas that have access to three+ plants.
        m: folium map; base to add two and three capture areas to.

    Returns:
        n/a, updates m.

    """

    everything = shapely.unary_union(chrones)
    single_plant_combined = shapely.unary_union(single_shapely)
    competition_single_plant = shapely.difference(everything, single_plant_combined)

    isochrones_shapely_two_plants = []
    for isochrone in chrones:
        if isochrone.intersection(competition_single_plant):
            isochrones_shapely_two_plants.append(isochrone)

    for i in range(len(isochrones_shapely_two_plants)):
        for j in range(i + 1, len(isochrones_shapely_two_plants)):
            plant_1 = isochrones_shapely_two_plants[i]
            plant_2 = isochrones_shapely_two_plants[j]

            # check if there's an intersection between the areas
            if not plant_1.intersection(plant_2):
                continue
            else:
                two_plant_area = shapely.unary_union([plant_1, plant_2])

            # exclude first plant
            other_plants = isochrones_shapely_two_plants[:i]
            # exclude second plant
            other_plants += isochrones_shapely_two_plants[i + 1 : j]
            other_plants += isochrones_shapely_two_plants[j + 1 :]

            # find the area where there's only two plants
            others_combined = shapely.unary_union(other_plants)
            captured_area = shapely.difference(
                two_plant_area, others_combined
            )  # returns the part of geometry a that does not intersect with geometry b
            # remove the area that is captured by only one of the plants
            captured_area = shapely.difference(captured_area, single_plant_combined)
            if captured_area:
                two_shapely.append(captured_area)

    two_plant_layer = folium.map.FeatureGroup(name="Access to 2 Parent Corporations")
    two_plants_combined = shapely.unary_union(two_shapely)
    folium.GeoJson(two_plants_combined, style_function=two_plant_color).add_to(
        two_plant_layer
    )
    two_plant_layer.add_to(m)

    three_plant_layer = folium.map.FeatureGroup(name="Access to 3+ Parent Corporations")
    three_shapely = shapely.difference(everything, single_plant_combined)
    three_shapely = shapely.difference(
        three_shapely.buffer(0), two_plants_combined.buffer(0)
    )
    three_combined.append(three_shapely)

    folium.GeoJson(three_shapely, style_function=three_plant_color).add_to(
        three_plant_layer
    )
    three_plant_layer.add_to(m)

    return


def save_map(single: list, two: list, three: list, dict: dict):
    """Saves country-wide plant capture area map as geojson.

    Args:
        single: list; isochrones of areas that have access to only one plant.
        two: list; isochrones of areas that have access to two plants.
        three: list; isochrones of areas that have access to three+ plants.
        dict: dictionary; contains parent corporations.

    Returns:
        n/a.

    """

    one_df = gpd.GeoDataFrame(
        {
            "Plant Access": [1] * len(single),
            "Parent Corporation": list(dict.keys()),
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
    full_df.to_file(
        ISOCHRONES_WITH_PARENT_CORP_FPATH, driver="GeoJSON"
    )

    return


def state_level_geojson(df: pd.DataFrame, single:list, two: list, three: list):
    """Assembles state-specific map of plant access, exports to data/clean as a geojson

    Args:
        df: dataframe; contains all plant isochrones, raw and simplified.
        single: list; isochrones of areas that have access to only one plant.
        two: list; isochrones of areas that have access to two plants.
        three: list; one isochrone of all areas that have access to three+ plants.

    Returns:
        n/a.

    """

    us_states = gpd.read_file(US_STATES_FPATH).set_crs(
        WGS84
    )
    abb2state = {
        "AL": "Alabama",
        "AR": "Arkansas",
        "CA": "California",
        "DE": "Delaware",
        "FL": "Florida",
        "GA": "Georgia",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "MD": "Maryland",
        "MN": "Minnesota",
        "MO": "Missouri",
        "MS": "Mississippi",
        "NC": "North Carolina",
        "NE": "Nebraska",
        "OK": "Oklahoma",
        "PA": "Pennsylvania",
        "SC": "South Carolina",
        "TN": "Tennessee",
        "TX": "Texas",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "IA": "Iowa",
    }

    df_states = gpd.GeoDataFrame()

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

    for _, corp in df_corps_joined.iterrows():
        for state in states:
            state_name = abb2state[state]
            state_layer = folium.map.FeatureGroup(name=state_name, show=False)
            state_geometry = us_states[us_states["NAME"] == state_name][
                "geometry"
            ].to_crs(WGS84)
            state_center = state_geometry.to_crs(ALBERS_EQUAL_AREA).centroid.to_crs(
                WGS84
            )

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
        state_layer = folium.map.FeatureGroup(name=state_name, show=False)
        state_geometry = us_states[us_states["NAME"] == state_name]["geometry"].to_crs(
            WGS84
        )
        state_center = state_geometry.to_crs(ALBERS_EQUAL_AREA).centroid.to_crs(WGS84)

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
    df_corp_state.to_file(
        ALL_STATES_GEOJSON_FPATH,
        driver="GeoJSON",
    )

    return


def full_script(token: str, distance: float=60) -> folium.Map:
    """Loads in cleaned data, adds isochrones based on passed radius, calculates areas that have
    access to 1, 2, and 3+ plants, and plots them on a country-wide map and a state-level map

    Args:
        token: str; API token to access mapbox.
        distance: float; radius of plant isochrones based on driving distance, in miles.
            default is 60 miles.

    Returns:
        country-wide map, outputs two html files.

    """

    # import cleaned data
    fsis_df = pd.read_csv(CLEANED_FSIS_PROCESSORS_FPATH)
    info_df = pd.read_csv(CLEANED_INFOGROUP_FPATH)

    # make base map for country-wide visualization
    m = folium.Map(location=[USA_LAT, USA_LNG], zoom_start=4)

    # dictionary of parent corps
    dict = {}
    chrones = []

    # Are we loading the token in one of the other files and passing it to all of these functions?
    # It looks like we load the token in this file too?
    df_map = make_geo_df(fsis_df, distance, token)
    add_plants(df_map, dict, chrones, m)

    # assemble country-wide capture map, save as GEOJSON to data/clean
    single_plant_cap(chrones, single_shapely, dict, m)
    two_and_three_plant_cap(chrones, single_shapely, two_shapely, three_combined, m)
    save_map(single_shapely, two_shapely, three_combined, dict)
    m.save(DATA_DIR / "html/poultry-map-smoothed.html")

    # assemble state-specific capture map, save as GEOJSON to data/clean
    state_level_geojson(df_map, single_shapely, two_shapely, three_combined)

    return m

if __name__ == "__main__":
    full_script("pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xqc3FnN2NjMDBqczNkdDNmdjBvdnU0ciJ9.0RfS-UsqS63pbAuqrE_REw")
