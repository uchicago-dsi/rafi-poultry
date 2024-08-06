"""Filter barns from Microsoft's computer vision model based on various criteria."""

import argparse
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
FILTERS_CONFIG_FILEPATH = Path(__file__).resolve().parent / "config_geo_filters.yaml"
PIPELINE_CONFIG_FILEPATH = Path(__file__).resolve().parent / "config_pipeline.yaml"
CITIES_PATH = SHAPEFILE_DIR / "municipalities___states.geoparquet"


with Path.open(FILTERS_CONFIG_FILEPATH) as f:
    filters_config = yaml.safe_load(f)

with Path.open(PIPELINE_CONFIG_FILEPATH) as f:
    pipeline_config = yaml.safe_load(f)
    cities_by_state = pipeline_config["cities"]


# TODO: This is probably a util also...
def load_geography(
    filepath: str, states: gpd.GeoDataFrame = GDF_STATES, state: str = None
) -> gpd.GeoDataFrame:
    """Load geographic data from a file and optionally filter by state.

    Args:
        filepath: Path to the geographic file.
        states: GeoDataFrame of states.
        state: State to filter the geographic data.

    Returns:
        The loaded and optionally filtered geographic data.
    """
    file_extension = Path(filepath).suffix
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


def get_state_info(
    gdf: gpd.GeoDataFrame,
    valid_states: list = None,
    gdf_states: gpd.GeoDataFrame = GDF_STATES,
) -> gpd.GeoDataFrame:
    """Get state information for a GeoDataFrame.

    Args:
        gdf: Input GeoDataFrame.
        valid_states: List of valid state abbreviations.
        gdf_states: GeoDataFrame of states.

    Returns:
        GeoDataFrame with state information.
    """
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
    gdf: gpd.GeoDataFrame,
    gdf_exclude: gpd.GeoDataFrame,
    how: str = "inside",
    buffer: float = 0,
    tolerance: float = 0.1,
    filter_on_state: bool = True,
) -> gpd.GeoDataFrame:
    """Filter a GeoDataFrame based on membership in exclusion geometries.

    Args:
        gdf: Input GeoDataFrame.
        gdf_exclude: GeoDataFrame of exclusion geometries.
        how: Method of filtering ("inside" or "outside").
        buffer: Buffer distance for exclusion geometries.
        tolerance: Tolerance for geometry simplification.
        filter_on_state: Whether to filter based on state information.

    Returns:
        Filtered GeoDataFrame.
    """
    if gdf.index.duplicated().any():
        print("Warning: Duplicate indices detected in input GeoDataFrame")

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

    # Ensure unique indices
    if joined.index.duplicated().any():
        joined = joined.groupby(joined.index).first()

    # update original dataframe with newly excluded barns
    gdf.loc[joined.index, "exclude"] = joined["exclude"]

    return gdf


def filter_barns_handler(
    gdf_barns: gpd.GeoDataFrame,
    filters_config: list,
    data_dir: Path = SHAPEFILE_DIR,
    cities_by_state: dict = cities_by_state,
) -> gpd.GeoDataFrame:
    """Apply a series of filters to exclude barns based on various criteria.

    Args:
        gdf_barns: GeoDataFrame of barns.
        filters_config: List of filter configurations.
        data_dir: Directory containing shapefiles.
        cities_by_state: Dictionary of major cities by state to exclude.

    Returns:
        Filtered GeoDataFrame of barns.
    """
    # Exclude barns in major cities
    # Note: Do this separately from the filters in config since we need to aggregate the cities
    print("Excluding barns in major cities...")
    cities_all = gpd.read_parquet(CITIES_PATH)
    matches = []
    for state, cities in cities_by_state.items():
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
    gdf_barns = apply_filters(gdf_barns, filters_config, data_dir)

    print(f"There are {len(gdf_barns[gdf_barns.exclude == 0])} barns remaining")
    return gdf_barns


def apply_filters(
    gdf: gpd.GeoDataFrame, filters_config: list, shapefile_dir: Path = SHAPEFILE_DIR
) -> gpd.GeoDataFrame:
    """Apply a series of spatial filters to a GeoDataFrame.

    Args:
        gdf: Input GeoDataFrame.
        filters_config: List of filter configurations.
        shapefile_dir: Directory containing shapefiles.

    Returns:
        Filtered GeoDataFrame.
    """
    for config in filters_config:
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
    gdf_barns: gpd.GeoDataFrame,
    gdf_isochrones: gpd.GeoDataFrame,
    shapefile_dir: Path = SHAPEFILE_DIR,
    nearest_neighbor: int = 50,
    smoke_test: bool = False,
    filter_barns: bool = True,
) -> gpd.GeoDataFrame:
    """Filter barns based on various criteria and return the filtered GeoDataFrame.

    Args:
        gdf_barns: GeoDataFrame of barns.
        gdf_isochrones: GeoDataFrame of isochrones.
        shapefile_dir: Directory containing shapefiles.
        nearest_neighbor: Distance to check for nearest neighbor in meters.
        smoke_test: Flag to run in smoke test mode with a smaller sample size.
        filter_barns: Flag to apply geospatial filtering on barns.

    Returns:
        Filtered GeoDataFrame of barns.
    """
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
    gdf_barns["exclude"] = gdf_barns["exclude"].astype(
        int
    )  # Dashboard expects int dtype

    # Project to latitude and longitude
    gdf_barns = gdf_barns.to_crs(WGS84)

    # Join with plant access isochrones
    print("Checking integrator access...")
    gdf_barns["integrator_access"] = 0
    gdf_single_corp = gdf_isochrones[gdf_isochrones["corp_access"] == 1]
    gdf_two_corps = gdf_isochrones[gdf_isochrones["corp_access"] == 2]  #  noqa
    gdf_three_plus_corps = gdf_isochrones[gdf_isochrones["corp_access"] == 3]  #  noqa

    # Buffer to fix invalid geometries
    gdf_single_corp["geometry"] = gdf_single_corp.geometry.buffer(0)
    gdf_two_corps["geometry"] = gdf_two_corps.geometry.buffer(0)
    gdf_three_plus_corps["geometry"] = gdf_three_plus_corps.geometry.buffer(0)

    fsis_union = gpd.GeoDataFrame(
        geometry=[gdf_single_corp.geometry.unary_union], crs=gdf_barns.crs
    )

    # TODO: can prob do this as a function
    # Note: I think I'm preprocessing for the barn calculation here?
    gdf_barns = gpd.sjoin(gdf_barns, fsis_union, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notna(), "integrator_access"] = 1
    # TODO: is this the right dataframe here...
    gdf_barns["parent_corporation"] = gdf_barns.progress_apply(
        lambda row: (
            gdf_single_corp.loc[row["index_right"], "Parent Corporation"]
            if pd.notna(row["index_right"])
            else None
        ),
        axis=1,
    )
    # Note: Need to drop the index column created by the join for future joins
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(gdf_barns, gdf_two_corps, how="left", predicate="within")
    gdf_barns.loc[gdf_barns["index_right"].notna(), "integrator_access"] = 2
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    gdf_barns = gpd.sjoin(
        gdf_barns, gdf_three_plus_corps, how="left", predicate="within"
    )
    gdf_barns.loc[gdf_barns["index_right"].notna(), "integrator_access"] = 3
    gdf_barns = gdf_barns.drop("index_right", axis=1)

    # TODO: add a flag for excluding barns without integrator access
    gdf_barns = gdf_barns[gdf_barns["integrator_access"] != 0]

    # TODO: I think I should have this as a flag in the utils function
    # Get state membership for each barn
    print("Getting states for all barns...")
    gdf_barns = get_state_info(gdf_barns)

    # Choose the first barn in each group of duplicates
    # Note: This happens with joins on messy buffered geometries
    if gdf_barns.index.duplicated().any():
        original_crs = gdf_barns.crs
        gdf_barns = gdf_barns.groupby(gdf_barns.index).first()
        gdf_barns = gdf_barns.set_crs(original_crs)

    print(f"Barns before filtering on shapefiles: {len(gdf_barns)}")

    with Path.open(FILTERS_CONFIG_FILEPATH) as f:
        filters_config = yaml.safe_load(f)

    filters = filters_config["filters"]

    # Note: Option for skipping geospatial filtering on barns for faster runs
    if filter_barns:
        gdf_barns = filter_barns_handler(gdf_barns, filters, shapefile_dir)

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
