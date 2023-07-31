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

# Running the Pipeline:
1. **Establish directory structure** 
    - pipeline
    - notebooks
    - data
        - raw
            - infogroup
            - cafo
        - clean
    - html
2. **Set up Conda environment**
    - conda create --name <myenv> python=3.9.16
2. **Download the files**
    - From team rafi google drive/Data, into data/raw add:
        - fsis-processors-with-location.csv
        - fsis-processors.csv
        - Counterglow+Facility+List+Complete.csv
    - From team rafi google drive/Data/CAFO, into data/raw/cafo add:
        - nc_cafo.csv
        - ms_cafo.csv
        - farm_source.json
        - al_cafo.csv
    - From team rafi google drive/Data/Infogroup, into data/raw/infogroup add:
        - poultry_plants_x.csv
            - where "x" is every year from 1997 to 2022
3. **Run pip install -r pipeline/requirements.txt**
4. **Run pip install -r notebooks/requirements.txt**
5. **Run main.py**
    - Structure the command line arguments as:
        - python main.py FILEPATH ANIMAL DISTANCE SIC_CODE FILTERING
            - FILEPATH; str; Relative path (from cwd) to raw data folder
            - ANIMAL; str; Keywords for animals to filter for, as a regex
            - DISTANCE; float; Maximum distance for farm matches to be made across different datasets, in km
            - SIC_CODE; str; SIC code to filter the dataset on, if FILTERING is False, this variable is not used
            - FILTERING; bool; True if infogroup data is raw and needs to be filtered by SIC code
        - i.e. python main.py "../data/raw" "poultry|chicken|broiler" 5 "2015" True
    - All functions are executed by default. If you want to run specific functions only, include a command line argument for all functions that you want to be excluded/not run. 
