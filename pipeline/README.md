# Rafi Poultry Pipeline README.md file

This is the pipeline for this project and a description of the files within it.

# List of Files

- calculate_captured_area.py
- clean.py
- counterglow_matches.py
- distances.py
- match_plants.py
- sic_matcher.py

# File Descriptions

- **calculate_captured_area.py** Reads in clean FSIS data (2022) from CSV file, reads in clean Infogroup data (2022) from CSV file, generate plant isochrones using the Mapbox API and output a GeoJSON file, groups plants by parent corporation and number of captured areas. Groups areas captured by one plant by state, calculate the total captured area in square miles, and output a GeoJSON file. Calculates the HHI and adds it to the GeoJSON. Writes the output DataFrame to the data/clean folder as captured_area.geojson.
- **clean.py** read in raw datasets from FSIS, Infogroup, Counterglow, and cafomaps.org, standardize the columns, fill in null values, filter to records of interest (e.g., poultry farms), and then output cleaned_cafo_poultry.csv, cleaned_counterglow_facility_list.csv, cleaned_infogroup_plants_all_time.csv, and cleaned_fsis_processors.csv to the data/clean folder.
- **counterglow_matches.py** file contained the functionality neccessary to match Infogroup data against Counterglow data. The goal is to see if any business listed in the Infogroup dataset matches will a suspects farm in the Counterglow dataset.
- **distances.py** contains calculations used in various parts of the research
- **match_plants.py** Reads in clean Infogroup datasets from 1997 through the present, matches plants across years using the ABI, match plants in FSIS with plants in Infogroup by location and address, to add sales volume data to plant records, writes the combined output DataFrame as a CSV file, matched_plants.csv, in the data/clean folder.
- **sic_matcher.py** allows the user to go through an entire dataframe of Infogroup data and filter out based on SIC Code that is input by the user. In this script, there is a choice to perform this task using the dask dataframe method or the pandas dataframe method.

# TODO: Need step-by-step instructions to actually run this

# file downloads? file download locations? virtual environment? DOCKER??????????~~?~?~??@@?@2

# configuration setup?

# what should my data directory look like?

- need to have "raw" and "clean"

# test and include instructions for filtering the raw infogroup data

# include data that should be in cafo directory on the google drive

# maybe: make it easy to pull out _parts_ of the pipeline (and do this via command line arguments)

# what arguments do I need to pass

# need to fix the order for getting the cleaned FSIS data - need to move this into a function maybe?
