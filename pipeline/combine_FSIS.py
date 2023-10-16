import pandas as pd
import numpy as np
import geopandas as gpd
from geopandas.tools import geocode
from geopy.geocoders import MapBox

df_with_address = pd.read_excel("data/raw/MPI_Directory_by_Establishment_Number.xlsx")
df_with_size = pd.read_excel("data/raw/Dataset_Establishment_Demographic_Data.xlsx",skiprows=3)

#only keep the columns we need
df_with_size = df_with_size[['EstNumber','Size', 'Chicken\nSlaughter']]

#merge two dataframes
df_FSIS = pd.merge(df_with_address, df_with_size, on='EstNumber')

df_FSIS["Full Address"] = df_FSIS['Street'] \
+ "," + df_FSIS['City'] \
+ "," + df_FSIS['State'] \
+ " " + df_FSIS["Zip"].astype(str)

#drop unnecessary columns
df_FSIS = df_FSIS.drop(columns=['Street','City','State','Zip'])

# preprocessing: only keep large chicken slaughter
# chicken_slaughter = Yes; Activities include Poultry
df_chicken = df_FSIS[df_FSIS["Activities"].str.contains("Poultry") | (df_FSIS["Chicken\nSlaughter"] == "Yes")]
# keep the large size 
df_large_chickens = df_chicken.loc[df_chicken.Size == "Large"]
# Iterate through the DataFrame and geocode each address


#geocoding
MAPBOX_API = "pk.eyJ1IjoiY2F0YWx5c3R4dSIsImEiOiJjbG5kYndnZjkwM2F6MnRyaTFxYTVqbzBvIn0.ESSjGjKW4wnBkh-TqjpjdA"
access_token = MAPBOX_API

# Initialize the MapBox geocoder with your access token
geolocator = MapBox(api_key=access_token)
df_large_chickens['Latitude'] = None
df_large_chickens['Longitude'] = None


for index, row in df_large_chickens.iterrows():
    location = geolocator.geocode(row['Full Address'])
    if location:
        df_large_chickens.at[index, 'Latitude'] = location.latitude
        df_large_chickens.at[index, 'Longitude'] = location.longitude


#save df_FSIS to raw folder
df_large_chickens.to_csv("data/raw/FSIS_filtered_wiz_location.csv")

