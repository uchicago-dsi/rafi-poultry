"""
Script contains functionality to create a dataframe from a file. With a desired SIC Code, the other 
function will trim out any row that does not contain that SIC Code.
"""
import dask.dataframe as dd



def to_dataframe(filepath):
    """
        creates dataframe from a file
        
        Args:
            filepath (string): filepath of desired file
        
        Returns:
            dataframe in Dask format
    """
    
    # create a dask dataframe
    df = dd.read_csv(filepath, dtype=str, encoding='unicode_escape')
    
    # force all columns to be uppercase
    df.columns = df.columns.str.upper() 
    
    return df


def sic_matches_df(mst_df, sic_code: str):
    
    """
        located SIC Code patches between a master dataframe and a specific SIC Code
        
        Args:
            mst_df (dataframe): master dataframe from import CSV
            sic_code (string): desired SIC Code to search for
            
        Returns:
            a dataframe containing only the row that contain the desired SIC Code
    """
    
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
    
    result = filtered_df.compute() # dask compute the df
            
    return result
