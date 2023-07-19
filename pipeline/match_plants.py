import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
import time
from distances import haversine


def address_match(infogroup_2022_path, fsis_path):
    df_filtered = pd.read_csv(infogroup_2022_path)
    df_filtered["Full Address"] = df_filtered["ADDRESS LINE 1"] + ", " + df_filtered["CITY"] + ", " + df_filtered["STATE"] + " " + df_filtered["ZIPCODE"].astype(int).astype(str)
    df_filtered["Full Address"] = df_filtered["Full Address"].astype(str)
    
    df_fsis = pd.read_csv(fsis_path, index_col=0)
    df_poultry = df_fsis[df_fsis["Animals Processed"].str.contains("Chicken")].copy()
    df_poultry["Sales Volume (Location)"] = np.NaN
    df_match = pd.DataFrame()
    df_match["Sales Volume (Location)"] = np.NaN

    plants_to_update = {}
    for i, fsis in df_poultry.iterrows():
        fsis_address = fsis["Full Address"].lower()
        for k, infogroup in df_filtered.iterrows():
            infogroup_address = infogroup["Full Address"].lower()
            if fuzz.token_sort_ratio(infogroup_address, fsis_address) > 75:
                print(f"Found a match at index {k}")
                print(infogroup_address)
                print(fsis_address)
                df_poultry.loc[i, "Sales Volume (Location)"] = infogroup['SALES VOLUME (9) - LOCATION']
                break

    return df_poultry

def loc_match(no_match, pp_2022, pp_sales, threshold):
    no_match_nulls = no_match[no_match["Sales Volume (Location)"].isna()]
    for index, row in no_match_nulls.iterrows():
        target_point = (row["latitude"], row["longitude"])
        for j, infogroup in pp_2022.iterrows():
            candidate_point = infogroup["LATITUDE"], infogroup["LONGITUDE"]
            distance = haversine(target_point[1], target_point[0], candidate_point[1], candidate_point[0])
            if distance <= threshold:
                print("current point: " + str(target_point) + "; match from pp22: " + str(candidate_point))
                print("current company: " + row["Parent Corporation"] + ", " + row["Establishment Name"] + 
                      "; matched: parent ABI (" + str(infogroup["PARENT NUMBER"]) + ") " + infogroup["COMPANY"])
                time.sleep(2)
                x = input("confirm location (type yes if match): ")
                if (x == "yes"):
                    pp_sales.loc[index, "Sales Volume (Location)"] = infogroup["SALES VOLUME (9) - LOCATION"]
                    break
    return pp_2022, pp_sales

def fill_remaining_nulls(pp_sales):
    median = pp_sales.groupby(['Parent Corporation'])['Sales Volume (Location)'].median().reset_index()
    median_sales = pp_sales["Sales Volume (Location)"].median()
    
    median["Sales Volume (Location)"] = median["Sales Volume (Location)"].fillna(median_sales)
    median["Sales Volume (Location)"] = median["Sales Volume (Location)"].replace(0, median_sales)

    dict1 = dict(zip(median["Parent Corporation"], median["Sales Volume (Location)"]))

    pp_sales_updated = pp_sales.copy()

    for index, row in pp_sales_updated.iterrows():
        if np.isnan(row["Sales Volume (Location)"]):
            parent = row["Parent Corporation"]
            pp_sales_updated.loc[index, "Sales Volume (Location)"] = dict1[parent]

    return pp_sales_updated

def save_all_matches(infogroup_2022_path, fsis_path, threshold):
    address_matches = address_match(infogroup_2022_path, fsis_path)
    no_match = address_matches[address_matches["Sales Volume (Location)"].isna()]

    pp_2022 = pd.read_csv(infogroup_2022_path)
    pp_2022, pp_sales = loc_match(no_match, pp_2022, address_matches, threshold)

    pp_sales_updated = fill_remaining_nulls(pp_sales)
    pp_sales_updated.to_csv("../data/clean/cleaned_matched_plants.csv")

if __name__ == "__main__":
    save_all_matches("../data/clean/poultry_plants_2022.csv", "../data/raw/fsis-processors-with-location.csv", 5)