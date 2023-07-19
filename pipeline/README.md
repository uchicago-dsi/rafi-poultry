
# Rafi Poultry Pipeline README.md file

This is the pipeline for this project and a description of the files within it.

# List of Files

- calculate_captured_area.py
- clean.py
- counterglow_matches.py
- distances.py
- match_plants.py

# File Descriptions

- **calculate_captured_area.py** Reads in clean FSIS data (2022) from CSV file, reads in clean Infogroup data (2022) from CSV file, generate plant isochrones using the Mapbox API and output a GeoJSON file, groups plants by parent corporation and number of captured areas. Groups areas captured by one plant by state, calculate the total captured area in square miles, and output a GeoJSON file. Calculates the HHI and adds it to the GeoJSON. Writes the output DataFrame to the data/clean folder as captured_area.geojson.
- **clean.py** read in raw datasets from FSIS, Infogroup, Counterglow, and cafomaps.org, standardize the columns, fill in null values, filter to records of interest (e.g., poultry farms), and then output cleaned_cafo_poultry.csv, cleaned_counterglow_facility_list.csv, cleaned_infogroup_plants_all_time.csv, and cleaned_fsis_processors.csv to the data/clean folder.
- **counterglow_matches.py** file contained the functionality neccessary to match Infogroup data against Counterglow data. The goal is to see if any business listed in the Infogroup dataset matches will a suspects farm in the Counterglow dataset.
- **distances.py** contains calculations used in various parts of the research
- **match_plants.py** Reads in clean Infogroup datasets from 1997 through the present, matches plants across years using the ABI, match plants in FSIS with plants in Infogroup by location and address, to add sales volume data to plant records, writes the combined output DataFrame as a CSV file, matched_plants.csv, in the data/clean folder.
