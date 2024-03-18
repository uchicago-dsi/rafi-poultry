import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point

FILENAME = "../data/raw/nc_only_unfiltered.geojson"
# FILENAME = "../data/raw/chesapeake-bay-3-18-2021_filtered.gpkg"
STATES_FILE = "../data/shapefiles/cb_2022_us_state_500k/cb_2022_us_state_500k.shp"

CITIES = {
    "North Carolina": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville", "Cary", "Wilmington", "High Point", "Concord"]
}

SMOKE_TEST = False
PROJECTION = 5070 # Albers Equal Area - suitable for continental USA

def filter_on_road_distance(gdf):
    # TODO: This should already be filtered but it filters only on 0 maybe? Look into this further
    pass

def get_state(gdf, states_fp=STATES_FILE):
    states = gpd.read_file(states_fp)
    states = states.to_crs(gdf.crs)
    gdf_with_state = gpd.sjoin(gdf, states, how="left", predicate="intersects")
    gdf_with_state = gdf_with_state[[column for column in gdf.columns] + ['NAME']]
    gdf_with_state = gdf_with_state.rename(columns={'NAME': 'state_name'})
    return gdf_with_state

def filter_on_membership(gdf, gdf_exclude, buffer=0):  
    if buffer != 0:
        gdf_exclude = gdf_exclude.to_crs(epsg=32633) # convert to CRS where the buffer unit is in meters
        gdf_exclude['geometry'] = gdf_exclude['geometry'].buffer(buffer)

    gdf_exclude = gdf_exclude.to_crs(gdf.crs)
    
    # combined_geometry = gdf_exclude.geometry.unary_union
    # gdf['is_within'] = gdf.apply(lambda row: row.geometry.within(combined_geometry), axis=1)
    # gdf_filtered = gdf[~gdf['is_within']]
    # gdf_filtered = gdf_filtered.drop(columns=["is_within"])
    
    joined = gpd.sjoin(gdf, gdf_exclude, how='left', predicate='within')
    gdf_filtered = joined[joined['index_right'].isna()]
    gdf_filtered = gdf_filtered.drop(columns=['index_right'])
    
    return gdf_filtered

if __name__ == "__main__":
    gdf = gpd.read_file(FILENAME)
    gdf = gdf[:1000] if SMOKE_TEST else gdf
    gdf = gdf.to_crs(epsg=PROJECTION)
    gdf['geometry'] = gdf['geometry'].centroid

    # Get state membership for each barn
    print("Getting states for all barns...")
    gdf = get_state(gdf, "../data/shapefiles/cb_2022_us_state_500k/cb_2022_us_state_500k.shp")
    length = len(gdf)
    print(f"len(gdf) before filtering: {length}")

    # Exclude barns on the coastline
    # Source: https://catalog.data.gov/dataset/tiger-line-shapefile-2019-nation-u-s-coastline-national-shapefile
    print("Excluding barns on the coastline...")
    gdf = filter_on_membership(gdf, gpd.read_file("../data/shapefiles/tl_2019_us_coastline/tl_2019_us_coastline.shp"), buffer=150)
    print(f"Excluded {length - len(gdf)} barns on the coastline")
    length = len(gdf)

    # Exclude barns in major cities
    print("Excluding barns in major cities...")
    # TODO: Should maybe set this up as a function and clean it up
    cities_all = gpd.read_parquet("../data/shapefiles/municipalities___states.geoparquet")
    matches = []
    for state, cities in CITIES.items():
        for city in cities:
            match = cities_all[cities_all['name'].str.contains(city, case=False, na=False) & cities_all['name'].str.contains(state, case=False, na=False)]
            matches.append(match)
    cities_filtered = pd.concat(matches, ignore_index=True).drop_duplicates()
    cities_filtered = gpd.GeoDataFrame(cities_filtered, geometry='geometry')

    # cities_filtered = cities_filtered.append(match, ignore_index=True)
    # gpd.GeoDataFrame(columns=cities_all.columns)
    gdf = filter_on_membership(gdf, cities_filtered)
    print(f"Excluded {length - len(gdf)} barns in major cities")
    length = len(gdf)

    # Exclude barns in airports
    # Source: https://geodata.bts.gov/datasets/c3ca6a6cdcb242698f1eadb7681f6162_0/explore
    print("Excluding barns in airports...")
    gdf = filter_on_membership(gdf, gpd.read_file("../data/shapefiles/Aviation_Facilities_-8733969321550682504/Aviation_Facilities.shp"))
    print(f"Excluded {length - len(gdf)} barns in airports")
    length = len(gdf)
    
    # # TODO: Could maybe filter this on state to speed this step up
    # # Exclude barns in bodies of water
    # # Source: https://www.arcgis.com/home/item.html?id=48c77cbde9a0470fb371f8c8a8a7421a
    # print("Excluding barns in bodies of water...")
    # gdf = filter_on_membership(gdf, gpd.read_file("../data/shapefiles/USA_Detailed_Water_Bodies.geojson"))
    # print(f"Excluded {length - len(gdf)} barns in bodies of water")
    # length = len(gdf)
    