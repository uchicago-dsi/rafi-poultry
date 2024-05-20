import pandas as pd
import geopandas as gpd
from pathlib import Path
from fuzzywuzzy import fuzz
from tqdm import tqdm


current_dir = Path(__file__).resolve().parent
DATA_DIR = current_dir / "../data/raw/"
# TODO: set filename in config
FSIS_PATH = DATA_DIR / "MPI_Directory_by_Establishment_Name_29_04_24.csv"
NETS_PATH = DATA_DIR / "nets" / "NETSData2022_RAFI(WithAddresses).txt"
NETS_NAICS_PATH = DATA_DIR / "nets" / "NAICS2022_RAFI.csv"


PARENT_CORPS = {
    "House of Raeford Farms of LA": "Raeford Farms Louisiana",
    "Mar-Jac Poultry-AL": "MARSHALL DURBIN FOOD CORP",
    "Mar-Jac Poultry-MS": "MARSHALL DURBIN FOOD CORP",
    "Perdue Foods, LLC": "PERDUE FARMS INC",
}


def clean_fsis(df):
    df = df.dropna(subset=["activities"])
    df = df[df.activities.str.lower().str.contains("poultry slaughter")]
    df = df[df["size"] == "Large"]
    df["duns_number"] = df["duns_number"].str.replace("-", "")
    df["matched"] = False
    return df


def get_spatial_matches(row, gdf_child):
    # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
    # Then check whether they intersect with the buffered geometry
    possible_matches_index = list(gdf_child.sindex.intersection(row["buffered"].bounds))
    possible_matches = gdf_child.iloc[possible_matches_index]
    return possible_matches[possible_matches.geometry.intersects(row["buffered"])]


def get_string_matches(
    row, spatial_matches, company_threshold=0.7, address_threshold=0.7
):
    for _, match in spatial_matches.iterrows():
        company_match = (
            fuzz.token_sort_ratio(
                row["establishment_name"].upper(), match["Company"].upper()
            )
            > company_threshold
        )
        address_match = (
            fuzz.token_sort_ratio(row["street"].upper(), match["Address"].upper())
            > address_threshold
        )
        if row["establishment_name"] in PARENT_CORPS:
            alt_name_match = (
                fuzz.token_sort_ratio(
                    PARENT_CORPS.get(row["establishment_name"], "").upper(),
                    match["Company"].upper(),
                )
                > company_threshold
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


def geospatial_match(
    gdf_parent, gdf_child, address_threshold=0.7, company_threshold=0.7, buffer=1000
):
    # Note: rows are filtered geospatially so can set address and company threshold somewhat low

    gdf_parent["buffered"] = gdf_parent.geometry.buffer(buffer)

    gdf_unmatched = gdf_parent[not gdf_parent.matched]

    matches = []
    no_spatial_match = []
    no_string_match = []
    no_string_match_multiple = []  # TODO: bad name, what is this

    for _, row in tqdm(
        gdf_unmatched.iterrows(),
        total=gdf_unmatched.shape[0],
        desc="Spatial matches of FSIS plants and NETS data",
    ):
        matched = False  # TODO: Do I need this?

        spatial_matches = get_spatial_matches(row, gdf_child)

        if len(spatial_matches) == 0:
            # No NETS record within buffered geometry, FSIS plant is unmatched so save for later and move to next
            no_spatial_match.append(row)
            continue

        # TODO: What?
        match_info = []
        spatial_matches_info = []

        if not matched:
            no_string_match.append(row)
            no_string_match_multiple.extend(
                spatial_matches_info
            )  # Append as dictionary for uniform format


if __name__ == "__main__":
    df_fsis = pd.read_csv(FSIS_PATH, dtype={"duns_number": str})
    df_fsis = clean_fsis(df_fsis)

    df_nets = pd.read_csv(
        NETS_PATH,
        sep="\t",
        encoding="latin-1",
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets_naics = pd.read_csv(
        NETS_NAICS_PATH,
        dtype={"DunsNumber": str},
        low_memory=False,
    )
    df_nets = pd.merge(df_nets, df_nets_naics, on="DunsNumber", how="left")

    # Merge FSIS and NETS data
    df_duns = pd.merge(
        df_fsis, df_nets, left_on="duns_number", right_on="DunsNumber", how="inner"
    )
    df_fsis["matched"] = df_fsis["duns_number"].isin(df_nets["DunsNumber"])

    # Convert to GDF for spatial matching
    gdf_parent = gpd.GeoDataFrame(
        df_fsis,
        geometry=gpd.points_from_xy(df_fsis.longitude, df_fsis.latitude),
        crs=9822,
    )
    gdf_nets = gpd.GeoDataFrame(
        df_nets,
        geometry=gpd.points_from_xy(-df_nets.Longitude, df_nets.Latitude),
        crs=9822,
    )

    gdf_parent["buffered"] = gdf_parent.geometry.buffer(1000)

    sindex_nets = gdf_nets.sindex

    matches = []
    no_spatial_match = []
    no_string_match = []
    no_string_match_multiple = []

    gdf_unmatched = gdf_parent[gdf_parent.matched == False]

    for index, row in tqdm(
        gdf_unmatched.iterrows(),
        total=gdf_unmatched.shape[0],
        desc="Spatial matches of FSIS plants",
    ):
        matched = False
        # For geospatial matching, get all NETS records in the bounding box of the FSIS plant
        # Then check whether they intersect with the buffered geometry
        possible_matches_index = list(sindex_nets.intersection(row["buffered"].bounds))
        possible_matches = gdf_nets.iloc[possible_matches_index]
        spatial_matches = possible_matches[
            possible_matches.geometry.intersects(row["buffered"])
        ]
        if len(spatial_matches) == 0:
            no_spatial_match.append(row)
            continue

        match_info = []
        spatial_matches_info = []

        for _, match in spatial_matches.iterrows():
            company_match = (
                fuzz.token_sort_ratio(
                    row["establishment_name"].upper(), match["Company"].upper()
                )
                > 70
            )
            address_match = (
                fuzz.token_sort_ratio(row["street"].upper(), match["Address"].upper())
                > 70
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
