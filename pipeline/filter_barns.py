import argparse
import os
import pandas as pd
import geopandas as gpd
import gzip
import shutil
from pathlib import Path

FILENAME = "../data/raw/full-usa-3-13-2021_filtered_deduplicated.gpkg"

STATES_FILE = "../data/shapefiles/cb_2022_us_state_500k/cb_2022_us_state_500k.shp"
STATES = gpd.read_file(STATES_FILE)

# TODO:...
current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/"
DATA_DIR_RAW = DATA_DIR / "raw/"
DATA_DIR_CLEAN = DATA_DIR / "clean/"

# Switch to state abbreviations so command line arguments work
state2abbrev = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
    "American Samoa": "AS",
    "Guam": "GU",
    "Northern Mariana Islands": "MP",
    "Puerto Rico": "PR",
    "United States Minor Outlying Islands": "UM",
    "U.S. Virgin Islands": "VI",
}
STATES["ABBREV"] = STATES["NAME"].map(state2abbrev)

CITIES = {
    "North Carolina": [
        "Charlotte",
        "Raleigh",
        "Greensboro",
        "Durham",
        "Winston-Salem",
        "Fayetteville",
        "Cary",
        "Wilmington",
        "High Point",
        "Concord",
    ],
    "Mississippi": [
        "Jackson",
        "Gulfport",
        "Southaven",
        "Biloxi",
        "Hattiesburg",
    ],
    "Arkansas": [
        "Little Rock",
        "Fayetteville",
        "Fort Smith",
        "Springdale",
        "Jonesboro",
        "Rogers",
        "Conway",
        "North Little Rock",
        "Bentonville",
        "Pine Bluff",
    ],
}

# TODO: Ok...what?
SMOKE_TEST = False
PROJECTION = 4326


def load_geography(filepath, state=None):
    _, file_extension = os.path.splitext(filepath)
    if file_extension.lower() == ".parquet":
        gdf = gpd.read_parquet(filepath)
    else:
        gdf = gpd.read_file(filepath)
    if state is not None:
        gdf = gdf.to_crs(STATES.crs)
        gdf = gpd.overlay(
            gdf,
            STATES[STATES["NAME"] == state],
            how="intersection",
            keep_geom_type=False,
        )
    return gdf


def filter_on_road_distance(gdf):
    # TODO: This should already be filtered but it filters only on 0 maybe? Look into this further
    pass


def get_state_info(gdf, states=STATES):
    states = states.to_crs(gdf.crs)
    gdf_with_state = gpd.sjoin(gdf, states, how="left", predicate="intersects")
    gdf_with_state = gdf_with_state[[column for column in gdf.columns] + ["ABBREV"]]
    gdf_with_state = gdf_with_state.rename(columns={"ABBREV": "state"})
    return gdf_with_state


def filter_on_membership(gdf, gdf_exclude, how="inside", buffer=0, smoke_test=False):
    if buffer != 0:
        gdf_exclude = gdf_exclude.to_crs(
            epsg=5070
        )  # convert to CRS where the buffer unit is in meters
        gdf_exclude["geometry"] = gdf_exclude["geometry"].buffer(buffer)

    gdf_exclude = gdf_exclude.to_crs(gdf.crs)

    # Simplify geometries if smoke_test is passed
    if smoke_test:
        tolerance = 0.1
        gdf_exclude["geometry"] = gdf_exclude["geometry"].simplify(
            tolerance, preserve_topology=True
        )

    # Exclude previously excluded barns to speed up processing
    joined = gpd.sjoin(
        gdf[gdf["exclude"] != 1], gdf_exclude, how="left", predicate="within"
    )

    if how == "inside":
        joined["exclude"] = joined.apply(
            lambda row: (1 if not pd.isna(row["index_right"]) else row["exclude"]),
            axis=1,
        )
    elif how == "outside":
        joined["exclude"] = joined.apply(
            lambda row: (
                1
                if pd.isna(row["index_right"]) and row["exclude"] == 0
                else row["exclude"]
            ),
            axis=1,
        )

    joined = joined.drop(columns=["index_right"])

    # update original dataframe with newly excluded barns
    gdf.loc[joined.index, "exclude"] = joined["exclude"]

    return gdf


# TODO: These function names need some work
def filter_barns_handler(gdf_barns, smoke_test=False):
    # Exclude barns in major cities
    print("Excluding barns in major cities...")
    # TODO: Should maybe set this up as a function and clean it up
    cities_all = gpd.read_parquet(
        "../data/shapefiles/municipalities___states.geoparquet"
    )
    matches = []
    for state, cities in CITIES.items():
        for city in cities:
            match = cities_all[
                cities_all["name"].str.contains(city, case=False, na=False)
                & cities_all["name"].str.contains(state, case=False, na=False)
            ]
            matches.append(match)
    cities_filtered = pd.concat(matches, ignore_index=True).drop_duplicates()
    cities_filtered = gpd.GeoDataFrame(cities_filtered, geometry="geometry")
    previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    gdf_barns = filter_on_membership(gdf_barns, cities_filtered)
    print(
        f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in major cities"
    )

    # TODO: This seems to not be working, look into this
    # Exclude barns in airports
    # Source: https://geodata.bts.gov/datasets/c3ca6a6cdcb242698f1eadb7681f6162_0/explore
    print("Excluding barns in airports...")
    previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    gdf_barns = filter_on_membership(
        gdf_barns,
        gpd.read_file(
            "../data/shapefiles/Aviation_Facilities_-8733969321550682504/Aviation_Facilities.shp",
            buffer=400,
        ),
        smoke_test=smoke_test,
    )
    print(
        f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in airports"
    )

    # Exclude barns in parks
    # Source: https://www.arcgis.com/home/item.html?id=578968f975774d3fab79fe56c8c90941
    print("Excluding barns in parks...")
    parks_gdb_path = "../data/shapefiles/USA_Parks/v10/park_dtl.gdb"
    layer_name = "park_dtl"
    parks_gdf = gpd.read_file(parks_gdb_path, layer=layer_name)
    previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    gdf_barns = filter_on_membership(
        gdf_barns,
        parks_gdf,
    )
    print(
        f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in parks"
    )

    # Exclude barns on the coastline
    # Source: https://catalog.data.gov/dataset/tiger-line-shapefile-2019-nation-u-s-coastline-national-shapefile
    print("Excluding barns on the coastline...")
    previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    gdf_barns = filter_on_membership(
        gdf_barns,
        gpd.read_file(
            "../data/shapefiles/tl_2019_us_coastline/tl_2019_us_coastline.shp"
        ),
        buffer=1000,
        smoke_test=smoke_test,
    )
    print(
        f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns on the coastline"
    )

    # TODO: Could maybe filter this on state to speed this step up
    # Exclude barns in bodies of water
    # Source: https://www.arcgis.com/home/item.html?id=48c77cbde9a0470fb371f8c8a8a7421a
    print("Excluding barns in bodies of water...")
    previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    gdf_barns = filter_on_membership(
        gdf_barns,
        gpd.read_file("../data/shapefiles/USA_Detailed_Water_Bodies.geojson"),
        smoke_test=smoke_test,
    )
    print(
        f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in bodies of water"
    )

    # Note: This will not match the final barn count since we only count barns in the capture areas
    print(f"There are {len(gdf_barns[gdf_barns.exclude == 0])} barns remaining")

    return gdf_barns


# TODO: Handle filepaths, etc. correctly
# TODO: Set an argument for filtering on barns that intersect with the capture areas
def filter_barns(gdf_barns, smoke_test=SMOKE_TEST, filter_barns=True):
    if SMOKE_TEST:
        n = 10000
        gdf_barns = gdf_barns.sample(n=n)
        print(f"Running in smoke test mode with {n} samples.")
    else:
        print(f"Running with {len(gdf_barns)} barns.")

    # Project to equal area projection and get centroid for each barn
    gdf_barns = gdf_barns.to_crs(epsg=2163)
    gdf_barns["geometry"] = gdf_barns["geometry"].centroid

    # Project to latitude and longitude
    gdf_barns = gdf_barns.to_crs(epsg=PROJECTION)

    # Initialize the "exclude" column
    gdf_barns["exclude"] = 0
    gdf_barns["integrator_access"] = 0

    # Join with plant access isochrones
    print("Checking integrator access...")

    # TODO: handle filepaths
    gdf_single_corp = gpd.read_file(
        DATA_DIR_CLEAN
        / "captured_areas_2024-05-22_17-35-03"
        / "single_corp_access.geojson"
    )
    gdf_two_corps = gpd.read_file(
        DATA_DIR_CLEAN
        / "captured_areas_2024-05-22_17-35-03"
        / "two_corp_access.geojson"
    )
    gdf_three_plus_corps = gpd.read_file(
        DATA_DIR_CLEAN
        / "captured_areas_2024-05-22_17-35-03"
        / "three_plus_corp_access.geojson"
    )

    fsis_union = gpd.GeoDataFrame(
        geometry=[gdf_single_corp.geometry.unary_union], crs=gdf_barns.crs
    )

    # TODO: can prob do this as a function
    gdf_barns = gpd.sjoin(gdf_barns, fsis_union, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 1
    # TODO: is this the right dataframe here...
    gdf_barns["parent_corporation"] = gdf_barns.apply(
        lambda row: (
            gdf_single_corp.loc[row["index_right"], "Parent Corporation"]
            if pd.notnull(row["index_right"])
            else None
        ),
        axis=1,
    )  # Note: need to do this for future joins
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(gdf_barns, gdf_two_corps, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 2
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(
        gdf_barns, gdf_three_plus_corps, how="left", predicate="within"
    )
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 3
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    # TODO: add a flag for this
    gdf_barns = gdf_barns[gdf_barns["integrator_access"] != 0]

    # Get state membership for each barn
    print("Getting states for all barns...")
    gdf_barns = get_state_info(gdf_barns)

    print(f"Barns before filtering: {len(gdf_barns)}")

    if filter_barns:
        gdf_barns = filter_barns_handler(gdf_barns, smoke_test=smoke_test)

    # # Exclude barns in major cities
    # print("Excluding barns in major cities...")
    # # TODO: Should maybe set this up as a function and clean it up
    # cities_all = gpd.read_parquet(
    #     "../data/shapefiles/municipalities___states.geoparquet"
    # )
    # matches = []
    # for state, cities in CITIES.items():
    #     for city in cities:
    #         match = cities_all[
    #             cities_all["name"].str.contains(city, case=False, na=False)
    #             & cities_all["name"].str.contains(state, case=False, na=False)
    #         ]
    #         matches.append(match)
    # cities_filtered = pd.concat(matches, ignore_index=True).drop_duplicates()
    # cities_filtered = gpd.GeoDataFrame(cities_filtered, geometry="geometry")
    # previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    # gdf_barns = filter_on_membership(gdf_barns, cities_filtered)
    # print(
    #     f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in major cities"
    # )

    # # TODO: This seems to not be working, look into this
    # # Exclude barns in airports
    # # Source: https://geodata.bts.gov/datasets/c3ca6a6cdcb242698f1eadb7681f6162_0/explore
    # print("Excluding barns in airports...")
    # previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    # gdf_barns = filter_on_membership(
    #     gdf_barns,
    #     gpd.read_file(
    #         "../data/shapefiles/Aviation_Facilities_-8733969321550682504/Aviation_Facilities.shp",
    #         buffer=400,
    #     ),
    #     smoke_test=smoke_test,
    # )
    # print(
    #     f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in airports"
    # )

    # # Exclude barns in parks
    # # Source: https://www.arcgis.com/home/item.html?id=578968f975774d3fab79fe56c8c90941
    # print("Excluding barns in parks...")
    # parks_gdb_path = "../data/shapefiles/USA_Parks/v10/park_dtl.gdb"
    # layer_name = "park_dtl"
    # parks_gdf = gpd.read_file(parks_gdb_path, layer=layer_name)
    # previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    # gdf_barns = filter_on_membership(
    #     gdf_barns,
    #     parks_gdf,
    # )
    # print(
    #     f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in parks"
    # )

    # # Exclude barns on the coastline
    # # Source: https://catalog.data.gov/dataset/tiger-line-shapefile-2019-nation-u-s-coastline-national-shapefile
    # print("Excluding barns on the coastline...")
    # previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    # gdf_barns = filter_on_membership(
    #     gdf_barns,
    #     gpd.read_file(
    #         "../data/shapefiles/tl_2019_us_coastline/tl_2019_us_coastline.shp"
    #     ),
    #     buffer=1000,
    #     smoke_test=smoke_test,
    # )
    # print(
    #     f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns on the coastline"
    # )

    # # TODO: Could maybe filter this on state to speed this step up
    # # Exclude barns in bodies of water
    # # Source: https://www.arcgis.com/home/item.html?id=48c77cbde9a0470fb371f8c8a8a7421a
    # print("Excluding barns in bodies of water...")
    # previously_excluded = len(gdf_barns[gdf_barns.exclude == 1])
    # gdf_barns = filter_on_membership(
    #     gdf_barns,
    #     gpd.read_file("../data/shapefiles/USA_Detailed_Water_Bodies.geojson"),
    #     smoke_test=smoke_test,
    # )
    # print(
    #     f"Excluded {len(gdf_barns[gdf_barns.exclude == 1]) - previously_excluded} barns in bodies of water"
    # )

    # # Note: This will not match the final barn count since we only count barns in the capture areas
    # print(f"There are {len(gdf_barns[gdf_barns.exclude == 0])} barns remaining")

    # TODO: There's a problem somewhere where this stuff is named inconsistently
    # Fix this in the rest of the pipeline
    gdf_barns = gdf_barns.rename(columns={"state_left": "state"})
    # TODO: "company" is missing from the full state final output from the isochrone pipeline
    # OUTPUT_COLS = ["state", "company", "plant_access", "geometry", "exclude"]
    OUTPUT_COLS = [
        "state",
        "parent_corporation",
        "integrator_access",
        "geometry",
        "exclude",
    ]
    gdf_barns = gdf_barns[OUTPUT_COLS]
    gdf_barns = gdf_barns.set_geometry("geometry")

    return gdf_barns


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke_test", action="store_true", help="Run in smoke test mode"
    )
    args = parser.parse_args()

    SMOKE_TEST = args.smoke_test

    # TODO: what do I want to do here...
    filename = "../data/clean/filtered_barns.geojson"

    # if args.smoke_test:
    #     filename += "_smoke_test"

    # TODO: ...
    gdf_barns = gpd.read_file(FILENAME)

    # TODO: this also doesn't work...need to load the three dataframes with corp access
    gdf_fsis = gpd.read_file(
        DATA_DIR_CLEAN
        / "fsis_isochrones_2024-05-22_16-49-51"
        / "plants_with_isochrones.geojson"
    )

    gdf_barns = filter_barns(gdf_barns, smoke_test=SMOKE_TEST)

    gdf_barns.to_file(f"{filename}.geojson", driver="GeoJSON")
    print(f"Complete! Saved to {filename}.geojson")

    # TODO: what is this duplicate file error I'm getting?
    # gzip file for web
    print("Zipping file...")
    with open(filename, "rb") as f_in:
        with gzip.open(filename + ".gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
