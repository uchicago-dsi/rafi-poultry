"""Calculate captured areas for FSIS plants."""

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from tqdm import tqdm

from rafi.constants import CLEAN_DIR, GDF_STATES, STATE2ABBREV, WGS84
from rafi.utils import save_file

tqdm.pandas()


def calculate_captured_areas(
    gdf_fsis: gpd.GeoDataFrame,
    corp_col: str = "Parent Corporation",
    chrone_col: str = "isochrone",
    access_col: str = "corp_access",
    simplify_tol: float = 0.01,
    multi_corp_threshold: int = 3,
) -> gpd.GeoDataFrame:
    """Calculates captured areas for each parent corporation and determines areas with access to one, two, or three or more corporations

    Args:
        gdf_fsis: GeoDataFrame of FSIS plants.
        corp_col: Column name for the parent corporation.
        chrone_col: Column name for the isochrone geometry.
        access_col: Column name for the corporation access level.
        simplify_tol: Tolerance for simplifying geometries.
        multi_corp_threshold: The minimum number of corporations to count as multi corp access.


    Returns:
        GeoDataFrame with captured areas for each parent corporation.
    """
    gdf_fsis = gdf_fsis.set_geometry(chrone_col).set_crs(WGS84)

    # Dissolve by parent corporation to calculate access on a corporation (not plant) level
    gdf_single_corp_dissolved = gdf_fsis.dissolve(by=corp_col).reset_index()[
        [corp_col, chrone_col]
    ]

    # Self join to find intersections in corporate access
    intersections = gpd.sjoin(
        gdf_single_corp_dissolved,
        gdf_single_corp_dissolved,
        how="inner",
        predicate="intersects",
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
            lambda row: gdf_single_corp_dissolved.loc[
                row.name, chrone_col
            ].intersection(
                gdf_single_corp_dissolved.loc[row["index_right"], chrone_col]
            ),
            axis=1,
        )
    )
    intersections_filtered = intersections_filtered.set_geometry(
        "intersection_geometry"
    ).set_crs(WGS84)
    intersections_filtered = intersections_filtered.rename(
        columns={
            f"{corp_col}_left": f"{corp_col} #1",
            f"{corp_col}_right": f"{corp_col} #2",
        }
    )
    intersections_filtered = intersections_filtered[
        [f"{corp_col} #1", f"{corp_col} #2", "intersection_geometry"]
    ]
    # This is still using the index for the corporations - reset so each intersection has a unique index
    intersections_filtered = intersections_filtered.reset_index(drop=True)

    print("Calculating single corporation access...")
    multi_corp_access_area = intersections_filtered["intersection_geometry"].unary_union
    # Take the difference between each corporate area and the area with access to more than one corp
    # This is the area that has access to only one corporation
    # Note: Make a copy so we can update this and save it in the isochrones
    gdf_single_corp = gdf_single_corp_dissolved.copy()
    gdf_single_corp["Captured Area"] = gdf_single_corp[chrone_col].progress_apply(
        lambda x: x.difference(multi_corp_access_area)
    )
    gdf_single_corp = gdf_single_corp.set_geometry("Captured Area")

    gdf_single_corp = gpd.overlay(
        GDF_STATES, gdf_single_corp, how="intersection", keep_geom_type=False
    )
    gdf_single_corp[access_col] = 1
    gdf_single_corp = gdf_single_corp.drop("isochrone", axis=1)

    # To calculate 3+ corporation access, we join intersections with themselves
    # Then we filter for intersections that intersect with at least three corporations
    # and calculate the actual overlapping area of those intersections

    # Note: These are multipolygons so need to explode the dataframe
    intersections_exploded = intersections_filtered.explode(index_parts=True)
    # Note: sjoin only keeps one geometry so we need to reassign it to retain after the join
    intersections_exploded["geometry_saved"] = intersections_exploded[
        "intersection_geometry"
    ]
    multi_corp_intersections = gpd.sjoin(
        intersections_exploded,
        intersections_exploded,
        how="inner",
        predicate="intersects",
    )

    # Find intersections that intersect with at least three corporations
    corp_columns = [
        "Parent Corporation #1_left",
        "Parent Corporation #2_left",
        "Parent Corporation #1_right",
        "Parent Corporation #2_right",
    ]

    def count_unique_corporations(row: pd.Series) -> int:
        """Counts the number of unique corporations in a row.

        Args:
            row: The row of the DataFrame to process.

        Returns:
            The number of unique corporations.
        """
        corporations = row[corp_columns].dropna().unique()
        return len(corporations)

    print("Calculating multi corporation access...")
    multi_corp_intersections["unique_corp_count"] = (
        multi_corp_intersections.progress_apply(count_unique_corporations, axis=1)
    )
    multi_corp_intersections = multi_corp_intersections[
        multi_corp_intersections["unique_corp_count"] >= multi_corp_threshold
    ]
    print("Calculating 3+ corporation access...")
    multi_corp_intersections["3+ Area"] = multi_corp_intersections[
        "geometry_saved_right"
    ].intersection(multi_corp_intersections["geometry_saved_left"])
    three_plus_corp_access_area = multi_corp_intersections["3+ Area"].unary_union

    # Two corp access area is the area with multi corp access minus the area with 3+ corp access
    print("Calculating two corporation access...")
    multi_corp_access_area = intersections_filtered["intersection_geometry"].unary_union
    two_corp_access_area = multi_corp_access_area.difference(
        three_plus_corp_access_area
    )

    gdf_two_corps = gpd.GeoDataFrame(geometry=[two_corp_access_area], crs=WGS84)
    gdf_two_corps = gpd.overlay(GDF_STATES, gdf_two_corps, keep_geom_type=False)
    gdf_two_corps[access_col] = 2

    gdf_three_plus_corps = gpd.GeoDataFrame(
        geometry=[three_plus_corp_access_area], crs=WGS84
    )
    gdf_three_plus_corps = gpd.overlay(
        GDF_STATES, gdf_three_plus_corps, keep_geom_type=False
    )
    gdf_three_plus_corps[access_col] = 3

    isochrones = gpd.GeoDataFrame(
        pd.concat(
            [gdf_single_corp, gdf_two_corps, gdf_three_plus_corps], ignore_index=True
        )
    )

    isochrones["state"] = isochrones["state"].map(STATE2ABBREV)
    isochrones["geometry"] = isochrones.simplify(simplify_tol)

    return isochrones


if __name__ == "__main__":
    RUN_DIR = (
        CLEAN_DIR / f"captured_areas_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    Path.mkdir(RUN_DIR, exist_ok=True, parents=True)

    # TODO: is there a better way to load clean versions of the files? Specify in config?
    GDF_FSIS_PATH = CLEAN_DIR / "_clean_run" / "plants_with_isochrones.geojson"
    gdf_fsis = gpd.read_file(GDF_FSIS_PATH)

    # Note: Since we are loading raw GeoJSON, rename "geometry" to match the expected from of GDF passed to function
    gdf_fsis["isochrone"] = gdf_fsis["geometry"]
    isochrones = calculate_captured_areas(gdf_fsis)

    print(f"Saving to {RUN_DIR}/isochrones.geojson")
    save_file(isochrones, RUN_DIR / "isochrones.geojson", gzip_file=True)
