import clean
import match_farms
import match_plants
import calculate_captured_areas
from ..notebooks.utils import visualize
from ..notebooks.utils import analyze
import argparse
from pathlib import Path
import pandas as pd

def main(token): # what should we put in datadir? which ones should take user input? 
	try:
		# Data Cleaning
		print("Cleaning FSIS data...")
		clean.clean_FSIS("../data/raw/fsis-processors-with-location.csv")
		print("Cleaning Counterglow data...")
		clean.clean_counterglow("../data/raw/Counterglow+Facility+List+Complete.csv")
		print("Cleaning Infogroup data...")
		clean.clean_infogroup()
		print("Cleaning CAFO Permit data...")
		clean.clean_CAFO("../data/raw/cafo")

		# Match plants and farms
		print("Matching FSIS and Infogroup...")
		match_plants.save_all_matches("../data/clean/poultry_plants_2022.csv",\
				"../data/cleaned_fsis_processors.csv", 5)
		print("Matching CAFO permit data and Counterglow for poultry plants...")
		match_farms.match_all_farms("../data/raw/Counterglow+Facility+List+Complete.csv",\
			      "../data/clean/cleaned_matched_farms.csv", "Poultry|Chicken|Broiler")
		
		# Generate GeoJSONs and maps
		print("Creating plant capture GeoJSON...")
		calculate_captured_areas.full_script(token)
		
		print("Mapping CAFO permits...")
		match_df = pd.read_csv("../data/clean/matched_farms.csv")
		states = match_df["state"].unique().tolist()
		for state in states:
			path = "../html/cafo_poultry_eda_" + "state" + ".html"
			visualize.map_state("../data/clean/matched_farms.csv", "../data/clean/unmatched_farms.csv", state).save(path)

	except:
	# except Exception as e:
	# 	maybe some sort of logging - could have a logs folder where this saves error messages
	# 	short term solution
	# 	print(f"Oops you screwed up dummy: {e}")
	# 	exit(1)
		exit(1)

if __name__ is "__main__":
	main()