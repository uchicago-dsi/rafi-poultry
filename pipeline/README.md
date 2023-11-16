# RAFI-USA Poultry Pipeline README.md file

This README contains information on the structure of the pipeline for the project and a description of the files and folder structure necessary to run it. 

# List of Files

- calculate_captured_area.py
- clean.py
- counterglow_matches.py
- distances.py
- match_plants.py
- sic_matcher.py

# File Descriptions

- **calculate_captured_area.py** Reads in clean FSIS data (2022) from CSV file, reads in clean Infogroup data (2022) from CSV file, generate plant isochrones using the Mapbox API and output a GeoJSON file, groups plants by parent corporation and number of captured areas. Groups areas captured by one plant by state, calculate the total captured area in square miles, and output a GeoJSON file. Calculates the HHI and adds it to the GeoJSON. Writes the output DataFrame to the data/clean folder as captured_area.geojson.
- **clean.py** read in raw datasets from FSIS, Infogroup, Counterglow, and individual state websites, standardize the columns, fill in null values, filter to records of interest (e.g., poultry farms), and then output cleaned_cafo_poultry.csv, cleaned_counterglow_facility_list.csv, cleaned_infogroup_plants_all_time.csv, and cleaned_fsis_processors.csv to the data/clean folder. Because state permit data is often formatted differently, users must update the farm_source.json file in the cafo folder with the names of the columns they want to be processed (name, address, permit, lat, long).
- **counterglow_matches.py** file contained the functionality neccessary to match Infogroup data against Counterglow data. The goal is to see if any business listed in the Infogroup dataset matches will a suspects farm in the Counterglow dataset.
- **distances.py** contains calculations used in various parts of the research
- **match_plants.py** Reads in clean Infogroup datasets from 1997 through the present, matches plants across years using the ABI, match plants in FSIS with plants in Infogroup by location and address, to add sales volume data to plant records, writes the combined output DataFrame as a CSV file, matched_plants.csv, in the data/clean folder.
- **match_farms.py** Reads in clean state permit datasets and Counterglow dataset to match farms across the two for the specified animal type, making matches and fuzzy matches based on name and location (if available). Outputs standardized datasets of matched and unmatched farms: matched_farms.csv and unmatched_farms.csv.
- **sic_matcher.py** allows the user to go through an entire dataframe of Infogroup data and filter out based on SIC Code that is input by the user. In this script, there is a choice to perform this task using the dask dataframe method or the pandas dataframe method.
- **farm_geojson_creation.py** reads in cleaned data from Counterglow, filters it for poultry only, and generates a Counterglow GeoJSON file containing plant access data based on the parent corporation information in the all_states_with_parent_corporation_by_corp.geojson file (which is created by the calculate_captured_areas script).


# Running the Pipeline:
1. **Establish directory structure** 
    - pipeline
    - notebooks
    - data
2. **Set up Conda environment**
   - conda create --name <myenv> python=3.9.16
3. **Download the files**
   - From team RAFI google drive/Data, download the data files into the data folder from the previous directory structure
   - From team RAFI google drive, download the .env file and place it under the rafi-poultry directory
4. **Run pip install -r pipeline/requirements.txt**
5. **Run pip install -r notebooks/requirements.txt**
6. **Run pip install -e .**
   - This installs the pipeline as a package.
7. **Run pip install geopy**
8. **Run main.py**
   - Structure the command line arguments as:
     - python main.py FILEPATH ANIMAL DISTANCE SIC_CODE FILTERING
       - FILEPATH; str; Relative path (from cwd) to raw data folder
       - ANIMAL; str; Keywords for animals to filter for, as a regex
       - DISTANCE; float; Maximum distance for farm matches to be made across different datasets, in km
       - SIC_CODE; str; SIC code to filter the dataset on, if FILTERING is False, this variable is not used
       - FILTERING; bool; True if infogroup data is raw and needs to be filtered by SIC code
     - i.e. python main.py "../data/raw" "poultry|chicken|broiler" 5 "2015" True
     - All functions are executed by default. Specify a function name in the command line argument following the --function flag to run that function individually.
     - To enable the smoke test for cleaning Infogroup files, add the flag --smoke_test True to the command line argument.
     - To run the NETS dataset version of the pipeline, add the flag --nets True to the command line argument