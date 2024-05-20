import pandas as pd
import geopandas as gpd
from pathlib import Path
from fuzzywuzzy import fuzz
from tqdm import tqdm


# TODO: Set this in config or something
FSIS_PATH = Path("../data/raw/MPI_Directory_by_Establishment_Name_29_04_24.csv")

PARENT_CORPS = {
    "House of Raeford Farms of LA": "Raeford Farms Louisiana",
    "Mar-Jac Poultry-AL": "MARSHALL DURBIN FOOD CORP",
    "Mar-Jac Poultry-MS": "MARSHALL DURBIN FOOD CORP",
    "Perdue Foods, LLC": "PERDUE FARMS INC",
}

df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
df_fsis = df_fsis.dropna(subset=["activities"])
df_fsis = df_fsis[df_fsis.activities.str.lower().str.contains("poultry slaughter")]
df_fsis = df_fsis[df_fsis["size"] == "Large"]
df_fsis["duns_number"] = df_fsis["duns_number"].str.replace("-", "")

gdf_fsis = gpd.GeoDataFrame(
    df_fsis, geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude), crs=9822
)

gdf_fsis["Matched"] = False

# TODO: set up the NETS files in config, etc.
df_nets = pd.read_csv(
    "../data/raw/nets/NETSData2022_RAFI(WithAddresses).txt",
    sep="\t",
    encoding="latin-1",
    dtype={"DunsNumber": str},
    low_memory=False,
)
df_nets_naics = pd.read_csv(
    "../data/raw/nets/NAICS2022_RAFI.csv",
    dtype={"DunsNumber": str},
    low_memory=False,
)
df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")

gdf_nets = gpd.GeoDataFrame(
    df_nets, geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude), crs=9822
)

gdf_fsis["buffered"] = gdf_fsis.geometry.buffer(1000)

sindex_nets = gdf_nets.sindex

matches = []
no_spatial_match = []
no_string_match = []
no_string_match_multiple = []

for index, row in tqdm(
    gdf_fsis.iterrows(), total=gdf_fsis.shape[0], desc="Spatial matches of FSIS plants"
):
    matched = False
    possible_matches_index = list(sindex_nets.intersection(row["buffered"].bounds))
    possible_matches = gdf_nets.iloc[possible_matches_index]
    spatial_matches = possible_matches[
        possible_matches.geometry.intersects(row["buffered"])
    ]  # [['Company', 'Address', 'City', 'HQDuns']]
    if len(spatial_matches) == 0:
        unmatched_dict = {
            "DUNS": row["duns_number"],
            "FSIS Company": row["establishment_name"],
            "DBAs": row["dbas"],
            "FSIS Address": row["street"],
            "FSIS City": row["city"],
        }
        no_spatial_match.append(unmatched_dict)
        continue

    match_info = []  # Collect information on all potential matches
    spatial_matches_info = []

    for _, match in spatial_matches.iterrows():
        company_match = (
            fuzz.token_sort_ratio(
                row["establishment_name"].upper(), match["Company"].upper()
            )
            > 70
        )
        address_match = (
            fuzz.token_sort_ratio(row["street"].upper(), match["Address"].upper()) > 70
        )
        alt_name_match = False
        if row["establishment_name"] in PARENT_CORPS:
            alt_name_match = (
                fuzz.token_sort_ratio(
                    PARENT_CORPS.get(row["establishment_name"], "").upper(),
                    match["Company"].upper(),
                )
                > 70
            )

        if company_match or address_match or alt_name_match:
            # print("Record matched!")
            extended_row = row.to_dict()
            extended_row.update(
                {
                    "Matched_Company": match["Company"],
                    "Matched_Address": match["Address"],
                    "Matched_City": match["City"],
                    "HQDuns": match["HQDuns"],
                    "HQ Company": match["HQCompany"],
                    "Sales Last Year": match["SalesHere"],
                    "Company_Match_Score": company_match,
                    "Address_Match_Score": address_match,
                }
            )
            matches.append(extended_row)
            matched = True
            break  # TODO: check multiple matches later
        else:
            spatial_matches_info.append(
                {
                    "DUNS": row["duns_number"],
                    "FSIS Company": row["establishment_name"],
                    "DBAs": row["dbas"],
                    "Matched_Company": match["Company"],
                    "FSIS Address": row["street"],
                    "Matched_Address": match["Address"],
                    "FSIS City": row["city"],
                    "Matched_City": match["City"],
                }
            )

    if not matched:
        no_string_match.append(
            {
                "DUNS": row["duns_number"],
                "FSIS Company": row["establishment_name"],
                "DBAs": row["dbas"],
                "FSIS Address": row["street"],
                "FSIS City": row["city"],
                "FSIS State": row["state"],
            }
        )
        no_string_match_multiple.extend(
            spatial_matches_info
        )  # Append as dictionary for uniform format

# Convert to DataFrame for easier review and manipulation
df_matches = pd.DataFrame(matches)
df_no_spatial = pd.DataFrame(no_spatial_match)
df_no_string = pd.DataFrame(no_string_match)
df_no_string_multiple = pd.DataFrame(no_string_match_multiple)

COL_ORDER = [
    "establishment_id",
    "establishment_number",
    "establishment_name",
    "duns_number",
    "street",
    "city",
    "state",
    "zip",
    "Matched_Company",
    "Matched_Address",
    "Matched_City",
    "Company_Match_Score",
    "Address_Match_Score",
    "phone",
    "grant_date",
    "activities",
    "dbas",
    "district",
    "circuit",
    "size",
    "latitude",
    "longitude",
    "county",
    "fips_code",
    "geometry",
    "buffered",
]

df_matches[COL_ORDER].to_csv("matches.csv", index=False)
df_no_spatial.to_csv("no_spatial_match.csv", index=False)
df_no_string.to_csv("no_string_match.csv", index=False)
df_no_string_multiple.to_csv("no_string_match_multiple.csv", index=False)

df_unmatched = pd.concat([df_no_spatial, df_no_string], sort=True)

df_duns = pd.merge(
    df_unmatched, df_nets, left_on="DUNS", right_on="DunsNumber", how="inner"
)
