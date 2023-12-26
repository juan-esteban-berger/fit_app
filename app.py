import warnings
warnings.filterwarnings('ignore')

import os
import numpy as np
import pandas as pd

import hmac
import streamlit as st

import pandas as pd
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

# Now you have the 'fitness.weight' table data in the DataFrame 'df'
# You can preview the DataFrame contents using:
st.write(df_weight)

st.write(df_strength)
