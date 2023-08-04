"""Executes cleaning and analysis scripts given the filepath to raw data, the animal type, 
and a distance threshold in km to find matching farms within.
"""

import clean
import match_farms
import match_plants
import calculate_captured_areas
import geojson_creation

import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'notebooks', 'utils'))
import utils.visualize as visualize
import utils.analyze as analyze

import argparse
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from constants import RAW_FSIS_FPATH, RAW_COUNTERGLOW_FPATH, RAW_INFOGROUP_FPATH, RAW_CAFO_FPATH, CLEANED_INFOGROUP_FPATH,\
	  CLEANED_FSIS_PROCESSORS_FPATH, CLEANED_COUNTERGLOW_FPATH, CLEANED_CAFO_POULTRY_FPATH, MATCHED_FARMS_FPATH,\
	  UNMATCHED_FARMS_FPATH, ROOT_DIR, CLEAN_DIR, ALL_STATES_GEOJSON_FPATH


def create_parser():
	parser = argparse.ArgumentParser(description='Executes scripts for cleaning, matching, and analyzing poultry plant and farm data.')
	# Inputs - defaults are set
	parser.add_argument('filepath', type=str, default="../data/raw", nargs='?', help='Relative path to raw data folder')
	parser.add_argument('animal', type=str, default="Poultry|Chicken|Broiler", nargs='?', help='Keywords for animals to filter for, as a regex')
	parser.add_argument('distance', type=float, default=5, nargs='?', help='Maximum distance for farm matches to be made across different datasets, in km')
	parser.add_argument('code', type=str, default="2015", nargs='?', help='SIC code to filter Infogroup entries on')
	parser.add_argument('filtering', type=bool, default=False, nargs='?', help='Determines whether infogroup data is raw and needs filtering by SIC Code')

	parser.add_argument('--function', choices = ["clean_FSIS", "clean_counterglow", \
						      "clean_infogroup", "clean_cafo", "match_plants", "match_farms", \
							  "calculate_captured_areas", "visualize", "counterglow_geojson_chicken"], help="Specify the function to run.")

	return parser

def run_all(args): 
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
		clean.clean_infogroup(RAW_INFOGROUP_FPATH, args.code, args.filtering)
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
		match_plants.save_all_matches(CLEANED_INFOGROUP_FPATH,\
				CLEANED_FSIS_PROCESSORS_FPATH, args.distance)
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Matching CAFO permit data and Counterglow for farms...")
		match_farms.match_all_farms(CLEANED_COUNTERGLOW_FPATH, CLEANED_CAFO_POULTRY_FPATH, args.animal)
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		# Generate GeoJSONs and maps
		print("Creating plant capture GeoJSON...")
		calculate_captured_areas.full_script("pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xqc3FnN2NjMDBqczNkdDNmdjBvdnU0ciJ9.0RfS-UsqS63pbAuqrE_REw")
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Mapping CAFO permits...")
		match_df = pd.read_csv(MATCHED_FARMS_FPATH)
		match_df = match_df[match_df['lat'].notna()]
		states = match_df["state"].unique().tolist()
		for state in states:
			path = "html/cafo_poultry_eda_" + state + ".html"
			visualize.map_state(MATCHED_FARMS_FPATH, UNMATCHED_FARMS_FPATH, state).save(ROOT_DIR / path)
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Creating Counterglow GeoJSON...")
		geojson_creation.counterglow_geojson_chicken(CLEANED_COUNTERGLOW_FPATH,\
			      CLEAN_DIR / "all_states_with_parent_corp_by_corp.geojson")
	except Exception as e:
		print(f"{e}")
		exit(1)


def main(args): 
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
				clean.clean_infogroup(RAW_INFOGROUP_FPATH, args.code, args.filtering)
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "clean_cafo":
			try:
				print("Cleaning CAFO Permit data...")
				clean.clean_cafo(RAW_CAFO_FPATH, RAW_CAFO_FPATH / "farm_source.json")
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "match_plants":
			try:
				# Match plants and farms
				print("Matching FSIS plants and Infogroup for sales volume data...")
				match_plants.save_all_matches(CLEANED_INFOGROUP_FPATH,\
						CLEANED_FSIS_PROCESSORS_FPATH, args.distance)
			except Exception as e:
				print(f"{e}")
				exit(1)

		elif args.function == "match_farms":
			try:
				print("Matching CAFO permit data and Counterglow for farms...")
				match_farms.match_all_farms(CLEANED_COUNTERGLOW_FPATH, CLEANED_CAFO_POULTRY_FPATH, args.animal)
			except Exception as e:
				print(f"{e}")
				exit(1)

		elif args.function == "calculate_captured_areas":
			try:
				# Generate GeoJSONs and maps
				print("Creating plant capture GeoJSON...")
				calculate_captured_areas.full_script("pk.eyJ1IjoidG9kZG5pZWYiLCJhIjoiY2xqc3FnN2NjMDBqczNkdDNmdjBvdnU0ciJ9.0RfS-UsqS63pbAuqrE_REw")
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "visualize":
			try:
				print("Mapping CAFO permits...")
				match_df = pd.read_csv(MATCHED_FARMS_FPATH)
				match_df = match_df[match_df['lat'].notna()]
				states = match_df["state"].unique().tolist()
				for state in states:
					path = "html/cafo_poultry_eda_" + state + ".html"
					visualize.map_state(MATCHED_FARMS_FPATH, UNMATCHED_FARMS_FPATH, state).save(ROOT_DIR / path)
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "counterglow_geojson_chicken":
			try:
				print("Creating Counterglow GeoJSON...")
				geojson_creation.counterglow_geojson_chicken(CLEANED_COUNTERGLOW_FPATH,\
						ALL_STATES_GEOJSON_FPATH)
			except Exception as e:
				print(f"{e}")
				exit(1)

	else:
		run_all(args)
	
	print("Done!")


if __name__ == "__main__":
	parser = create_parser()
	args = parser.parse_args()
	main(args)