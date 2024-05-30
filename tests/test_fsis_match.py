import geopandas as gpd
from shapely.geometry import Point
from pipeline.fsis_match import fsis_match
from pipeline.constants import WGS84


def test_fsis_match():
    gdf_fsis = gpd.GeoDataFrame(
        {
            "duns_number": ["123"],
            "Company": "Chicken Little Chicken Factory",
            "geometry": [Point(1, 1)],
        }
    ).set_crs(WGS84)
    gdf_nets = gpd.GeoDataFrame(
        {
            "DunsNumber": ["123"],
            "Company": "Chicken Little Chicken Factory, Inc.",
            "geometry": [Point(1, 1)],
        }
    ).set_crs(WGS84)
    result, _, _ = fsis_match(gdf_fsis, gdf_nets)
    assert not result.empty
    assert "geometry" in result.columns
