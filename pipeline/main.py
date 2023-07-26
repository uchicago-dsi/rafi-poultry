import clean
import match_farms
import match_plants
import calculate_captured_areas

import sys
sys.path.append('..')
from notebooks.utils import visualize
from notebooks.utils import analyze

import argparse
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

def create_parser():
    parser = argparse.ArgumentParser(description='Executes scripts for cleaning, matching, and analyzing poultry plant and farm data.')
    parser.add_argument('filepath', type=str, help='Relative path to raw data folder')
    parser.add_argument('animal', type=str, help='Keywords for animals to filter for, as a regex')
    parser.add_argument('distance', type=float, help='Maximum distance for farm matches to be made, in km')
    return parser

def main(args): 
	try:
		# Data Cleaning
		print("Cleaning FSIS data...")
		clean.clean_FSIS(args.filepath + "/fsis-processors-with-location.csv")
		
		print("Cleaning Counterglow data...")
		clean.clean_counterglow(args.filepath + "/Counterglow+Facility+List+Complete.csv")
		
		print("Cleaning Infogroup data...")
		clean.clean_infogroup(args.filepath + "/infogroup")
		
		print("Cleaning CAFO Permit data...")
		clean.clean_cafo(args.filepath + "/cafo", args.filepath + "/cafo/farm_source.json")

		# Match plants and farms
		print("Matching FSIS and Infogroup...")
		match_plants.save_all_matches("../data/clean/cleaned_infogroup_plants_all_time.csv",\
				"../data/clean/cleaned_fsis_processors.csv", 5)
		print("Matching CAFO permit data and Counterglow for poultry plants...")
		match_farms.match_all_farms(args.filepath + "Counterglow+Facility+List+Complete.csv",\
			      "../data/clean/cleaned_matched_farms.csv", args.animal)
		
		# Generate GeoJSONs and maps
		print("Creating plant capture GeoJSON...")
		calculate_captured_areas.full_script("pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xqc3FnN2NjMDBqczNkdDNmdjBvdnU0ciJ9.0RfS-UsqS63pbAuqrE_REw")
		
		print("Mapping CAFO permits...")
		match_df = pd.read_csv("../data/clean/matched_farms.csv")
		match_df = match_df[match_df['lat'].notna()]
		states = match_df["state"].unique().tolist()

		for state in states:
			path = "../html/cafo_poultry_eda_" + "state" + ".html"
			visualize.map_state("../data/clean/matched_farms.csv", "../data/clean/unmatched_farms.csv", state).save(path)

	except Exception as e:
		print(f"{e}")
		exit(1)


if __name__ == "__main__":
	parser = create_parser()
	args = parser.parse_args()
	main(args)