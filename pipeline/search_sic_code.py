import dask.dataframe as dd


def to_dataframe(filepath):
    df = dd.read_csv(filepath, dtype=str, encoding='unicode_escape')
    df.columns = df.columns.str.upper() # force all columns to be uppercase
    return df


# function to filter the DataFrame that has everything read in from the master CSV.
# Inputs are the master dataframe and the SIC code of choice. Returns a Dask DataFrame
# that has been filtered to be the lines from Infogroup records that contain the desired
# SIC Code in 1 of 5 different columns

def sic_matches_df(mst_df, sic_code: str):
    
    # reassure SIC Code is a string, sanity check    
    sic_code = str(sic_code)
    
    # this filters checks SIC Code 1 through 4 & Primary SIC Code if they contain desired SIC Code we are searching for
    filtered_df = mst_df[ mst_df['SIC CODE'].str.contains(sic_code, na=False) |
                          mst_df['SIC CODE 1'].str.contains(sic_code, na=False) |
                          mst_df['SIC CODE 2'].str.contains(sic_code, na=False) |
                          mst_df['SIC CODE 3'].str.contains(sic_code, na=False) |
                          mst_df['SIC CODE 4'].str.contains(sic_code, na=False) |
                          mst_df['PRIMARY SIC CODE'].str.contains(sic_code, na=False)
                         ]
    
    result = filtered_df.compute()
            
    return result


## Question: should I create a function to turn it into a csv?
## a script that can just be ran from top to bottm for the entire
## process?
## name of the file? filepath? etc...
    