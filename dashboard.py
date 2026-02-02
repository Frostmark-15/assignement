import streamlit as st
import pandas as pd
import datetime
import os
from streamlit_folium import st_folium
import folium
import firebase_admin
from firebase_admin import credentials, db
from streamlit_autorefresh import st_autorefresh

# ---------- FILE & DATA CONFIG ----------
USER_FILE = "users.csv"
required_columns = ["Name", "Age", "Address", "Nationality", "Religion",
                    "Civil Status", "Email", "Business Permit", "Station Name",
                    "Contact Number", "Password"]

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "firebase_initialized" not in st.session_state:
    st.session_state.firebase_initialized = False

# ---------- FIREBASE SETUP ----------
if not st.session_state.firebase_initialized:
    try:
        cred = credentials.Certificate("firebase-adminsdk.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://hydrotrack-iot-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
        st.session_state.firebase_initialized = True
        st.success("Firebase initialized ✅")
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")

# ---------- HELPER FUNCTIONS ----------
def get_rack_status(station_name):
    """Fetch rack status from Firebase RTDB"""
    rack_status = {}
    try:
        ref = db.reference(f"stations/{station_name}/racks")
        data = ref.get()
        if data:
            for key, value in data.items():
                rack_status[key] = "Full" if str(value) == "1" else "Empty" if str(value) == "0" else "Unknown"
        else:
            rack_status = {f"rack_{i}": "Unknown" for i in range(1, 9)}
    except Exception as e:
        st.error(f"Error fetching {station_name} racks: {e}")
        rack_status = {f"rack_{i}": "Unknown" for i in range(1, 9)}
    return rack_status

def get_user_csv():
    """Return path to user's CSV for water stock"""
    filename = f"{st.session_state.user_name.replace(' ','_')}_stock.csv"
    if not os.path.exists(filename):
        df = pd.DataFrame(columns=["Date","Station","Bottles Delivered"])
        df.to_csv(filename, index=False)
    return filename

def record_sale(station_name, bottles):
    """Add new sale entry to user's CSV"""
    filename = get_user_csv()
    df = pd.read_csv(filename)
    df = pd.concat([df, pd.DataFrame([{"Date": datetime.date.today(),
                                       "Station": station_name,
                                       "Bottles Delivered": bottles}])], ignore_index=True)
    df.to_csv(filename, index=False)

def get_sales_summary():
    """Return total daily, weekly, monthly, yearly water sales per station"""
    filename = get_user_csv()
    df = pd.read_csv(filename)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        df["Date"] = pd.NaT
    df_valid = df.dropna(subset=["Date"])
    today = pd.Timestamp.today()
    summary = {}
    for station in ["Station1", "Station2"]:
        station_df = df_valid[df_valid["Station"]==station]
        summary[station] = {
            "daily": station_df[station_df["Date"].dt.date==today.date()]["Bottles Delivered"].sum(),
            "weekly": station_df[station_df["Date"].dt.date >= (today - pd.Timedelta(days=7)).date()]["Bottles Delivered"].sum(),
            "monthly": station_df[station_df["Date"].dt.month==today.month]["Bottles Delivered"].sum(),
            "yearly": station_df[station_df["Date"].dt.year==today.year]["Bottles Delivered"].sum()
        }
    return summary

# ---------- DASHBOARD ----------
def show_dashboard():
    if not st.session_state.logged_in:
        st.warning("Please log in first.")
        return

    st.success(f"Welcome, {st.session_state.user_name}! 👋")

    # Load user info
    users_df = pd.read_csv(USER_FILE)
    for col in required_columns:
        if col not in users_df.columns:
            users_df[col] = ""
    user_info = users_df[users_df["Name"] == st.session_state.user_name].iloc[0]
    
    # --- AUTO REFRESH ---
    st_autorefresh(interval=5000, key="auto_refresh")  # Refresh every 5 seconds

    # ---------- LAYOUT ----------
    map_col, stations_col = st.columns([1.5, 2])

    # --- LEFT: Campus Map ---
    with map_col:
        st.subheader("Caraga State University Cabadbaran Campus")
        campus_lat = 9.1172736
        campus_lon = 125.5350530
        map_obj = folium.Map(location=[campus_lat, campus_lon], zoom_start=17)
        folium.Marker(
            [campus_lat, campus_lon],
            popup="CSU Cabadbaran Campus",
            tooltip="Caraga State University - Cabadbaran"
        ).add_to(map_obj)
        st_folium(map_obj, width=500, height=450)

    # --- RIGHT: Stations Info ---
    with stations_col:
        st.markdown("### Station Info")
        st.write(f"**User Station Assigned:** {user_info['Station Name']}")
        st.write(f"**Business Permit:** {user_info['Business Permit']}")
        st.write(f"**Email:** {user_info['Email']}")
        st.write(f"**Contact Number:** {user_info['Contact Number']}")
        st.write(f"**Address:** {user_info['Address']}")

        # --- Station1 Racks ---
        st.markdown("### Station1 Racks")
        racks1 = get_rack_status("Station1")
        station1_empty = 0
        for rack, status in racks1.items():
            if status == "Full":
                st.success(f"{rack}: Full")
            elif status == "Empty":
                st.warning(f"{rack}: Empty")
                station1_empty += 1
            else:
                st.info(f"{rack}: Unknown")

        # --- Station2 Racks ---
        st.markdown("### Station2 Racks")
        racks2 = get_rack_status("Station2")
        station2_empty = 0
        for rack, status in racks2.items():
            if status == "Full":
                st.success(f"{rack}: Full")
            elif status == "Empty":
                st.warning(f"{rack}: Empty")
                station2_empty += 1
            else:
                st.info(f"{rack}: Unknown")

        # ---------- Notifications & Record Sale ----------
        st.markdown("---")
        if st.button(f"Notify Delivery for Both Stations"):
            if station1_empty > 0:
                record_sale("Station1", station1_empty)
                st.success(f"Station1: {station1_empty} bottles marked as delivered!")
            else:
                st.info("Station1: No empty racks")
            if station2_empty > 0:
                record_sale("Station2", station2_empty)
                st.success(f"Station2: {station2_empty} bottles marked as delivered!")
            else:
                st.info("Station2: No empty racks")

        # ---------- Water Sales Summary ----------
        st.markdown("---")
        st.markdown("### Water Gallons Sold Summary")
        summary = get_sales_summary()
        for station, values in summary.items():
            st.markdown(f"**{station}**")
            st.write(f"Daily: {values['daily']} gallons")
            st.write(f"Weekly: {values['weekly']} gallons")
            st.write(f"Monthly: {values['monthly']} gallons")
            st.write(f"Yearly: {values['yearly']} gallons")
            st.markdown("---")

        # ---------- Water Stock History ----------
        st.markdown("### Water Stock History")
        filename = get_user_csv()
        df = pd.read_csv(filename)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df_valid = df.dropna(subset=["Date"])
            if not df_valid.empty:
                df_grouped = df_valid.groupby(["Date","Station"]).sum().reset_index()
                st.line_chart(df_grouped.pivot(index="Date", columns="Station", values="Bottles Delivered").fillna(0))
            else:
                st.info("No water stock history yet.")
        else:
            st.info("No water stock history yet.")

        # ---------- Logout ----------
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.session_state.show_register = False
            st.experimental_rerun()
