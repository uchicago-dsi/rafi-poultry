from distances import haversine
import pandas as pd

# list of states that you want to search within
states = ['IA', 'OK', 'MO', 'OK', 'AL', 'LA', 'MS', 'IL', 'IN', 'OH', 'KY', 'TN', 'AR', 'NC', 'SC', 'GA']

def potential_farms(infogroup_df, counterglow_df, states, max_dist_km, print_bool=True ):
    
    """
        finds potential farms in the infogroup dataset based on the speculative farms
        in the counterglow dataset
        
        Args:
            infogroup_df   (dataframe): 
            counterglow_df (dataframe): 
            states (list): list of states that  you want to specifically look at
            max_dist_km (float): maximum radius distance you want to check within
            print_bool (bool): default true, prints results to terminal
            
        Returns:
            two dataframes: infogroup_trim & counterglow_trim. They are both the same length.
            Each time a match is found, the infogroup match & the counterglow match will append
            to a new, trimmed dataframe
    """
    
    # ruduce dataframe to only consist rows with specified two lettered state
    infogroup_state_df      = infogroup_df[infogroup_df["STATE"] == states]
    counterglow_state_df    = counterglow_df[counterglow_df["State"] == states]
    
    # create two new empty dataframe that we will be adding to when match is found
    infogroup_trim     = pd.DataFrame(columns=infogroup_state_df.columns)
    counterglow_trim   = pd.DataFrame(columns=counterglow_state_df.columns)
    
    counter = 0 # to counter matches, can print to terminal if desired
    for i in range(len(infogroup_state_df)):
        
        infogroup_longitude  = infogroup_state_df.iloc[i]["LONGITUDE"]  # get longitude
        infogroup_latitude   = infogroup_state_df.iloc[i]["LATITUDE"]   # get latitude
        
        for j in range(len(counterglow_state_df)):
            
            counterglow_latitude    = counterglow_state_df.iloc[j]["Lat"]    # get latitude
            counterglow_longitude   = counterglow_state_df.iloc[j]["Lat.1"]  # get longitude
            
            dist_km                 = haversine(infogroup_longitude, infogroup_latitude, 
                                                counterglow_longitude, counterglow_latitude)
            
            if(dist_km <= max_dist_km): # if the distance is <= the max distance set in function
                counter += 1

                # appending the potential match to the new dataframes
                infogroup_trim.loc[len(infogroup_trim.index)]      = infogroup_state_df.iloc[i]
                counterglow_trim.loc[len(counterglow_trim.index)]  = counterglow_state_df.iloc[j]
        
    # change the name of the columns for Latitude & Longitude in each dataframe
    # for Infogroup Dataframe
    infogroup_trim      = infogroup_trim.rename(columns={'LATITUDE': 'LATITUDE 1', 
                                                        'LONGITUDE': 'LONGITUDE 1'})
    counterglow_trim    = counterglow_trim.rename(columns={'Lat' : 'LATITUDE 2',
                                                           'Lat.1': 'LONGITUDE 2'})
    
    # print to terminal to let user know there were matches found, 
    if( (counter !=0) & (print_bool == True) ):
        print(states + ":", "Total number of matches:", counter)
                
    return infogroup_trim, counterglow_trim   


#################################################################################################################

"""
function take a dataframe and a list of states. This function calls the function 'potential_farms'
if the two dataframes returned from 'potential_farms' are NOT empty, they are added to the dictionaries
the keys for the dictionaries are the STATE in the current iteration (in the for loop) and the values
are the dataframes associated with the state. This function will return two dictionaries

This function POTENTIAL_FARMS function
"""

def infogroup_counterglow_dict(sic_df, counterglow_df, list_of_states, radium_km):
    
    """
        finds potential farms in the infogroup dataset based on the speculative farms
        in the counterglow dataset
        
        Args:
            infogroup_df   (dataframe): 
            counterglow_df (dataframe): 
            states (list): list of states that  you want to specifically look at
            max_dist_km (float): maximum radius distance you want to check within
            print_bool (bool): default true, prints results to terminal
            
        Returns:
            two dataframes: infogroup_trim & counterglow_trim. They are both the same length.
            Each time a match is found, the infogroup match & the counterglow match will append
            to a new, trimmed dataframe
    """
    
    
    # empty dictionaries
    igroup_sic_dict = {}
    ctrglow_dict = {}

    # loop through states list and use those as keys to match with the dataframe that was output 
    for state in range(len(list_of_states)):
        infogroup_matches, counterglow_matches = potential_farms(sic_df, counterglow_df, list_of_states[state], radium_km)
        
        # set up key value pairing for both dictionaries
        # only adding to dictionaries if there are matches
        if( (len(infogroup_matches)!=0) & (len(counterglow_matches)!=0) ):
            igroup_sic_dict[list_of_states[state]]    = infogroup_matches
            ctrglow_dict[list_of_states[state]]       = counterglow_matches
            
    return igroup_sic_dict, ctrglow_dict



# function that take a dictionary, the keys are STATES (2 letter) and the VALUES are a dataframe
# containing the locations that are close to a counterglow location, returns a list of all the 
# dataframe that are in the dictionary

def list_of_dataframes(infogroup_dict):
    
    all_df_list = []
    # loop through each key in the dictinary (each state in this case)
    for key in infogroup_dict.keys():
        # drop the duplicate rows and then add the trimmed dataframe to master_list
        all_df_list.append(infogroup_dict[key].drop_duplicates())
        
    return all_df_list


'''
Questions: I have this in my Jupyter nottebook where I convert this list into a
csv file. Still need to do that, but should I make that as a master function?

Questions: make this a script that can be ran straight through

'''