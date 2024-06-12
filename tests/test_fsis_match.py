import geopandas as gpd
from shapely.geometry import Point
from pipeline.fsis_match import fsis_match
from pipeline.constants import WGS84

RENAME_DICT = {
    # FSIS columns
    "establishment_name": "establishment_name_fsis",
    "duns_number": "duns_number_fsis",
    "street": "street_fsis",
    "city": "city_fsis",
    "state": "state_fsis",
    "zip": "zip_fsis",
    "activities": "activities_fsis",
    "dbas": "dbas_fsis",
    "size": "size_fsis",
    "latitude": "latitude_fsis",
    "longitude": "longitude_fsis",
    # NETS columns
    "DunsNumber": "duns_number_nets",
    "Company": "company_nets",
    "TradeName": "trade_name_nets",
    "Address": "address_nets",
    "City": "city_nets",
    "State": "state_nets",
    "HQDuns": "hq_duns_nets",
    "HQCompany": "hq_company_nets",
    "SalesHere": "sales_here_nets",
}


def test_fsis_match():
    # TODO: Should these be gdfs or dfs?
    # TODO: put these in a fixture so I can use them across tests
    gdf_fsis = gpd.GeoDataFrame(
        {
            "duns_number": ["123"],
            "establishment_name": "Chicken Little Chicken Factory",
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "activities": "slaughter",  # TODO...
            "dbas": "The Little Chicken Company",
            "size": "large",
            "latitude": 1,
            "longitude": 1,
            "geometry": [Point(1, 1)],  # TODO: ...
        }
    ).set_crs(WGS84)
    gdf_nets = gpd.GeoDataFrame(
        {
            "DunsNumber": ["123"],
            "Company": "Chicken Little Chicken Factory, Inc.",
            "Address": "123 Main Street",
            "City": "Springfield",
            "State": "IL",
            "HQDuns": "456",
            "HQCompany": "The Little Chicken Company",
            "geometry": [Point(1, 1)],  # TODO: ...
            "TradeName": "Chicken Little Chicken Factory",
            "SalesHere": 1000,
        }
    ).set_crs(WGS84)
    result, _, _ = fsis_match(gdf_fsis, gdf_nets)
    assert not result.empty
    assert "geometry" in result.columns
