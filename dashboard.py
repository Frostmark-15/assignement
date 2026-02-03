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
required_columns = [
    "Name", "Age", "Address", "Nationality", "Religion",
    "Civil Status", "Email", "Business Permit",
    "Station Name", "Contact Number", "Password"
]

STATION_RACKS = {
    "Station1": ["rack_1", "rack_2", "rack_3", "rack_4"],
    "Station2": ["rack_5", "rack_6", "rack_7", "rack_8"]
}

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
            "databaseURL": "https://hydrotrack-iot-default-rtdb.asia-southeast1.firebasedatabase.app/"
        })
        st.session_state.firebase_initialized = True
        st.success("Firebase initialized ✅")
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")

# ---------- HELPER FUNCTIONS ----------
def get_rack_status(station_name):
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
        st.error(f"Error fetching racks: {e}")
        rack_status = {f"rack_{i}": "Unknown" for i in range(1, 9)}
    return rack_status

def get_request_status(station_name):
    try:
        ref = db.reference(f"stations/{station_name}/request")
        val = ref.get()
        return val if val is not None else False
    except:
        return False

def send_buzzer_signal(station_name):
    try:
        ref = db.reference(f"stations/{station_name}/buzzer")
        ref.set(True)
    except Exception as e:
        st.error(f"Failed to send buzzer signal: {e}")

def reset_request(station_name):
    try:
        ref = db.reference(f"stations/{station_name}/request")
        ref.set(False)
    except:
        pass

def get_user_csv():
    filename = f"{st.session_state.user_name.replace(' ','_')}_stock.csv"
    if not os.path.exists(filename):
        df = pd.DataFrame(columns=["Date", "Station", "Bottles Delivered"])
        df.to_csv(filename, index=False)
    return filename

def record_sale(station_name, bottles):
    filename = get_user_csv()
    df = pd.read_csv(filename)
    df = pd.concat([df, pd.DataFrame([{
        "Date": datetime.date.today(),
        "Station": station_name,
        "Bottles Delivered": bottles
    }])], ignore_index=True)
    df.to_csv(filename, index=False)

def get_sales_summary():
    filename = get_user_csv()
    df = pd.read_csv(filename)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    today = pd.Timestamp.today()
    summary = {}

    for station in ["Station1", "Station2"]:
        station_df = df[df["Station"] == station]
        summary[station] = {
            "daily": station_df[station_df["Date"].dt.date == today.date()]["Bottles Delivered"].sum(),
            "weekly": station_df[station_df["Date"].dt.date >= (today - pd.Timedelta(days=7)).date()]["Bottles Delivered"].sum(),
            "monthly": station_df[station_df["Date"].dt.month == today.month]["Bottles Delivered"].sum(),
            "yearly": station_df[station_df["Date"].dt.year == today.year]["Bottles Delivered"].sum()
        }
    return summary

# ---------- DASHBOARD ----------
def show_dashboard():
    if not st.session_state.logged_in:
        st.warning("Please log in first.")
        return

    st.success(f"Welcome, {st.session_state.user_name}! 👋")

    users_df = pd.read_csv(USER_FILE)
    for col in required_columns:
        if col not in users_df.columns:
            users_df[col] = ""

    user_info = users_df[users_df["Name"] == st.session_state.user_name].iloc[0]

    st_autorefresh(interval=5000, key="auto_refresh")

    map_col, stations_col = st.columns([1.5, 2])

    # ---------- MAP ----------
    with map_col:
        st.subheader("Caraga State University Cabadbaran Campus")
        campus_lat = 9.1172736
        campus_lon = 125.5350530
        map_obj = folium.Map(location=[campus_lat, campus_lon], zoom_start=17)
        folium.Marker([campus_lat, campus_lon], popup="CSU Cabadbaran Campus").add_to(map_obj)
        st_folium(map_obj, width=500, height=450)

    # ---------- STATION INFO ----------
    with stations_col:
        st.markdown("### Station Info")
        st.write(f"**Station Assigned:** {user_info['Station Name']}")
        st.write(f"**Business Permit:** {user_info['Business Permit']}")
        st.write(f"**Email:** {user_info['Email']}")
        st.write(f"**Contact Number:** {user_info['Contact Number']}")
        st.write(f"**Address:** {user_info['Address']}")

        # ---------- STATION 1 ----------
        st.markdown("### Station1 Racks (1–4)")
        racks1 = get_rack_status("Station1")
        station1_empty = 0
        for rack in STATION_RACKS["Station1"]:
            status = racks1.get(rack, "Unknown")
            if status == "Full":
                st.success(f"{rack}: Full")
            elif status == "Empty":
                st.warning(f"{rack}: Empty")
                station1_empty += 1
            else:
                st.info(f"{rack}: Unknown")

        # ---------- STATION 1 REQUEST ----------
        if get_request_status("Station1"):
            st.error("⚠️ Station1: I need stock of Water Gallon, please Delivery")
            reset_request("Station1")

        # ---------- STATION 2 ----------
        st.markdown("### Station2 Racks (5–8)")
        racks2 = get_rack_status("Station2")
        station2_empty = 0
        for rack in STATION_RACKS["Station2"]:
            status = racks2.get(rack, "Unknown")
            if status == "Full":
                st.success(f"{rack}: Full")
            elif status == "Empty":
                st.warning(f"{rack}: Empty")
                station2_empty += 1
            else:
                st.info(f"{rack}: Unknown")

        # ---------- STATION 2 REQUEST ----------
        if get_request_status("Station2"):
            st.error("⚠️ Station2: I need stock of Water Gallon, please Delivery")
            reset_request("Station2")

        # ---------- NOTIFICATION BUTTONS ----------
        st.markdown("---")
        st.markdown("### Delivery Notifications")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Notify Station1 Delivery"):
                if station1_empty > 0:
                    record_sale("Station1", station1_empty)
                    send_buzzer_signal("Station1")
                    st.success(f"Station1: {station1_empty} gallons recorded and buzzer activated!")
                else:
                    st.info("Station1: No empty racks")

        with col2:
            if st.button("Notify Station2 Delivery"):
                if station2_empty > 0:
                    record_sale("Station2", station2_empty)
                    send_buzzer_signal("Station2")
                    st.success(f"Station2: {station2_empty} gallons recorded and buzzer activated!")
                else:
                    st.info("Station2: No empty racks")

        # ---------- SALES SUMMARY ----------
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

        # ---------- STOCK HISTORY ----------
        st.markdown("### Water Stock History")
        df = pd.read_csv(get_user_csv())
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            if not df.empty:
                grouped = df.groupby(["Date", "Station"]).sum().reset_index()
                chart_data = grouped.pivot(index="Date", columns="Station", values="Bottles Delivered").fillna(0)
                st.line_chart(chart_data)
            else:
                st.info("No stock history yet.")

        # ---------- LOGOUT ----------
        st.markdown("---")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.experimental_rerun()
