"""Executes cleaning and analysis scripts given the the animal type
and a distance threshold in km to find matching farms within, and whether
filtering needs to be done on Infogroup or not. Functions can be run 
individually by including a function flag; the default is to run all of them.
"""

import clean
import match_farms
import match_plants
import calculate_captured_areas
import farm_geojson_creation
import os

import utils.visualize as visualize
import utils.analyze as analyze

import argparse
import pandas as pd
import warnings
import json

warnings.filterwarnings("ignore")
from pipeline.constants import (
    RAW_FSIS_FPATH,
    RAW_COUNTERGLOW_FPATH,
    RAW_INFOGROUP_FPATH,
    RAW_CAFO_FPATH,
    CLEANED_INFOGROUP_FPATH,
    CLEANED_FSIS_PROCESSORS_FPATH,
    CLEANED_COUNTERGLOW_FPATH,
    CLEANED_CAFO_POULTRY_FPATH,
    MATCHED_FARMS_FPATH,
    UNMATCHED_FARMS_FPATH,
    ROOT_DIR,
    CLEAN_DIR,
    ALL_STATES_GEOJSON_FPATH,
    CONFIG_FPATH, 
    SMOKE_TEST_FPATH,
    SMOKE_TEST_CLEAN_FPATH,
    DATA_DIR
)

with open(CONFIG_FPATH, "r") as jsonfile:
    config = json.load(jsonfile)
    print("Config file read successful")

def create_parser():
    """Argparser that contains all the command line arguments for executing
    the main script, which includes the type of animal, distance threshold for
    matching entries, filtering, and what functions to run.

    Args:
        None
    
    Returns:
        None

    """
    parser = argparse.ArgumentParser(
        description="Executes scripts for cleaning, matching, \
            and analyzing poultry plant and farm data."
    )
    # Inputs - defaults are set
    parser.add_argument(
        "animal",
        type=str,
        default="Poultry|Chicken|Broiler",
        nargs="?",
        help="Keywords for animals to filter for, as a regex"
    )
    parser.add_argument(
        "distance",
        type=float,
        default=5,
        nargs="?",
        help="Maximum distance for farm matches to be made across\
            different datasets, in km"
    )
    parser.add_argument(
        "code",
        type=str,
        default="2015",
        nargs="?",
        help="SIC code to filter Infogroup entries on"
    )
    parser.add_argument(
        "filtering",
        type=bool,
        default=False,
        nargs="?",
        help="Determines whether Infogroup data is raw \
            and needs filtering by SIC Code"
    )
    parser.add_argument(
        "--function",
        choices=[
            "clean_FSIS",
            "clean_counterglow",
            "clean_infogroup",
            "clean_cafo",
            "match_plants",
            "match_farms",
            "calculate_captured_areas",
            "visualize",
            "create_counterglow_geojson",
        ],
        help="Specify the function to run.",
    )
    parser.add_argument(
        "--smoke_test",
        action='store_true',
        help="Indicates whether smoke test on Infogroup data\
            should be run or not"
    )

    return parser


def run_all(args) -> None:
    """In the case that no specific functions are specified in the command line, 
    executes all functions in the script.
    
    Args:  
        None

    Returns:
        None
    """
    try:
        # Data Cleaning
        print("Cleaning FSIS data...")
        clean.clean_FSIS(RAW_FSIS_FPATH)
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Cleaning Counterglow data...")
        clean.clean_counterglow(RAW_COUNTERGLOW_FPATH)
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Cleaning Infogroup data...")
        ABI_dict = config["ABI_map"]
        if args.smoke_test:
            clean.clean_infogroup(SMOKE_TEST_FPATH, 
                    ABI_dict, 
                    args.code, 
                    SMOKE_TEST_CLEAN_FPATH,
                    True)
        else:
            clean.clean_infogroup(RAW_INFOGROUP_FPATH, 
                                ABI_dict, 
                                args.code, 
                                CLEANED_INFOGROUP_FPATH,
                                args.filtering)
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Cleaning CAFO Permit data...")
        clean.clean_cafo(RAW_CAFO_FPATH, RAW_CAFO_FPATH / "farm_source.json")
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        # Match plants and farms
        print("Matching FSIS plants and Infogroup for sales volume data...")
        match_plants.save_all_matches(
            CLEANED_INFOGROUP_FPATH, 
            CLEANED_FSIS_PROCESSORS_FPATH, 
            args.distance
        )
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Matching CAFO permit data and Counterglow for farms...")
        match_farms.match_all_farms(
            CLEANED_COUNTERGLOW_FPATH, CLEANED_CAFO_POULTRY_FPATH, args.animal
        )
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        # Generate GeoJSONs and maps
        print("Creating plant capture GeoJSON...")
        try:
            MAPBOX_KEY = os.getenv('MAPBOX_API')
        except:
            print("Missing environment variable")
        calculate_captured_areas.full_script(MAPBOX_KEY)
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Mapping CAFO permits...")
        match_df = pd.read_csv(MATCHED_FARMS_FPATH)
        match_df = match_df[match_df["lat"].notna()]
        states = match_df["state"].unique().tolist()
        for state in states:
            path = "html/cafo_poultry_eda_" + state + ".html"
            visualize.map_state(MATCHED_FARMS_FPATH, 
                                UNMATCHED_FARMS_FPATH, state).save(
                ROOT_DIR / path
            )
    except Exception as e:
        print(f"{e}")
        exit(1)

    try:
        print("Creating Counterglow GeoJSON...")
        farm_geojson_creation.create_counterglow_geojson(
            CLEANED_COUNTERGLOW_FPATH,
            CLEAN_DIR / "all_states_with_parent_corp_by_corp.geojson",
        )
    except Exception as e:
        print(f"{e}")
        exit(1)


def main(args) -> None:
    """Executes functions based on what was specified in command line. 
    If no function names were specified, runs all functions in the script.

    Args:
        None
    
    Returns:
        None
    """
    if args.function:
        if args.function == "clean_FSIS":
            try:
                # Data Cleaning
                print("Cleaning FSIS data...")
                clean.clean_FSIS(RAW_FSIS_FPATH)
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "clean_counterglow":
            try:
                print("Cleaning Counterglow data...")
                clean.clean_counterglow(RAW_COUNTERGLOW_FPATH)
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "clean_infogroup":
            try:
                print("Cleaning Infogroup data...")
                ABI_dict = config["ABI_map"]
                if args.smoke_test:
                    clean.clean_infogroup(SMOKE_TEST_FPATH, 
                                          ABI_dict, 
                                          args.code,
                                          SMOKE_TEST_CLEAN_FPATH,
                                          True)
                else:
                    clean.clean_infogroup(RAW_INFOGROUP_FPATH, 
                                          ABI_dict, 
                                          args.code, 
                                          CLEANED_INFOGROUP_FPATH,
                                          args.filtering)
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "clean_cafo":
            try:
                print("Cleaning CAFO Permit data...")
                clean.clean_cafo(RAW_CAFO_FPATH, 
                                 RAW_CAFO_FPATH / "farm_source.json")
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "match_plants":
            try:
                # Match plants and farms
                print("Matching FSIS plants and Infogroup for sales volume \
                      data...")
                match_plants.save_all_matches(
                    CLEANED_INFOGROUP_FPATH,
                    CLEANED_FSIS_PROCESSORS_FPATH,
                    args.distance,
                )
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "match_farms":
            try:
                print("Matching CAFO permit data and Counterglow for farms...")
                match_farms.match_all_farms(
                    CLEANED_COUNTERGLOW_FPATH, 
                    CLEANED_CAFO_POULTRY_FPATH, 
                    args.animal
                )
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "calculate_captured_areas":
            try:
                # Generate GeoJSONs and maps
                print("Creating plant capture GeoJSON...")
                try:
                    MAPBOX_KEY = os.getenv('MAPBOX_API')
                except:
                    print("Missing environment variable")
                calculate_captured_areas.full_script(MAPBOX_KEY)
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "visualize":
            try:
                print("Mapping CAFO permits...")
                match_df = pd.read_csv(MATCHED_FARMS_FPATH)
                match_df = match_df[match_df["lat"].notna()]
                states = match_df["state"].unique().tolist()
                for state in states:
                    path = "html/cafo_poultry_eda_" + state + ".html"
                    visualize.map_state(
                        MATCHED_FARMS_FPATH, UNMATCHED_FARMS_FPATH, state
                    ).save(DATA_DIR / path)
            except Exception as e:
                print(f"{e}")
                exit(1)

        elif args.function == "create_counterglow_geojson":
            try:
                print("Creating Counterglow GeoJSON...")
                farm_geojson_creation.create_counterglow_geojson(
                    CLEANED_COUNTERGLOW_FPATH, ALL_STATES_GEOJSON_FPATH
                )
            except Exception as e:
                print(f"{e}")
                exit(1)

    else:
        run_all(args)

    print("Done!")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() 
    parser = create_parser()
    args = parser.parse_args()
    main(args)