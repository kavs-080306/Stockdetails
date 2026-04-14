import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 1. YOUR VERCEL URL
API_BASE = "https://stockdetails.vercel.app/api"

st.set_page_config(page_title="Office Stock Manager", page_icon="📦", layout="wide")

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

# ---------------- LOGIN PAGE ---------------- #
if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            resp = requests.post(f"{API_BASE}/login", json={
                "username": username,
                "password": password
            }, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                st.session_state.logged_in = True
                st.session_state.role = data['role']
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials.")
        except Exception as e:
            st.error(f"Could not connect to Backend: {e}")
    st.stop()

# ---------------- BACKEND UTILITIES ---------------- #
def get_stocks():
    try:
        resp = requests.get(f"{API_BASE}/stocks", timeout=15)
        return resp.json().get('stocks', []) if resp.status_code == 200 else []
    except:
        return []

def get_history():
    try:
        resp = requests.get(f"{API_BASE}/history", timeout=15)
        return resp.json() if resp.status_code == 200 else []
    except:
        return []

# ---------------- SIDEBAR & RESET ---------------- #
st.sidebar.title("Settings")
st.sidebar.info(f"User Role: **{st.session_state.role.upper() if st.session_state.role else 'NONE'}**")

if st.session_state.role == "admin":
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚠️ Admin Tools")
    confirm_reset = st.sidebar.checkbox("Confirm: Wipe all data")
    if st.sidebar.button("Reset Cloud Database", disabled=not confirm_reset):
        try:
            res = requests.post(f"{API_BASE}/admin/clear", json={"role": "admin"}, timeout=15)
            if res.status_code == 200:
                st.sidebar.success("Database Cleared!")
                st.rerun()
        except:
            st.sidebar.error("Connection Error")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------------- DASHBOARD DATA FETCH ---------------- #
st.title("🏢 Office Stock Manager")

with st.spinner('Fetching cloud data...'):
    stocks = get_stocks()
    history = get_history()

# Initialize DataFrames
df_stocks = pd.DataFrame(columns=['name', 'quantity', 'category'])
df_history = pd.DataFrame(columns=['date_time', 'stock_name', 'action', 'quantity', 'person'])

if history:
    df_history = pd.DataFrame(history)
    df_history['date_time'] = pd.to_datetime(df_history['date_time'], errors='coerce')
    df_history = df_history.dropna(subset=['date_time'])
    if not df_history.empty:
        df_history = df_history.sort_values(by='date_time', ascending=False)
        df_history['display_time'] = df_history['date_time'].dt.strftime('%d %b, %I:%M %p')
        df_history['stock_name'] = df_history['stock_name'].str.title()
        if 'action' not in df_history.columns: df_history['action'] = 'REMOVE'

if stocks:
    df_raw = pd.DataFrame(stocks)
    df_raw['name'] = df_raw['name'].astype(str).str.strip().str.lower()
    df_stocks = df_raw.groupby('name').agg({'quantity': 'sum', 'category': 'first'}).reset_index()

# ---------------- MAIN CONTENT ---------------- #
col_left, col_right = st.columns([1.8, 1.4])

with col_left:
    st.subheader("📦 Current Stock")
    if not df_history.empty:
        csv_data = df_history[['date_time', 'stock_name', 'action', 'quantity', 'person']].to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Report (CSV)", data=csv_data, file_name=f"report_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')

    if df_stocks.empty:
        st.info("No items found.")
    else:
        search = st.text_input("🔍 Search stock...", key="search").strip().lower()
        filtered = df_stocks if not search else df_stocks[df_stocks['name'].str.contains(search)]
        for _, row in filtered.iterrows():
            q = row['quantity']
            bg = "#d4edda" if q > 5 else "#fff3cd" if q > 0 else "#f8d7da"
            st.markdown(f'<div style="background-color: {bg}; padding: 12px; border-radius: 8px; margin-bottom: 8px; color: black; border-left: 5px solid gray;"><b>{row["name"].title()}</b> ({row["category"]}): <b>{q}</b></div>', unsafe_allow_html=True)

with col_right:
    st.subheader("📋 Recent History")
    if not df_history.empty:
        st.dataframe(df_history[['display_time', 'stock_name', 'action', 'quantity', 'person']], height=450, use_container_width=True)
    else:
        st.write("No history available.")

# ---------------- ACTIONS (TABS) ---------------- #
st.markdown("---")
PERSON_LIST = ["Abul", "Balaji", "Vibin"]

if st.session_state.role == "admin":
    t1, t2, t3 = st.tabs(["🔄 Update Stock", "➕ Add New Product", "➖ Remove Stock"])
else:
    t3 = st.tabs(["➖ Remove Stock"])[0]
    t1 = t2 = None

# TAB 1: UPDATE EXISTING STOCK (DROPDOWN)
if t1:
    with t1:
        st.write("Use this to refill items already in the system.")
        with st.form("refill_form"):
            available_names = sorted(df_stocks['name'].tolist()) if not df_stocks.empty else []
            refill_item = st.selectbox("Select Product to Refill", available_names, format_func=lambda x: x.title())
            refill_qty = st.number_input("Quantity to Add", min_value=1)
            if st.form_submit_button("Update Stock"):
                if refill_item:
                    payload = {"name": refill_item, "quantity": int(refill_qty), "role": "admin"}
                    requests.post(f"{API_BASE}/stocks", json=payload)
                    st.rerun()

# TAB 2: ADD BRAND NEW PRODUCT (TEXT INPUT)
if t2:
    with t2:
        st.write("Use this to register a product that doesn't exist yet.")
        with st.form("new_product_form"):
            new_name = st.text_input("New Product Name")
            new_qty = st.number_input("Initial Quantity", min_value=1)
            new_cat = st.selectbox("Category", ["Stationery", "Electronics", "Pantry", "General"])
            if st.form_submit_button("Register New Product"):
                if new_name:
                    payload = {"name": new_name.strip().lower(), "quantity": int(new_qty), "category": new_cat, "role": "admin"}
                    requests.post(f"{API_BASE}/stocks", json=payload)
                    st.rerun()

# TAB 3: REMOVE STOCK
with t3:
    with st.form("remove_form"):
        staff = st.selectbox("Person", PERSON_LIST + ["Other"])
        if staff == "Other": staff = st.text_input("Enter Name")
        available_names = sorted(df_stocks['name'].tolist()) if not df_stocks.empty else []
        target_item = st.selectbox("Select Item", available_names, format_func=lambda x: x.title(), key="remove_select")
        rem_qty = st.number_input("Quantity to Remove", min_value=1)
        if st.form_submit_button("Confirm Removal"):
            if target_item:
                payload = {"name": target_item, "quantity": int(rem_qty), "person": staff, "role": st.session_state.role}
                requests.post(f"{API_BASE}/stocks/remove", json=payload)
                st.rerun()
