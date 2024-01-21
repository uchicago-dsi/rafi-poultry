# assign session: didn't find why it's necessary here. 
# fips code: should county also be included?
# SIC change

# After installation of streamlit, type in terminal: streamlit run stream.py and view in chrome
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# read in data
df = pd.read_csv('auction_info.csv')
# filter data by state and sic code
def get_subset(df, condition_sic, condition_state):
    if condition_state == 'All states':
        df_new = df[df['SICDescription'].isin(condition_sic)]
    else: 
        df_new = df[(df['State'] == condition_state) & (df['SICDescription'].isin(condition_sic))]

    return df_new

## Functions
# revnue and count
def calculate_revenue(df):
    # Get revenue and count
    revenue = []
    auction_count = []
    for i in range(1990,2023):
        sales = "Sales"+str(i)[2:4]
        count = 'NAICS'+str(i)[2:4]
        revenue.append(round(df[sales].sum()/1000000,2))
        auction_count.append(df[count].count())
    # Create a new dataframe of time series data
    df_new = pd.DataFrame({
        'Year': range(1990, 2023),
        'Revenue(Millions)': revenue,
        'Revenue/Auction(Thousands)': [round(a / b * 1000, 2) for a, b in zip(revenue, auction_count)],
        'Count': auction_count
    })
    return df_new
# revenue plot
def revenue_plot(df):
    fig, ax1 = plt.subplots()

    ax1.plot(df['Year'], df['Revenue(Millions)'], 'g-')  # 'g-' is for green solid line
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Total Revenue(Millions)', color='g')

    ax2 = ax1.twinx()  
    ax2.plot(df['Year'], df['Revenue/Auction(Thousands)'], 'b-')  
    ax2.set_ylabel('Revenue/Auction(Thousands)', color='b')
    plt.title("Revenue of auction houses over the years")
    return plt
# 

## Create the app
sics = list(set(df['SICDescription']))
states = ['All states'] + list(set(df['State']))

st.set_page_config(layout="wide") # whole page config set as fullscreen

with st.sidebar:
    st.title('RAFI Companies Analysis')
    st.subheader('Count, revenues and geolocation', divider='rainbow')
    st.text("")
    # check for sic
    sic_options = st.multiselect(
        'Select SIC types', 
        sics,
        'Hogs')
    sic_all = st.checkbox('View all SIC types')
    # check for states
    state_option = st.selectbox(
    'Select a state', 
    states)

    if sic_all:
        df2 = get_subset(df, sics, state_option) # select all sic types
        df2 = calculate_revenue(df2) 
    else: 
        df2 = get_subset(df, sic_options, state_option) # allows for multiple sic types
        df2 = calculate_revenue(df2)

    # View original data
        with st.expander("View data for this filter"):
            dt = st.dataframe(df2) # used to check data

# layout: 2*2 grids
c1, c2 = st.columns(2, gap="large")
c3, c4 = st.columns(2, gap="large") 

with c1:
    plot = st.pyplot(revenue_plot(df2))
with c2:
    plot2 = st.pyplot(revenue_plot(df2)) # TB replaced
with c3:
    plot = st.pyplot(revenue_plot(df2)) # TB replaced
with c4:
    plot2 = st.pyplot(revenue_plot(df2)) # TB replaced
