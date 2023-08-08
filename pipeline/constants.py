"""Constants used throughout the pipeline"""

from pathlib import Path

# directories
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR.parent / "data"
CLEAN_DIR = DATA_DIR / "clean"
RAW_DIR = DATA_DIR / "raw"

# raw data
RAW_COUNTERGLOW_FPATH = RAW_DIR / "Counterglow+Facility+List+Complete.csv"
RAW_FSIS_FPATH = RAW_DIR / "fsis-processors-with-location.csv"
RAW_INFOGROUP_FPATH = RAW_DIR / "infogroup"
RAW_CAFO_FPATH = RAW_DIR / "cafo"
US_STATES_FPATH = RAW_DIR / "gz_2010_us_040_00_500k.json"

# cleaned data
CLEANED_COUNTERGLOW_FPATH = CLEAN_DIR / "cleaned_counterglow_facility_list.csv"
CLEANED_INFOGROUP_FPATH = CLEAN_DIR / "cleaned_infogroup_plants_all_time.csv"
CLEANED_FSIS_PROCESSORS_FPATH = CLEAN_DIR / "cleaned_fsis_processors.csv"
CLEANED_CAFO_POULTRY_FPATH = CLEAN_DIR / "cleaned_cafo_poultry.csv"
MATCHED_FARMS_FPATH = CLEAN_DIR / "matched_farms.csv"
UNMATCHED_FARMS_FPATH = CLEAN_DIR / "unmatched_farms.csv"
CLEANED_MATCHED_PLANTS_FPATH = CLEAN_DIR / "cleaned_matched_plants.csv"

# geojsons
ALL_STATES_GEOJSON_FPATH = CLEAN_DIR / "all_states_with_parent_corp_by_corp.geojson"
COUNTERGLOW_GEOJSON_FPATH = CLEAN_DIR / "counterglow_geojson.geojson"
ISOCHRONES_WITH_PARENT_CORP_FPATH = CLEAN_DIR / "isochrones_with_parent_corp.geojson"

# config file
CONFIG_FPATH = ROOT_DIR / "config.json"

# mapping
ALBERS_EQUAL_AREA = "EPSG:9822"
WGS84 = "EPSG:4326"
USA_LAT = 37.0902
USA_LNG = -95.7129


# state abbreviations
abb2state = {
    "AL":"Alabama",
    "AK":"Alaska",
    "AZ":"Arizona",
    "AR":"Arkansas",
    "CA":"California",
    "CO":"Colorado",
    "CT":"Connecticut",
    "DE":"Delaware",
    "FL":"Florida",
    "GA":"Georgia",
    "HI":"Hawaii",
    "ID":"Idaho",
    "IL":"Illinois",
    "IN":"Indiana",
    "IA":"Iowa",
    "KS":"Kansas",
    "KY":"Kentucky",
    "LA":"Louisiana",
    "ME":"Maine",
    "MD":"Maryland",
    "MA":"Massachusetts",
    "MI":"Michigan",
    "MN":"Minnesota",
    "MS":"Mississippi",
    "MO":"Missouri",
    "MT":"Montana",
    "NE":"Nebraska",
    "NV":"Nevada",
    "NH":"New Hampshire",
    "NJ":"New Jersey",
    "NM":"New Mexico",
    "NY":"New York",
    "NC":"North Carolina",
    "ND":"North Dakota",
    "OH":"Ohio",
    "OK":"Oklahoma",
    "OR":"Oregon",
    "PA":"Pennsylvania",
    "RI":"Rhode Island",
    "SC":"South Carolina",
    "SD":"South Dakota",
    "TN":"Tennessee",
    "TX":"Texas",
    "UT":"Utah",
    "VT":"Vermont",
    "VA":"Virginia",
    "WA":"Washington",
    "WV":"West Virginia",
    "WI":"Wisconsin",
    "WY":"Wyoming"
}

