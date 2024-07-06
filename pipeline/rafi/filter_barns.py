import argparse
import os
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml
from tqdm import tqdm

from rafi.constants import (
    ALBERS_EQUAL_AREA,
    CLEAN_DIR,
    GDF_STATES,
    RAW_DIR,
    SHAPEFILE_DIR,
    WGS84,
)
from rafi.utils import save_file

tqdm.pandas()

# TODO: move to config or constants
CONFIG_FILENAME = Path(__file__).resolve().parent / "geospatial_filter_config.yaml"
CITIES_PATH = SHAPEFILE_DIR / "municipalities___states.geoparquet"
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


# TODO: This is probably a util also...
def load_geography(filepath, states=GDF_STATES, state=None):
    _, file_extension = os.path.splitext(filepath)
    if file_extension.lower() == ".parquet":
        gdf = gpd.read_parquet(filepath)
    else:
        gdf = gpd.read_file(filepath)
    if state is not None:
        gdf = gdf.to_crs(GDF_STATES.crs)
        gdf = gpd.overlay(
            gdf,
            states[states["NAME"] == state],
            how="intersection",
            keep_geom_type=False,
        )
    return gdf


def get_state_info(gdf, valid_states=None, gdf_states=GDF_STATES):
    if valid_states is not None:
        gdf_states = gdf_states[gdf_states["ABBREV"].isin(valid_states)]
    gdf_states = gdf_states.to_crs(gdf.crs)
    gdf_with_state = gpd.sjoin(gdf, gdf_states, how="left", predicate="intersects")
    gdf_with_state = gdf_with_state[list(gdf.columns) + ["ABBREV"]]

    # TODO: fix this warning, the commented fix doesn't work
    # Probably need to drop columns before doing the merge for the larger geographies
    # /usr/local/lib/python3.10/dist-packages/geopandas/geodataframe.py:1569: FutureWarning: Passing 'suffixes' which cause duplicate columns {'state_left'} in the result is deprecated and will raise a MergeError in a future version.
    # result = DataFrame.merge(self, *args, **kwargs)
    # Note: Avoid column conflicts by renaming the joined columns
    # if (
    #     "state_left" in gdf_with_state.columns
    #     or "state_right" in gdf_with_state.columns
    # ):
    #     gdf_with_state = gdf_with_state.rename(
    #         columns={"state_left": "state_gdf", "state_right": "state_states"}
    #     )
    gdf_with_state = gdf_with_state.rename(columns={"ABBREV": "state"})
    return gdf_with_state


def filter_on_membership(
    gdf, gdf_exclude, how="inside", buffer=0, tolerance=0.1, filter_on_state=True
):
    # Simplify geometries to speed up processing
    gdf_exclude["geometry"] = gdf_exclude["geometry"].simplify(
        tolerance, preserve_topology=True
    )

    # Note: This step can be slow, but it's necessary to prevent the process from
    # being killed for large/detailed geometries
    if filter_on_state:
        valid_states = gdf["state"].unique()
        print("Getting state info for exclusion geographies...")
        gdf_exclude = get_state_info(gdf_exclude, valid_states=valid_states)
        gdf_exclude = gdf_exclude[gdf_exclude["state"].isin(valid_states)]

    # TODO: Should I use ALBERS_EQUAL_AREA here?
    if buffer != 0:
        gdf_exclude = gdf_exclude.to_crs(
            epsg=5070
        )  # convert to CRS where the buffer unit is in meters
        gdf_exclude["geometry"] = gdf_exclude["geometry"].buffer(buffer)

    gdf_exclude = gdf_exclude.to_crs(gdf.crs)

    # Exclude previously excluded barns to speed up processing
    joined = gpd.sjoin(
        gdf[gdf["exclude"] != 1], gdf_exclude, how="left", predicate="within"
    )

    if how == "inside":
        joined["exclude"] = joined.progress_apply(
            lambda row: (1 if not pd.isna(row["index_right"]) else row["exclude"]),
            axis=1,
        )
    elif how == "outside":
        joined["exclude"] = joined.progress_apply(
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


def filter_barns_handler(gdf_barns, filter_configs, data_dir=SHAPEFILE_DIR):
    # Exclude barns in major cities
    # Note: Do this separately from the filters in config since we need to aggregate the cities
    print("Excluding barns in major cities...")
    cities_all = gpd.read_parquet(CITIES_PATH)
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

    # Apply all other filters from config
    gdf_barns = apply_filters(gdf_barns, filter_configs, data_dir)

    print(f"There are {len(gdf_barns[gdf_barns.exclude == 0])} barns remaining")
    return gdf_barns


def apply_filters(gdf, filter_configs, shapefile_dir=SHAPEFILE_DIR):
    for config in filter_configs:
        description = config["description"]
        exclude_gdf_path = shapefile_dir / config["filename"]
        buffer = config.get("buffer", 0)
        how = config.get("how", "inside")
        filter_on_state = config.get("filter_on_state", False)

        print(f"Filtering barns in/on {description}...")
        print(f"Reading file {exclude_gdf_path}")
        if exclude_gdf_path.suffix == ".gdb":
            layer = config.get("layer")
            exclude_gdf = gpd.read_file(exclude_gdf_path, layer=layer)
        else:
            exclude_gdf = gpd.read_file(exclude_gdf_path)

        print("Applying filter...")
        previously_excluded = len(gdf[gdf.exclude == 1])
        gdf = filter_on_membership(
            gdf, exclude_gdf, buffer=buffer, filter_on_state=filter_on_state, how=how
        )
        excluded_count = len(gdf[gdf.exclude == 1]) - previously_excluded
        print(f"Excluded {excluded_count} barns in/on {description}")

    return gdf


def filter_barns(
    gdf_barns,
    gdf_isochrones,
    shapefile_dir=SHAPEFILE_DIR,
    nearest_neighbor=50,
    smoke_test=False,
    filter_barns=True,
):
    if smoke_test:
        n = 10000
        gdf_barns = gdf_barns.sample(n=n)
        print(f"Running in smoke test mode with {n} samples.")
    else:
        print(f"Running with {len(gdf_barns)} barns.")

    # Project to equal area projection and get centroid for each barn
    gdf_barns = gdf_barns.to_crs(ALBERS_EQUAL_AREA)
    gdf_barns["geometry"] = gdf_barns["geometry"].centroid

    # Exclude barns with no nearest neighbor (barns are almost always in at least groups of two)
    # TODO: Make this prettier?
    def nearest_neighbor(geom, gdf, distance=nearest_neighbor):
        nearest_idx = gdf.sindex.nearest(geom, exclusive=True, max_distance=distance)
        return nearest_idx.size == 0

    print("Excluding barns without a nearest neighbor...")
    gdf_barns["exclude"] = gdf_barns["geometry"].progress_apply(
        lambda geom: nearest_neighbor(geom, gdf_barns, distance=50)
    )
    # Drop the barns that don't have a nearest neighbor here to save computation time on other steps
    gdf_barns = gdf_barns[~gdf_barns["exclude"]]
    gdf_barns["exclude"] = gdf_barns["exclude"].astype(int)  # Dashboard expects int

    # Project to latitude and longitude
    gdf_barns = gdf_barns.to_crs(WGS84)

    # Join with plant access isochrones
    print("Checking integrator access...")
    gdf_barns["integrator_access"] = 0
    gdf_single_corp = gdf_isochrones[gdf_isochrones["corp_access"] == 1]
    gdf_two_corps = gdf_isochrones[gdf_isochrones["corp_access"] == 2]
    gdf_three_plus_corps = gdf_isochrones[gdf_isochrones["corp_access"] == 3]

    fsis_union = gpd.GeoDataFrame(
        geometry=[gdf_single_corp.geometry.unary_union], crs=gdf_barns.crs
    )

    # TODO: can prob do this as a function
    # Note: I think I'm preprocessing for the barn calculation here?
    gdf_barns = gpd.sjoin(gdf_barns, fsis_union, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 1
    # TODO: is this the right dataframe here...
    gdf_barns["parent_corporation"] = gdf_barns.progress_apply(
        lambda row: (
            gdf_single_corp.loc[row["index_right"], "Parent Corporation"]
            if pd.notnull(row["index_right"])
            else None
        ),
        axis=1,
    )
    # Note: Need to drop the index column created by the join for future joins
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(gdf_barns, gdf_two_corps, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 2
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(
        gdf_barns, gdf_three_plus_corps, how="left", predicate="within"
    )
    gdf_barns.loc[gdf_barns["index_right"].notnull(), "integrator_access"] = 3
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    # TODO: add a flag for excluding barns without integrator access
    gdf_barns = gdf_barns[gdf_barns["integrator_access"] != 0]

    # TODO: I think I should have this as a flag in the utils function
    # Get state membership for each barn
    print("Getting states for all barns...")
    gdf_barns = get_state_info(gdf_barns)

    print(f"Barns before filtering on shapefiles: {len(gdf_barns)}")

    with open(CONFIG_FILENAME) as f:
        filter_configs = yaml.safe_load(f)

    filter_configs = filter_configs["filters"]

    # Note: Option for skipping geospatial filtering on barns for faster runs
    if filter_barns:
        gdf_barns = filter_barns_handler(gdf_barns, filter_configs, shapefile_dir)

    # TODO: Maybe put this in a config
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
    RUN_DIR = CLEAN_DIR / f"barns_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    Path.mkdir(RUN_DIR, parents=True, exist_ok=True)

    # TODO: Add to config
    BARNS_FILENAME = "full-usa-3-13-2021_filtered_deduplicated.gpkg"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke_test", action="store_true", help="Run in smoke test mode"
    )
    args = parser.parse_args()

    SMOKE_TEST = args.smoke_test

    # TODO: Maybe create a read function for this
    gdf_barns = gpd.read_file(RAW_DIR / BARNS_FILENAME)
    # TODO: Filepaths...
    gdf_isochrones = gpd.read_file(CLEAN_DIR / "_clean_run" / "isochrones.geojson")

    gdf_barns = filter_barns(gdf_barns, gdf_isochrones, smoke_test=SMOKE_TEST)

    save_file(gdf_barns, RUN_DIR / "barns.geojson", gzip_file=True)
