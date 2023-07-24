
import pandas as pd
import numpy as np
import requests
import folium
import geopandas as gpd
import shapely
from shapely.geometry import Polygon, mapping
from shapely import GeometryCollection, MultiPolygon
from shapely.ops import unary_union
import json
from pathlib import Path
from pyproj import Geod
from dotenv import load_dotenv
import os

# load mapbox API
load_dotenv()

# make it easier to access files
here = Path(__file__).resolve().parent

# import data
fsis_df = pd.read_csv(here.parent / "data/clean/cleaned_fsis_processors.csv")
info_df = pd.read_csv(here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv")

ALBERS_EQUAL_AREA = "EPSG:9822"
WGS84 = "EPSG:4326"
USA_LAT = 37.0902
USA_LNG = -95.7129

single_shapely = []
two_shapely = []
three_combined = []

empty_color = lambda x: {
    "fillColor": "00" # empty
}
one_plant_color = lambda x: {
    "fillColor": "#ED7117" # carrot
}
two_plant_color = lambda x: {
    "fillColor": "#ED7117" # carrot
}
three_plant_color = lambda x: {
    "fillColor": "#9F2B68" # amaranth
}


def isochrones(df, x, token):
    """Adds plant isochrones to fsis dataframe; captures area that is within an x mile raidus of the plant.

    Args:
        df: fsis_df, cleaned.
        x: radius of captured area (in driving distance).

    Returns:
        fsis_df with added column for isochrones.

    """
    
    MAPBOX_TOKEN = token
    ENDPOINT = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
    DRIVING_DISTANCE = str(int(x * 1609.34)) # 60 miles in meters: 90 percent of all birds were produced on farms within 60 miles of the plant, according to 2011 ARMS data

    isochrones = []
    for index, row in df.iterrows():
        lat = str(row['latitude'])
        lng = str(row['longitude'])

        # add driving radius isochrone to map
        url = ENDPOINT + lng + "," + lat + "?" + "contours_meters=" + DRIVING_DISTANCE + "&access_token=" + MAPBOX_TOKEN
        response = requests.get(url)
        isochrone = Polygon(response.json()['features'][0]['geometry']['coordinates'])
        isochrones.append(isochrone)

    df = df.copy()
    df["Isochrone"] = isochrones

    return df



def make_geo_df(df, dist, token):
    """Adds slightly simpligied isochrones to fsis dataframe.

    Args:
        df: fsis_df, cleaned.
        dist: radius of captured area (in driving distance) to be passed to isochrones function.

    Returns:
        geo_df with added column for isochrones and cleaned/simplified isochrones.

    """

    geo_df = isochrones(df, dist, token)
    geo_df = gpd.GeoDataFrame(geo_df).set_geometry("Isochrone").set_crs(WGS84, inplace = True)
    geo_df["Isochrone Cleaned"] = geo_df["Isochrone"].simplify(.01)

    return geo_df



def add_plants(df_map, dict, chrones, m):
    """Take geo_df and adds the plant isochrones to the map as well as sorts the isochrones by parent corporation.

    Args:
        df_map: geo_df that contains plant isochrones.
        dict: empty dictionary, gets filled with parent company names and geoshapes.
        chrones: empty list, gets filled with one isochrone for each parent company.
        m: base-map to add plants to.

    Returns:
        n/a; updates dict, chrones, and m.

    """

    plants_layer = folium.map.FeatureGroup(name="Large Poultry Plants")

    for index, row in df_map.iterrows():
        lat = str(row['latitude'])
        lng = str(row['longitude'])

        # set up plant tooltip
        name = row['Establishment Name']
        corp = row['Parent Corporation']
        address = row['Full Address']

        # add plant marker to map
        tooltip = folium.map.Tooltip(f"{name}<br>{address}<br>Parent Corporation: {corp}")
        folium.Marker(location=[lat, lng],tooltip=tooltip).add_to(plants_layer)

        isochrone = row['Isochrone Cleaned']
        corp = row['Parent Corporation']

        # sorting by parent corp
        if (corp in dict):
            dict[corp].append(isochrone)
        else:
            dict[corp] = [isochrone]

    for key in dict:
        chrone = shapely.unary_union(dict[key])
        chrones.append(chrone)

    plants_layer.add_to(m)



def single_plant_cap(chrones, single_shapely, dict, m):
    """Adds a layer containing areas that have access to one plant to country-wide visualization

    Args:
        chrones: list of isochrones, one for each parent corporation.
        single_shapely: empty list, gets filled with isochrones of areas that have access to only one plant.
        dict: dictionary of parent corporation names/geoshapes.
        m: base-map to add single-capture areas to.

    Returns:
        n/a, updates m.

    """

    for index, poly in enumerate(chrones):
        others = shapely.unary_union(chrones[:index] + chrones[index+1:])
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



def two_and_three_plant_cap(chrones, single_shapely, two_shapely, three_shapely, m):
    """Adds 2 layers to country-wide visualization 
        - One containing areas that have access to two plants
        - One containing areas that have access to three+ plants

    Args:
        chrones: list of isochrones, one for each parent corporation.
        single_shapely: isochrones of areas that have access to only one plant.
        two_shapely: empty list, gets filled with isochrones of areas that have access to two plants.
        three_shapely: empty list, gets filled with one isochrone of all areas that have access to three+ plants.
        m: base-map to add single-capture areas to.

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
        for j in range(i+1, len(isochrones_shapely_two_plants)):
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
            other_plants += isochrones_shapely_two_plants[i+1:j]
            other_plants += isochrones_shapely_two_plants[j+1:]

            # find the area where there's only two plants
            others_combined = shapely.unary_union(other_plants)
            captured_area = shapely.difference(two_plant_area, others_combined) # returns the part of geometry a that does not intersect with geometry b
            # remove the area that is captured by only one of the plants
            captured_area = shapely.difference(captured_area, single_plant_combined)
            if captured_area:
                two_shapely.append(captured_area)
    
    two_plant_layer = folium.map.FeatureGroup(name="Access to 2 Parent Corporations")
    two_plants_combined = shapely.unary_union(two_shapely)
    folium.GeoJson(two_plants_combined,style_function=two_plant_color).add_to(two_plant_layer)
    two_plant_layer.add_to(m)


    three_plant_layer = folium.map.FeatureGroup(name="Access to 3+ Parent Corporations")
    three_shapely = shapely.difference(everything, single_plant_combined)
    three_shapely = shapely.difference(three_shapely.buffer(0), two_plants_combined.buffer(0))
    three_combined.append(three_shapely)

    folium.GeoJson(three_shapely, style_function=three_plant_color).add_to(three_plant_layer)
    three_plant_layer.add_to(m)

    return



def save_map(single, two, three, dict):
    """Saves country-wide plant capture area map as geojson.

    Args:
        single: isochrones of areas that have access to only one plant.
        two: isochrones of areas that have access to two plants.
        three: isochrones of areas that have access to three+ plants.
        m: base-map to add single-capture areas to.

    Returns:
        n/a.

    """

    one_df = gpd.GeoDataFrame({"Plant Access": [1] * len(single), 
                            "Parent Corporation": list(dict.keys()), 
                            "Geometry": single})
    two_df = gpd.GeoDataFrame({"Plant Access": [2] * len(two), 
                            "Parent Corporation": [None] * len(two), 
                            "Geometry": two})
    three_df = gpd.GeoDataFrame({"Plant Access": [3] * len(three), 
                                "Parent Corporation": [None] * len(three), 
                                "Geometry": three})

    full_df = gpd.GeoDataFrame(pd.concat([one_df, two_df, three_df], ignore_index=True))
    full_df = full_df.set_geometry('Geometry')
    full_df.to_file(here.parent / "data/clean/isochrones_with_parent_corp.geojson", driver="GeoJSON")

    return



def state_level_geojson(df, map, single, two, three):
    """Assembles state-specific map of plant access, exports to data/clean as a geojson

    Args:
        df: geo_df containing all plant isochrones, raw and simplified.
        map: base-map for state-specific visualization.
        single: isochrones of areas that have access to only one plant.
        two: isochrones of areas that have access to two plants.
        three_plants_combined: one isochrone of all areas that have access to three+ plants.

    Returns:
        n/a.

    """

    us_states = gpd.read_file(here.parent / "data/gz_2010_us_040_00_500k.json").set_crs(WGS84)
    abb2state = {
        'AL': "Alabama", 
        'AR': "Arkansas", 
        'CA': "California", 
        'DE': "Delaware", 
        'FL': "Florida", 
        'GA': "Georgia", 
        'KY': "Kentucky", 
        'LA': "Louisiana", 
        'MD': "Maryland", 
        'MN': "Minnesota", 
        'MO': "Missouri",
        'MS': "Mississippi", 
        'NC': "North Carolina", 
        'NE': "Nebraska", 
        'OK': "Oklahoma", 
        'PA': "Pennsylvania", 
        'SC': "South Carolina", 
        'TN': "Tennessee", 
        'TX': "Texas", 
        'VA': "Virginia", 
        'WA': "Washington", 
        'WV': "West Virginia",
        'IA': "Iowa"
    }
    
    df_states = gpd.GeoDataFrame()

    corp_dfs = []
    for corp in df['Parent Corporation'].unique():
        new_df = df[df['Parent Corporation'] == corp]
        corp_dfs.append(new_df)

    states = df.State.unique()

    corps_joined = []
    for corp_df in corp_dfs:
        corp_geomtery = corp_df['Isochrone Cleaned'].unary_union
        corp_data = {
            "parent_corporation": corp_df.iloc[0]["Parent Corporation"],
            "geometry": corp_geomtery,
        }
        corps_joined.append(corp_data)

    df_corps_joined = gpd.GeoDataFrame(corps_joined)

    corp_state_geojsons = []
    single_plant_combined = shapely.unary_union(single)
    two_plants_combined = shapely.unary_union(two)

    for i, corp in df_corps_joined.iterrows():
        for state in states:
            state_name = abb2state[state]
            state_layer = folium.map.FeatureGroup(name=state_name, show=False)
            state_geometry = us_states[us_states["NAME"] == state_name]['geometry'].to_crs(WGS84)
            state_center = state_geometry.to_crs(ALBERS_EQUAL_AREA).centroid.to_crs(WGS84)

            one_plant = shapely.intersection(single_plant_combined,state_geometry).set_crs(WGS84).iloc[0]
            one_plant_one_corp_one_state = shapely.intersection(one_plant,corp.geometry)

            if one_plant_one_corp_one_state:

                geod = Geod(ellps="WGS84")
                area = abs(geod.geometry_area_perimeter(one_plant_one_corp_one_state)[0]) * (0.000621371**2)

                one_plant_one_state_data = {
                    "state": state_name,
                    "geometry": one_plant_one_corp_one_state,
                    "parent_corporation": corp.parent_corporation,
                    "area": area,
                    "corporate_access": 1
                }

                corp_state_geojsons.append(one_plant_one_state_data)

    for state in states:
        state_name = abb2state[state]
        state_layer = folium.map.FeatureGroup(name=state_name, show=False)
        state_geometry = us_states[us_states["NAME"] == state_name]['geometry'].to_crs(WGS84)
        state_center = state_geometry.to_crs(ALBERS_EQUAL_AREA).centroid.to_crs(WGS84)

        two_plants = shapely.intersection(two_plants_combined,state_geometry).set_crs(WGS84).iloc[0]
        three_plants = shapely.intersection(three,state_geometry).set_crs(WGS84).iloc[0]
            
        if two_plants:
            geod = Geod(ellps="WGS84")
            two_area = abs(geod.geometry_area_perimeter(two_plants)[0]) * (0.000621371**2)

            two_plants_one_state_data = {
                "state": state_name,
                "geometry": two_plants,
                "parent_corporation": np.nan,
                "area": two_area,
                "corporate_access": 2
            }

            corp_state_geojsons.append(two_plants_one_state_data)

        if three_plants:
            geod = Geod(ellps="WGS84")
            three_area = abs(geod.geometry_area_perimeter(three_plants)[0]) * (0.000621371**2)

            three_plants_one_state_data = {
                "state": state_name,
                "geometry": three_plants,
                "parent_corporation": np.nan,
                "area": three_area,
                "corporate_access": 3
            }

            corp_state_geojsons.append(three_plants_one_state_data)

    df_corp_state = gpd.GeoDataFrame(corp_state_geojsons)
    df_corp_state = df_corp_state.sort_values(by='state')
    df_corp_state.to_file(here.parent / "data/clean/all_states_with_parent_corp_by_corp.geojson", driver="GeoJSON")

    return



def full_script(token):
    # make base map for country-wide visualization
    m = folium.Map(location=[USA_LAT, USA_LNG],zoom_start=4)

    # dictionary of parent corps
    dict = {}
    chrones = []

    df_map = make_geo_df(fsis_df, 60, token)
    add_plants(df_map, dict, chrones, m)

    # assemble country-wide capture map, save as GEOJSON to data/clean
    single_plant_cap(chrones, single_shapely, dict, m)
    two_and_three_plant_cap(chrones, single_shapely, two_shapely, three_combined, m)
    save_map(single_shapely, two_shapely, three_combined, dict)
    m.save(here.parent / "html/poultry-map-smoothed.html")

    # make base map for state-specific visualization
    mm = folium.Map(location=[USA_LAT, USA_LNG],zoom_start=4)

    # assemble state-specific capture map, save as GEOJSON to data/clean
    state_level_geojson(df_map, mm, single_shapely, two_shapely, three_combined)
    mm.save(here.parent / "html/state-poultry-map-smoothed.html")

    return m


