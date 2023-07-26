"""
Script contains functionality to create a dataframe from a file. With a desired SIC Code, the other 
function will trim out any row that does not contain that SIC Code.
"""
import dask.dataframe as dd
import numpy as np
import pandas as pd



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


def dask_sic_matches_df(mst_df, sic_code):
    
    """
        ! DASK METHOD !
        function will filter the master dataframe input that contains everything read in from csv file.
        This will filter the master dataframe to contain only those rows that contain the SIC Code that
        is input into the function. this is intended for dask dataframes (not pandas)
        
        Args:
            mst_df (dataframe): master dataframe resulted from reading in the csv file
            sic_code  (string): SIC Code that the user 
            
        Returns:
            a dataframe that contains only the rows where the input SIC Code is listed for that row (busienss)
    """
    
    # reassure SIC Code is a string    
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


def sic_matches_df(df, sic_code):
    
    """
        ! PANDAS METHOD !
        function will filter the master dataframe input that contains everything read in from csv file.
        This will filter the master dataframe to contain only those rows that contain the SIC Code that
        is input into the function. this is intended for pandas dataframes (not dask)
        
        Args:
            df (dataframe): master dataframe resulted from reading in the csv file
            sic_code  (string): SIC Code that the user 
            
        Returns:
            a dataframe that contains only the rows where the input SIC Code is listed for that row (busienss)
    """
    
    df_sic = pd.DataFrame(columns=df.columns)
    sic_code = str(sic_code)
    
    for i in range(len(df)):
        if (  (df.iloc[i]['SIC CODE'].__contains__(sic_code) ) |
              (df.iloc[i]['SIC CODE 1'].__contains__(sic_code)) |
              (df.iloc[i]['SIC CODE 2'].__contains__(sic_code)) |
              (df.iloc[i]['SIC CODE 3'].__contains__(sic_code)) |
              (df.iloc[i]['SIC CODE 4'].__contains__(sic_code)) |
              (df.iloc[i]['PRIMARY SIC CODE'].__contains__(sic_code))
            ):
            df_sic.loc[len(df_sic.index)] = df.iloc[i]
            
    return df_sic
