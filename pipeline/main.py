import clean
from ..notebooks.utils import visualize
from ..notebooks.utils import analyze
import argparse
from pathlib import Path

def main(data_dir):
	# try:    
    	# DATA CLEANING 
    	# print("Cleaning FSIS data")
		# clean.clean_fsis(data_dir) # saves cleaned data to the defined output directory
	# 	print("Cleaning Counterglow")
	# 	clean.clean_counterglow(data_dir)
	# 	# additional cleaning
    #     print("Cleaning Infogroup")
	#     clean.clean_infogroup(data_dir)
    # cleaning CAFO permit data
    # clean.clean_CAFO()
	# except Exception as e:
	# 	# maybe some sort of logging - could have a logs folder where this saves error messages
	# 	# short term solution
	# 	print(f"Oops you screwed up dummy: {e}")
	# 	exit(1)
	try:
		# Data Cleaning
		print("Cleaning FSIS data...")
		# clean.clean_FSIS()
		print("Cleaning Counterglow data...")
		# clean.clean_counterglow()
		print("Cleaning Infogroup data...")
		# clean.clean_infogroup()
		print("Cleaning CAFO Permit data...")
    except Exception as e:
        print("test")

if __name__ is "__main__":
	main("../data/raw")