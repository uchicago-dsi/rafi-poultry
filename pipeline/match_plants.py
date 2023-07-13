import pandas as pd
import numpy as np
import time
from math import radians, cos, sin, asin, sqrt


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r



def loc_match(no_match, pp_2022, threshold):
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
                x = input("confirm location")
                if (x == "yes"):
                    pp_sales.loc[index, "Sales Volume (Location)"] = infogroup["SALES VOLUME (9) - LOCATION"]
                    no_match.loc[index, "Sales Volume (Location)"] = infogroup["SALES VOLUME (9) - LOCATION"]
                    break