# RAFI-USA Poultry Pipeline README.md file

This README contains information on the structure of the pipeline for the project and a description of the files and folder structure necessary to run it.

# List of Files

- calculate_captured_area.py
- clean.py
- counterglow_matches.py
- distances.py
- match_plants.py
- match_plants_nets.py
- sic_matcher.py

# File Descriptions

- **calculate_captured_area.py** Reads in clean FSIS data (2022) from CSV file, reads in clean Infogroup data (2022) from CSV file, generate plant isochrones using the Mapbox API and output a GeoJSON file, groups plants by parent corporation and number of captured areas. Groups areas captured by one plant by state, calculate the total captured area in square miles, and output a GeoJSON file. Calculates the HHI and adds it to the GeoJSON. Writes the output DataFrame to the data/clean folder as captured_area.geojson.
- **clean.py** read in raw datasets from FSIS, Infogroup, Counterglow, and individual state websites, standardize the columns, fill in null values, filter to records of interest (e.g., poultry farms), and then output cleaned_cafo_poultry.csv, cleaned_counterglow_facility_list.csv, cleaned_infogroup_plants_all_time.csv, and cleaned_fsis_processors.csv to the data/clean folder. Because state permit data is often formatted differently, users must update the farm_source.json file in the cafo folder with the names of the columns they want to be processed (name, address, permit, lat, long).
- **counterglow_matches.py** file contained the functionality neccessary to match Infogroup data against Counterglow data. The goal is to see if any business listed in the Infogroup dataset matches will a suspects farm in the Counterglow dataset.
- **distances.py** contains calculations used in various parts of the research
- **match_plants.py** Reads in clean Infogroup datasets from 1997 through the present, matches plants across years using the ABI, match plants in FSIS with plants in Infogroup by location and address, to add sales volume data to plant records, writes the combined output DataFrame as a CSV file, matched_plants.csv, in the data/clean folder.
- **match_plants_nets.py** Reads in clean NETS datasets from 1990 through the present, matches plants and sales volume information in FSIS with plants in NETS by location and address, and writes the combined output DataFrame as a CSV file, cleaned_matched_plants.csv, in the data/clean folder.
- **match_farms.py** Reads in clean state permit datasets and Counterglow dataset to match farms across the two for the specified animal type, making matches and fuzzy matches based on name and location (if available). Outputs standardized datasets of matched and unmatched farms: matched_farms.csv and unmatched_farms.csv.
- **sic_matcher.py** allows the user to go through an entire dataframe of Infogroup data and filter out based on SIC Code that is input by the user. In this script, there is a choice to perform this task using the dask dataframe method or the pandas dataframe method.
- **farm_geojson_creation.py** reads in cleaned data from Counterglow, filters it for poultry only, and generates a Counterglow GeoJSON file containing plant access data based on the parent corporation information in the all_states_with_parent_corporation_by_corp.geojson file (which is created by the calculate_captured_areas script).

# Running the Pipeline:

1. **Establish directory structure**
   - pipeline
   - notebooks
   - data
     - raw
       - infogroup
       - cafo
       - nets
     - clean
     - html
   - Note: clone the repository first and then add the data directory in the rafi-poultry directory
2. **Set up Conda environment**
   - conda create --name \<myenv\> python=3.9.16
3. **Download the files**
   - From team RAFI google drive/Data/raw, into data/raw add:
     - fsis-processors-with-location.csv
     - fsis-processors.csv
     - Counterglow+Facility+List+Complete.csv
     - Dataset_Establishment_Demographic_Data.xlsx
     - gz_2010_us_040_00_500k.json
     - MPI_Directory_by_Establishment_Number.xlsx
   - From team RAFI google drive/Data/CAFO, into data/raw/cafo add:
     - nc_cafo.csv
     - ms_cafo.csv
     - farm_source.json
     - al_cafo.csv
   - From team RAFI google drive/Data/Infogroup, into data/raw/infogroup add:
     - poultry_plants_x.csv
       - where "x" is every year from 1997 to 2022
     - For the smoke test, create a subfolder data/raw/infogroup/smoke_test and add the file infogroup_2022_small.csv
   - From team RAFI google drive/Data/nets, into data/raw/infogroup add:
     - 2022-NAICS-CODES-6-digit.csv
     - MoveYear2022_RAFI(WithAddresses).txt
     - NAICS2022_RAFI.csv
     - NAICS2022_RAFI.txt
     - NETSData2022_RAFI(WithAddresses).txt
   - From team RAFI google drive, download .env file and place under rafi-poultry directory
     - You will likely have to rename the file to place the "." in front
4. **Run pip install -r pipeline/requirements.txt**
5. **Run pip install -r notebooks/requirements.txt**
6. **Run pip install -e .**
   - This installs the pipeline as a package.
7. **Run main.py**
     - All functions are executed by default. Specify a function name in the command line argument following the --function flag to run that function individually.
     - To enable the smoke test for cleaning Infogroup files, add the flag --smoke_test True to the command line argument.
     - The full command line argument for running the pipeline requires the specification of using either the NETS or Infogroup dataset
     - The command is:
        - python pipeline/main.py --use_nets
        - python pipeline/main.py --use_infogroup
          - Note that the main method to use is --use_nets (In other words, NETS is the preferred dataset)
     - All functions are executed by default. Specify a function name in the command line argument following the --function flag to run that function individually.
     - To enable the smoke test for cleaning Infogroup files, add the flag --smoke_test True to the command line argument.
