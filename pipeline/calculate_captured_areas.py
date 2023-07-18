
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

# make it easier to access files
here = Path(__file__).resolve().parent

# import data
fsis_df = pd.read_csv(here.parent / "data/clean/cleaned_fsis_processors.csv")
info_df = pd.read_csv(here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv")

USA_LAT = 37.0902
USA_LNG = -95.7129

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


def isochrones(df):
    
    MAPBOX_TOKEN = "pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xncGpzbmhhMTBwdzNnbXJjNWlzaTY2aCJ9.UhUELBA2iNIDsTN9YESsIw"
    ENDPOINT = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
    DRIVING_DISTANCE = str(int(60 * 1609.34)) # 60 miles in meters: 90 percent of all birds were produced on farms within 60 miles of the plant, according to 2011 ARMS data

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



def make_geo_df(df):

    geo_df = isochrones(df)
    geo_df = gpd.GeoDataFrame(geo_df).set_geometry("Isochrone").set_crs(WGS84, inplace = True)
    geo_df["Isochrone Cleaned"] = geo_df["Isochrone"].simplify(.01)

    return geo_df



# add markers and isochrones to map, sort isochrones by parent company
# create an empty dictionary to fill with unique parent companies 
def add_more_isochrones(df, dict, chrones, m):
    """Example function with PEP 484 type annotations.

    Args:
        df: 
        dict: empty dictionary, filled with parent company names and geoshapes.
        isochrones: empty list, filled with an isochrone for each parent company.

    Returns:
        hm

    """

    df_map = make_geo_df(df)
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

        # Can add the isochrones to the map, too, but this gets pretty cluttered with the other geospatial data
        # add driving radius isochrone to map layer
        # geojson = folium.GeoJson(row['Isochrone Cleaned'], style_function=empty_color)
        # geojson.add_to(driving_distance_layer)



def single_plant_cap(chrones, single_shapely, dict, m):
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



def two_and_three_plant_cap(chrones, single_shapely, two_shapely, m):
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

    three_plants_combined = shapely.difference(everything, single_plant_combined)
    three_plants_combined = shapely.difference(three_plants_combined.buffer(0), two_plants_combined.buffer(0))

    three_plant_layer = folium.map.FeatureGroup(name="Access to 3+ Parent Corporations")
    folium.GeoJson(three_plants_combined,style_function=three_plant_color).add_to(three_plant_layer)
    three_plant_layer.add_to(m)

    return



def save_map(single, two, three, dict):
    one_df = gpd.GeoDataFrame({"Plant Access": [1] * len(single), 
                            "Parent Corporation": list(dict.keys()), 
                            "Geometry": single})
    two_df = gpd.GeoDataFrame({"Plant Access": [2] * len(two), 
                            "Parent Corporation": [None] * len(two), 
                            "Geometry": two})
    three_df = gpd.GeoDataFrame({"Plant Access": [3] * len(three), 
                                "Parent Corporation": [None] * len(three), 
                                "Geometry": three})

    full_df = gpd.GeoDataFrame(pd.concat([one_df, two_df, three_df, four_df], ignore_index=True))
    full_df = full_df.set_geometry('Geometry')
    full_df.to_file(here.parent / "data/clean/isochrones_with_parent_corp.geojson", driver="GeoJSON")

    return



if __name__ == "__main__":
    m = folium.Map(location=[USA_LAT, USA_LNG],zoom_start=4)

    dict = {}
    chrones = []

    single_shapely = []
    two_shapely = []
    three_shapely = []

    add_more_isochrones(fsis_df, dict, chrones, m)
    single_plant_cap(chrones, single_shapely, dict, m)
    two_and_three_plant_cap(chrones, two_shapely, m)

    save_map(single_shapely, two_shapely, three_shapely, dict)

    # state_level


