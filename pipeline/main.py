"""Executes cleaning and analysis scripts given the filepath to raw data, the animal type, 
and a distance threshold in km to find matching farms within.
"""

import clean
import match_farms
import match_plants
import calculate_captured_areas

import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'notebooks', 'utils'))
import visualize
import analyze

import argparse
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

here = Path(__file__).resolve().parent

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
							  "calculate_captured_areas", "visualize"], help="Specify the function to run.")

	return parser

def run_all(args): 
	try:
		# Data Cleaning
		print("Cleaning FSIS data...")
		clean.clean_FSIS(here.parent / "data/raw/fsis-processors-with-location.csv")
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Cleaning Counterglow data...")
		clean.clean_counterglow(here.parent / "data/raw/Counterglow+Facility+List+Complete.csv")
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Cleaning Infogroup data...")
		clean.clean_infogroup(here.parent / "data/raw/infogroup", args.code, args.filtering)
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Cleaning CAFO Permit data...")
		clean.clean_cafo(here.parent / "data/raw/cafo", here.parent / "data/raw/cafo/farm_source.json")
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		# Match plants and farms
		print("Matching FSIS plants and Infogroup for sales volume data...")
		match_plants.save_all_matches(here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv",\
				here.parent / "data/clean/cleaned_fsis_processors.csv", args.distance)
	except Exception as e:
		print(f"{e}")
		exit(1)

	try:
		print("Matching CAFO permit data and Counterglow for farms...")
		match_farms.match_all_farms(here.parent / "data/raw/Counterglow+Facility+List+Complete.csv",\
				here.parent / "data/clean/cleaned_matched_farms.csv", args.animal)
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
		match_df = pd.read_csv(here.parent / "data/clean/matched_farms.csv")
		match_df = match_df[match_df['lat'].notna()]
		states = match_df["state"].unique().tolist()
		for state in states:
			path = "html/cafo_poultry_eda_" + state + ".html"
			visualize.map_state(here.parent / "data/clean/matched_farms.csv", here.parent / "data/clean/unmatched_farms.csv", state).save(here.parent / path)
	except Exception as e:
		print(f"{e}")
		exit(1)


def main(args): 
	if args.function:
		if args.function == "clean_FSIS":
			try:
				# Data Cleaning
				print("Cleaning FSIS data...")
				clean.clean_FSIS(here.parent / "data/raw/fsis-processors-with-location.csv")
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "clean_counterglow":
			try:
				print("Cleaning Counterglow data...")
				clean.clean_counterglow(here.parent / "data/raw/Counterglow+Facility+List+Complete.csv")
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "clean_infogroup":
			try:
				print("Cleaning Infogroup data...")
				clean.clean_infogroup(here.parent / "data/raw/infogroup", args.code, args.filtering)
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "clean_cafo":
			try:
				print("Cleaning CAFO Permit data...")
				clean.clean_cafo(here.parent / "data/raw/cafo", here.parent / "data/raw/cafo/farm_source.json")
			except Exception as e:
				print(f"{e}")
				exit(1)
		
		elif args.function == "match_plants":
			try:
				# Match plants and farms
				print("Matching FSIS plants and Infogroup for sales volume data...")
				match_plants.save_all_matches(here.parent / "data/clean/cleaned_infogroup_plants_all_time.csv",\
						here.parent / "data/clean/cleaned_fsis_processors.csv", args.distance)
			except Exception as e:
				print(f"{e}")
				exit(1)

		elif args.function == "match_farms":
			try:
				print("Matching CAFO permit data and Counterglow for farms...")
				match_farms.match_all_farms(here.parent / "data/raw/Counterglow+Facility+List+Complete.csv",\
						here.parent / "data/clean/cleaned_matched_farms.csv", args.animal)
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
				match_df = pd.read_csv(here.parent / "data/clean/matched_farms.csv")
				match_df = match_df[match_df['lat'].notna()]
				states = match_df["state"].unique().tolist()

				for state in states:
					path = "html/cafo_poultry_eda_" + state + ".html"
					visualize.map_state(here.parent / "data/clean/matched_farms.csv", here.parent / "data/clean/unmatched_farms.csv", state).save(here.parent / path)
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