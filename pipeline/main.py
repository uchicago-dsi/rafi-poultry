"""Executes cleaning and analysis scripts given the filepath to raw data, the animal type, 
and a distance threshold in km to find matching farms within.
"""

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
	# inputs
	parser.add_argument('filepath', type=str, default="../data/raw", nargs='?', help='Relative path to raw data folder')
	parser.add_argument('animal', type=str, default="Poultry|Chicken|Broiler", nargs='?', help='Keywords for animals to filter for, as a regex')
	parser.add_argument('distance', type=float, default=5, nargs='?', help='Maximum distance for farm matches to be made across different datasets, in km')
	parser.add_argument('SIC code', type=str, default="2015", nargs='?', help='SIC code to filter Infogroup entries on')

	# functions
	parser.add_argument('--clean_FSIS', action='store_false', help='Run clean_FSIS')
	parser.add_argument('--clean_counterglow', action='store_false', help='Run clean_counterglow')
	parser.add_argument('--clean_infogroup', action='store_false', help='Run clean_infogroup')
	parser.add_argument('--clean_cafo', action='store_false', help='Run clean_cafo')
	parser.add_argument('--match_plants', action='store_false', help='Run match_plants')
	parser.add_argument('--match_farms', action='store_false', help='Run match_farms')
	parser.add_argument('--calculate_captured_areas', action='store_false', help='Run calculate_captured_areas')
	parser.add_argument('--visualize', action='store_false', help='Run visualize')

	return parser

def main(args): 
	if args.clean_FSIS:
		try:
			# Data Cleaning
			print("Cleaning FSIS data...")
			clean.clean_FSIS(args.filepath + "/fsis-processors-with-location.csv")
		except Exception as e:
			print(f"{e}")
			exit(1)
	
	if args.clean_counterglow:
		try:
			print("Cleaning Counterglow data...")
			clean.clean_counterglow(args.filepath + "/Counterglow+Facility+List+Complete.csv")
		except Exception as e:
			print(f"{e}")
			exit(1)
	
	if not args.clean_infogroup:
		try:
			print("Cleaning Infogroup data...")
			clean.clean_infogroup(args.filepath + "/infogroup")
		except Exception as e:
			print(f"{e}")
			exit(1)
	
	if args.clean_cafo:
		try:
			print("Cleaning CAFO Permit data...")
			clean.clean_cafo(args.filepath + "/cafo", args.filepath + "/cafo/farm_source.json")
		except Exception as e:
			print(f"{e}")
			exit(1)
	
	if args.match_plants:
		try:
			# Match plants and farms
			print("Matching FSIS and Infogroup...")
			match_plants.save_all_matches("../data/clean/cleaned_infogroup_plants_all_time.csv",\
					"../data/clean/cleaned_fsis_processors.csv", args.distance)
		except Exception as e:
			print(f"{e}")
			exit(1)

	if args.match_farms:
		try:
			print("Matching CAFO permit data and Counterglow for poultry plants...")
			match_farms.match_all_farms(args.filepath + "/Counterglow+Facility+List+Complete.csv",\
					"../data/clean/cleaned_matched_farms.csv", args.animal)
		except Exception as e:
			print(f"{e}")
			exit(1)

	if args.calculate_captured_areas:
		try:
			# Generate GeoJSONs and maps
			print("Creating plant capture GeoJSON...")
			calculate_captured_areas.full_script("pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xqc3FnN2NjMDBqczNkdDNmdjBvdnU0ciJ9.0RfS-UsqS63pbAuqrE_REw")
		except Exception as e:
			print(f"{e}")
			exit(1)
	
	if args.visualize:
		try:
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