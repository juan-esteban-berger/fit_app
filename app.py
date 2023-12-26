import warnings
warnings.filterwarnings('ignore')

import os
import numpy as np
import pandas as pd

import hmac
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import pymongo
import psycopg2

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

# Load the first record from the
# mongodb fitness database garmin_connect collection
client = pymongo.MongoClient(st.secrets["mongo_uri"])
db = client.fitness
collection = db.garmin_connect
df_garmin = list(collection.find())
client.close()

#########################################################################
# Streamlit code
st.title('Fitness Dashboard')

st.write(df_weight)

st.write(df_strength)

session_messages = df_garmin[0]["session_mesgs"][0]

records = pd.DataFrame(df_garmin[0]["record_mesgs"])
# Convert timestamp column from this format 2023-12-25 16:32:21+00:00 to datetime
records['timestamp'] = pd.to_datetime(records['timestamp'])

activity_title = session_messages["start_time"] + "_" + session_messages["sport"] + "_" + session_messages["sub_sport"]

st.markdown(f"## {activity_title}")

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
        st.write(f"Average Speed {min_per_km:.2f}min/km")
        st.write(f"Average Cadence: {session_messages['avg_cadence']}rpm")
    with col3:
        st.write(f"Calories {session_messages['total_calories']} kcal")
        st.write(f"Average Temperature {session_messages['avg_temperature']}°C")
    with col4:
        st.write(f"Total Ascent {session_messages['total_ascent']}m")
        st.write(f"Total Descent {session_messages['total_descent']}m")

    # Convert speed from m/s to min/km pace in datetime format
    records['enhanced_speed'] = 1000 / records['enhanced_speed'] / 60
    records['enhanced_speed'] = pd.to_datetime(records['enhanced_speed'], unit='h')

    # Create figure with secondary y-axis using Plotly Graph Objects
    fig = go.Figure()

    # Add traces for each series
    fig.add_trace(go.Scatter(x=records['timestamp'], y=records['enhanced_speed'], name='Speed'))
    fig.add_trace(go.Scatter(x=records['timestamp'], y=records['enhanced_altitude'], name='Altitude', yaxis='y2'))
    # You can add more traces for other series, assigning them to different axes

    # Create axis objects
    fig.update_layout(
        yaxis=dict(title='Speed (min/km)'),
        yaxis2=dict(title='Altitude (m)', overlaying='y', side='right')
        # You can add more y-axis configurations for other series here
    )

    st.plotly_chart(fig, use_container_width=True)


import folium
from streamlit_folium import folium_static
import streamlit as st
import pandas as pd

# Assuming 'records' DataFrame already exists and contains the running data
# including 'position_lat' and 'position_long' in semicircles

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
folium_static(m)
