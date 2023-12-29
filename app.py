import warnings
warnings.filterwarnings('ignore')

import os
import numpy as np
import pandas as pd

import hmac
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import folium
from streamlit_folium import folium_static

import pymongo
import psycopg2

import pytz
from dateutil.parser import parse
from dateutil.tz import tzutc
from datetime import datetime, timedelta, time

st.set_page_config(layout="wide")

#########################################################################
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the passward is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

#########################################################################
# Database connection parameters
db_params = {
    'database': 'postgres',
    'user': st.secrets["pg_username"],
    'password': st.secrets["pg_password"],
    'host': st.secrets["pg_host"],
    'port': st.secrets["pg_port"]
}

# Connect to the PostgreSQL database
conn = psycopg2.connect(**db_params)

# Query to select all rows from the fitness.weight table
query = "SELECT * FROM fitness.weight;"

# Load the data into a pandas DataFrame
df_weight = pd.read_sql(query, conn)

query = "SELECT * FROM fitness.strength;"

df_strength = pd.read_sql(query, conn)

# Close the database connection
conn.close()

#########################################################################
# Streamlit code
st.title('Fitness Dashboard')

# st.write(df_weight)

# Create a line chart for df_weight with 'date' on the x-axis, and 'lbs', 'caloric_intake', 'cardio_calories' on the y-axes
fig_weight = go.Figure()

# Add traces
fig_weight.add_trace(go.Scatter(x=df_weight['date'], y=df_weight['lbs'], name='lbs'))
fig_weight.add_trace(go.Scatter(x=df_weight['date'], y=df_weight['caloric_intake'], name='Caloric Intake', yaxis='y2'))
fig_weight.add_trace(go.Scatter(x=df_weight['date'], y=df_weight['cardio_calories'], name='Cardio Calories', yaxis='y3'))

# Create axis objects
fig_weight.update_layout(
    xaxis=dict(domain=[0.3, 1], showgrid=False),
    yaxis=dict(title='lbs', position=0.1, showgrid=False),
    yaxis2=dict(title='Caloric Intake', overlaying='y', side='left', position=0.2, showgrid=False),
    yaxis3=dict(title='Cardio Calories', overlaying='y', side='right', showgrid=False)
)

# Show the figure
st.plotly_chart(fig_weight, use_container_width=True)

#########################################################################

# st.write(df_weight)

# Create two separate charts with plotly express
fig1 = px.bar(df_weight, x='date', y='run_kms',
              color = df_weight['run_type'],
              title='Run Kms')
fig2 = px.bar(df_weight, x='date', y='run_calories',
                color = df_weight['run_type'],
                title='Run Calories')

# Create two columns in Streamlit page
col1, col2 = st.columns(2)

# Show each figure in respective column
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

# st.write(df_strength)

# Filter data for pull ups and push ups
df_pull_ups = df_strength[df_strength['exercise'] == 'pull ups']
df_push_ups = df_strength[df_strength['exercise'] == 'push ups']

# Make sure 'date' is datetime
df_pull_ups['date'] = pd.to_datetime(df_pull_ups['date'])
df_push_ups['date'] = pd.to_datetime(df_push_ups['date'])

# Create side by side barcharts
col1, col2 = st.columns(2)

# pull ups
with col1:
    fig_pull_ups = px.bar(df_pull_ups, x='date', y='reps', color='variation', title='Pull ups')
    fig_pull_ups.update_xaxes(showgrid=False)
    fig_pull_ups.update_yaxes(showgrid=False)
    st.plotly_chart(fig_pull_ups, use_container_width=True)

# push ups
with col2:
    fig_push_ups = px.bar(df_push_ups, x='date', y='reps', color='variation', title='Push ups')
    fig_push_ups.update_xaxes(showgrid=False)
    fig_push_ups.update_yaxes(showgrid=False)
    st.plotly_chart(fig_push_ups, use_container_width=True)

#########################################################################
# Streamlit input to select timezone
timezones = pytz.all_timezones
selected_tz = st.selectbox('Select your timezone:', timezones, index=timezones.index('America/Guatemala'))
local_tz = pytz.timezone(selected_tz)  # Define local_tz using the selected timezone

# Streamlit date filters
today = datetime.now().date()
yesterday = today - timedelta(days=1)
# Streamlit date filters
date_col1, date_col2 = st.columns(2)
#Start time from midnight
time_start = time(0, 0, 0)
#End time to midnight
time_end = time(23, 59, 59)
with date_col1:
    date_start = st.date_input("Start Date",value=yesterday)
    date_end = st.date_input("End Date",value=today)
with date_col2:
    time_start = st.time_input('Start Time', value=time_start)
    time_end = st.time_input('End Time', value=time_end)
#Streamlit Time filters
start_datetime = datetime.combine(date_start, time_start)
end_datetime = datetime.combine(date_end, time_end)

# Converting datetime to string before sending to mongodb
start_datetime_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")
end_datetime_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%S")

# Connect to MongoDB
client = pymongo.MongoClient(st.secrets["mongo_uri"])
db = client.fitness
collection = db.garmin_connect

# MongoDB datetime query
query = {"session_mesgs.start_time": {"$gte": start_datetime_str, "$lt": end_datetime_str}}

# Retrieve documents satisfying the query
garmin_collection = list(collection.find(query))

# Close the MongoDB connection
client.close()

# Process collection details (the code below assumes all `start_time` are in UTC)
for i in range(len(garmin_collection) -1, -1, -1):

    # Process each session message
    session_messages = garmin_collection[i]["session_mesgs"][0]
    session_messages_utc = session_messages.copy()

    # Parse the start time of the activity and make it timezone aware as UTC
    session_messages['start_time'] = parse(session_messages['start_time']).replace(tzinfo=pytz.utc)
    
    # Now convert the start time from UTC to the selected local timezone
    session_messages['start_time'] = session_messages['start_time'].astimezone(local_tz)
    
    # The activity title should be displayed using the local timezone:
    activity_title = session_messages["start_time"].strftime('%Y-%m-%d %H:%M:%S') + "_" + \
                 session_messages["sport"] + "_" + session_messages["sub_sport"]

    records = pd.DataFrame(garmin_collection[0]["record_mesgs"])

    # Convert 'timestamp' column to datetime objects with timezone
    records['timestamp'] = records['timestamp'].apply(parse)

    # Convert all timestamps in 'records' from UTC to the selected timezone
    records['timestamp'] = records['timestamp'].dt.tz_convert(local_tz)

    st.markdown(f"## {activity_title}")
    # write utc time for reference
    st.write(f"Start Time (UTC): {session_messages_utc['start_time']}")

    col1, col2, col3, col4 = st.columns(4)
    if session_messages["sport"] == "running":
        with col1:
            # Convert Distance to km
            km_distance = session_messages['total_distance'] / 1000
            st.write(f"Distance: {km_distance:.2f}km")
            # Convert Duration from seconds to hh:mm:ss
            time_elapsed = pd.to_timedelta(session_messages['total_elapsed_time'], unit='s')
            # Cleanup the time format (remove days)
            time_elapsed = str(time_elapsed).split()[2]
            # Remove stuff after seconds
            time_elapsed = time_elapsed.split('.')[0]
            st.write(f"Duration: {time_elapsed}")
        with col2:
            # Convert m/s to min/km
            min_per_km = 1000 / session_messages['enhanced_avg_speed'] / 60
            st.write(f"Average Speed: {min_per_km:.2f}min/km")
            st.write(f"Average Cadence: {session_messages['avg_cadence']}rpm")
        with col3:
            st.write(f"Calories: {session_messages['total_calories']} kcal")
            st.write(f"Average Temperature: {session_messages['avg_temperature']}°C")
        with col4:
            st.write(f"Total Ascent: {session_messages['total_ascent']}m")
            st.write(f"Total Descent: {session_messages['total_descent']}m")
   
        # Convert speed from m/s to min/km pace in datetime format (if the value is zero, make the value 0)
        records['enhanced_speed'] = records['enhanced_speed'].apply(lambda x: 0 if x == 0 else 1000 / x / 60)

        # If there are any values in enhanced speed that are 0, null, or not a number (or any other problematic thing) make the value 0.0
        # Create figure with secondary y-axis using Plotly Graph Objects
        fig = go.Figure()
    
        # Add traces for each series
        fig.add_trace(go.Scatter(x=records['timestamp'], y=records['enhanced_speed'], name='Speed'))
        fig.add_trace(go.Scatter(x=records['timestamp'], y=records['enhanced_altitude'], name='Altitude', yaxis='y2'))
        # You can add more traces for other series, assigning them to different axes
    
        # Create axis objects
        fig.update_layout(
            yaxis=dict(title='Speed (min/km)', autorange='reversed'),
            yaxis2=dict(title='Altitude (m)', overlaying='y', side='right')
            # You can add more y-axis configurations for other series here
        )
    
        st.plotly_chart(fig, use_container_width=True)
    
    #########################################################################
    # Create a subset DataFrame where both latitude and longitude position is not null
    records_subset = records.dropna(subset=['position_lat', 'position_long'])
    
    # Convert latitude and longitude from semicircles to degrees
    records_subset['position_lat'] = records_subset['position_lat'] * (180 / 2**31)
    records_subset['position_long'] = records_subset['position_long'] * (180 / 2**31)
    
    # Create a new map object centered at the mean of the latitude and longitude
    center_lat = records_subset['position_lat'].mean()
    center_long = records_subset['position_long'].mean()
    
    # Initialize the map with a more zoomed in value
    zoom_start = 17  # Closer view where most of the route should be visible
    
    m = folium.Map(location=[center_lat, center_long], zoom_start=zoom_start)
    
    # Add the running route using a line to represent the path
    folium.PolyLine(
        list(zip(records_subset['position_lat'], records_subset['position_long'])),
        weight=5,
        color='blue',
        line_opacity=0.8
    ).add_to(m)
    
    # Display the interactive map in the Streamlit application
    # Add scrollbar for width
    folium_width = st.slider(f'Map Width_slider_{i}', 0, 2000, 1000)
    folium_static(m, width=folium_width, height=500)
    # folium_static(m)
