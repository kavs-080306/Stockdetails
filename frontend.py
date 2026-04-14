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
st.sidebar.info(f"User: **{st.session_state.role.upper() if st.session_state.role else 'NONE'}**")

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

# --- INITIALIZE DATAFRAMES (Robust Version) ---
df_stocks = pd.DataFrame(columns=['name', 'quantity', 'category'])
df_history = pd.DataFrame(columns=['date_time', 'stock_name', 'action', 'quantity', 'person'])

if history:
    df_history = pd.DataFrame(history)
    # Robust date conversion
    df_history['date_time'] = pd.to_datetime(df_history['date_time'], errors='coerce')
    df_history = df_history.dropna(subset=['date_time'])
    
    if not df_history.empty:
        df_history = df_history.sort_values(by='date_time', ascending=False)
        df_history['display_time'] = df_history['date_time'].dt.strftime('%d %b, %I:%M %p')
        df_history['stock_name'] = df_history['stock_name'].str.title()
        # Default action to REMOVE if missing from old data
        if 'action' not in df_history.columns:
            df_history['action'] = 'REMOVE'

# ---------------- MAIN CONTENT ---------------- #
col_left, col_right = st.columns([2, 1.3])

with col_left:
    st.subheader("📦 Current Stock")
    
    if not df_history.empty:
        # Exporting full history including ADD/REMOVE actions
        csv_data = df_history[['date_time', 'stock_name', 'action', 'quantity', 'person']].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Transaction Report (CSV)",
            data=csv_data,
            file_name=f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime='text/csv',
        )

    if not stocks:
        st.info("No items found. Database is empty.")
    else:
        df_raw = pd.DataFrame(stocks)
        df_raw['name'] = df_raw['name'].astype(str).str.strip().str.lower()
        df_stocks = df_raw.groupby('name').agg({'quantity': 'sum', 'category': 'first'}).reset_index()

        search = st.text_input("🔍 Search items...", placeholder="e.g. Battery").strip().lower()
        filtered = df_stocks
        if search:
            filtered = df_stocks[df_stocks['name'].str.contains(search)]
            
        for _, row in filtered.iterrows():
            q = row['quantity']
            display_name = row['name'].title()
            bg_color = "#d4edda" if q > 5 else "#fff3cd" if q > 0 else "#f8d7da"
            border = "green" if q > 5 else "orange" if q > 0 else "red"
            
            st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; 
                            border-left: 8px solid {border}; margin-bottom: 10px; color: black;">
                    <div style="display: flex; justify-content: space-between;">
                        <h4 style="margin:0;">{display_name} <small style="color: #444;">({row['category']})</small></h4>
                        <span style="font-size: 1.2em; font-weight: bold;">{q}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

with col_right:
    st.subheader("📋 Recent Transactions")
    if not df_history.empty:
        # Added 'action' column to the view
        st.dataframe(
            df_history[['display_time', 'stock_name', 'action', 'quantity', 'person']], 
            height=500, 
            use_container_width=True,
            column_config={
                "display_time": "Time (IST)",
                "stock_name": "Product",
                "action": "Action",
                "quantity": "Qty",
                "person": "User/Staff"
            }
        )
    else:
        st.write("No history available.")

# ---------------- ACTIONS (TABS) ---------------- #
st.markdown("---")
PERSON_LIST = ["Abul", "Balaji", "Vibin"]

if st.session_state.role == "admin":
    t1, t2 = st.tabs(["➕ Add Stock", "➖ Remove Stock"])
else:
    # Users only see the Remove tab
    t2 = st.tabs(["➖ Remove Stock"])[0]
    t1 = None

if t1:
    with t1:
        with st.form("add_stock_form"):
            c1, c2, c3 = st.columns(3)
            new_item_name = c1.text_input("Item Name")
            new_item_qty = c2.number_input("Quantity to Add", min_value=1)
            new_item_cat = c3.selectbox("Category", ["Office supplies", "Electronics", "General"])
            
            if st.form_submit_button("Add to Cloud"):
                if new_item_name:
                    payload = {
                        "name": new_item_name.strip().lower(), 
                        "quantity": int(new_item_qty), 
                        "category": new_item_cat, 
                        "role": st.session_state.role
                    }
                    requests.post(f"{API_BASE}/stocks", json=payload, timeout=15)
                    st.rerun()

with t2:
    with st.form("remove_stock_form"):
        c1, c2, c3 = st.columns(3)
        staff = c1.selectbox("Person", PERSON_LIST + ["Other"])
        if staff == "Other": staff = st.text_input("Enter Name")
        
        available_names = sorted(df_stocks['name'].tolist()) if not df_stocks.empty else []
        target_item = c2.selectbox("Select Item", available_names, format_func=lambda x: x.title())
        remove_qty = c3.number_input("Quantity to Remove", min_value=1)
        
        if st.form_submit_button("Confirm Removal"):
            if target_item:
                payload = {
                    "name": target_item, 
                    "quantity": int(remove_qty), 
                    "person": staff, 
                    "role": st.session_state.role
                }
                res = requests.post(f"{API_BASE}/stocks/remove", json=payload, timeout=15)
                if res.status_code == 200:
                    st.rerun()
                else:
                    st.error(res.json().get('error', 'Error removing stock'))
