
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


fsis_df = pd.read_csv("../data/clean/cleaned_fsis_processors.csv")
info_df = pd.read_csv("../data/clean/cleaned_infogroup_plants_all_time.csv")

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

four_plant_color = lambda x: {
    "fillColor": "#90ee90" # light green
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
isochrones = []
# create an empty dictionary to fill with unique parent companies 
dict = {}
plants_layer = folium.map.FeatureGroup(name="Large Poultry Plants")

def add_more_isochrones(df):
    df_map = make_geo_df(df)

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
        isochrones.append(chrone)

        # Can add the isochrones to the map, too, but this gets pretty cluttered with the other geospatial data
        # add driving radius isochrone to map layer
        # geojson = folium.GeoJson(row['Isochrone Cleaned'], style_function=empty_color)
        # geojson.add_to(driving_distance_layer)





m = folium.Map(location=[USA_LAT, USA_LNG],zoom_start=4)





