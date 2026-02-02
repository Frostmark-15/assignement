import streamlit as st
import pandas as pd
import os
from dashboard import show_dashboard  # import dashboard function

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="HydroTrack", page_icon="💧", layout="wide")

# ---------- STYLING ----------
st.markdown("""
<style>
.title {
    font-size:100px;
    font-weight: bold;
    background: linear-gradient(to right, #00f, #0ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.tagline {
    font-size:30px;
    color: #0077cc;
    font-weight: bold;
}
.box {
    background-color: #f0f8ff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 5px 5px 15px #888888;
}
</style>
""", unsafe_allow_html=True)

# ---------- CSV FILE ----------
FILE_NAME = "users.csv"
required_columns = ["Name", "Age", "Address", "Nationality", "Religion",
                    "Civil Status", "Email", "Business Permit", "Station Name",
                    "Contact Number", "Password"]

# Create CSV if it doesn't exist
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=required_columns)
    df.to_csv(FILE_NAME, index=False)

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_register" not in st.session_state:
    st.session_state.show_register = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "refresh" not in st.session_state:
    st.session_state.refresh = 0  # dummy variable to force refresh

# ---------- MAIN APP ----------
if st.session_state.logged_in:
    show_dashboard()  # show dashboard if logged in
else:
    # Show login page
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown('<div class="title">HYDROTRACK</div>', unsafe_allow_html=True)
        st.markdown('<div class="tagline">When WATER MATTERS, we TRACK IT!</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        st.subheader("Login")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            users_df = pd.read_csv(FILE_NAME)
            for col in required_columns:
                if col not in users_df.columns:
                    users_df[col] = ""
            user = users_df[(users_df["Email"] == email) & (users_df["Password"] == password)]
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_name = user.iloc[0]["Name"]
                st.session_state.refresh += 1  # force refresh
            else:
                st.error("Invalid Email or Password")

        st.markdown("---")

        if st.button("No account? Create Now!"):
            st.session_state.show_register = True

        if st.session_state.show_register:
            st.subheader("Register New Account")
            with st.form(key="register_form"):
                name = st.text_input("Name")
                age = st.number_input("Age", min_value=1, max_value=120)
                address = st.text_input("Address")
                nationality = st.text_input("Nationality")
                religion = st.text_input("Religion")
                civil_status = st.text_input("Civil Status")
                email_reg = st.text_input("Email Address")
                business_permit = st.text_input("Business Permit")
                station_name = st.text_input("Station Name")
                contact_number = st.text_input("Contact Number")
                password_reg = st.text_input("Password", type="password")

                submit = st.form_submit_button("Register")
                if submit:
                    users_df = pd.read_csv(FILE_NAME)
                    for col in required_columns:
                        if col not in users_df.columns:
                            users_df[col] = ""
                    if email_reg in users_df["Email"].values:
                        st.error("Email already exists!")
                    else:
                        new_user = {
                            "Name": name,
                            "Age": age,
                            "Address": address,
                            "Nationality": nationality,
                            "Religion": religion,
                            "Civil Status": civil_status,
                            "Email": email_reg,
                            "Business Permit": business_permit,
                            "Station Name": station_name,
                            "Contact Number": contact_number,
                            "Password": password_reg
                        }
                        users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
                        users_df.to_csv(FILE_NAME, index=False)
                        st.success("Account created successfully! You are now logged in.")

                        st.session_state.logged_in = True
                        st.session_state.user_name = name
                        st.session_state.show_register = False
                        st.session_state.refresh += 1  # force refresh

        st.markdown('</div>', unsafe_allow_html=True)
