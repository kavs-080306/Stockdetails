import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 1. YOUR VERCEL URL (Ensure no trailing slash)
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
                st.error("Invalid credentials. Try admin / admin123")
        except Exception as e:
            st.error(f"Could not connect to Backend: {e}")
    st.stop()

# ---------------- BACKEND UTILITIES ---------------- #
def test_backend():
    try:
        resp = requests.get(f"{API_BASE}/stocks", timeout=10)
        if resp.status_code == 200:
            return True, "🟢 Cloud API Live"
        return False, f"🔴 API Error {resp.status_code}"
    except:
        return False, "🔴 Backend Offline (Vercel Sleeping?)"

def get_stocks():
    try:
        resp = requests.get(f"{API_BASE}/stocks", timeout=15)
        if resp.status_code == 200:
            return resp.json().get('stocks', [])
        return []
    except:
        return []

def get_history():
    try:
        resp = requests.get(f"{API_BASE}/history", timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

# ---------------- SIDEBAR & STATUS ---------------- #
backend_ok, backend_status = test_backend()
st.sidebar.title("Settings")
st.sidebar.info(f"User Role: **{st.session_state.role.upper()}**")
st.sidebar.markdown(f"Status: {backend_status}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------------- DASHBOARD ---------------- #
st.title("🏢 Office Stock Manager")

# Fetch Data
with st.spinner('Fetching cloud data...'):
    stocks = get_stocks()
    history = get_history()

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Total Items", len(stocks))
col2.metric("📊 In Stock", len([s for s in stocks if s.get('quantity', 0) > 0]))
col3.metric("📈 Transactions", len(history))

# ---------------- MAIN CONTENT ---------------- #
col_left, col_right = st.columns([2, 1.2])

with col_left:
    st.subheader("📦 Current Stock")
    if not stocks:
        st.info("No items found. Add items using the form below.")
    else:
        df_stocks = pd.DataFrame(stocks)
        search = st.text_input("🔍 Search items...", placeholder="e.g. Pens")
        
        filtered = df_stocks
        if search:
            filtered = df_stocks[df_stocks['name'].str.contains(search, case=False)]
            
        for _, row in filtered.iterrows():
            q = row['quantity']
            bg_color = "#d4edda" if q > 5 else "#fff3cd" if q > 0 else "#f8d7da"
            border = "green" if q > 5 else "orange" if q > 0 else "red"
            
            st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; 
                            border-left: 8px solid {border}; margin-bottom: 10px; color: black;">
                    <h4 style="margin:0;">{row['name']} <small style="color: #444;">({row.get('category', 'General')})</small></h4>
                    <p style="font-size: 20px; font-weight: bold; margin: 5px 0;">Qty: {q}</p>
                </div>
            """, unsafe_allow_html=True)

with col_right:
    st.subheader("📋 Recent History")
    if history:
        df_h = pd.DataFrame(history)
        df_h['date_time'] = pd.to_datetime(df_h['date_time']).dt.strftime('%b %d, %H:%M')
        st.dataframe(df_h[['date_time', 'stock_name', 'quantity', 'person']], height=400, use_container_width=True)
    else:
        st.write("No transactions logged.")

# ---------------- ACTIONS (TABS) ---------------- #
st.markdown("---")
PERSON_LIST = ["Abul", "Balaji", "Vibin"]

# Admin can Add and Remove; User can only Remove
if st.session_state.role == "admin":
    t1, t2 = st.tabs(["➕ Add Stock", "➖ Remove Stock"])
else:
    t2 = st.tabs(["➖ Remove Stock"])[0]
    t1 = None

if t1:
    with t1:
        with st.form("add_stock_form"):
            c1, c2, c3 = st.columns(3)
            item_name = c1.text_input("Item Name")
            item_qty = c2.number_input("Quantity to Add", min_value=1)
            item_cat = c3.selectbox("Category", ["Stationery", "Electronics", "Pantry", "General"])
            
            if st.form_submit_button("Add to Cloud"):
                if not item_name:
                    st.warning("Please enter an item name.")
                else:
                    payload = {
                        "name": item_name, 
                        "quantity": int(item_qty), 
                        "category": item_cat, 
                        "role": st.session_state.role
                    }
                    res = requests.post(f"{API_BASE}/stocks", json=payload, timeout=15)
                    
                    if res.status_code in [200, 201]:
                        st.success(f"Added {item_qty} {item_name}!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {res.json().get('error', 'Unknown Error')}")

with t2:
    with st.form("remove_stock_form"):
        c1, c2, c3 = st.columns(3)
        staff_member = c1.selectbox("Person", PERSON_LIST + ["Other"])
        if staff_member == "Other": 
            staff_member = st.text_input("Enter Name")
        
        # Dropdown of existing stock items
        available_items = [s['name'] for s in stocks] if stocks else ["No items"]
        item_to_remove = c2.selectbox("Select Item", available_items)
        qty_to_remove = c3.number_input("Quantity to Remove", min_value=1)
        
        if st.form_submit_button("Confirm Removal"):
            if not stocks:
                st.error("No items available to remove.")
            else:
                payload = {
                    "name": item_to_remove, 
                    "quantity": int(qty_to_remove), 
                    "person": staff_member, 
                    "role": st.session_state.role
                }
                # Backend route for removal is /api/stocks/remove
                res = requests.post(f"{API_BASE}/stocks/remove", json=payload, timeout=15)
                
                if res.status_code == 200:
                    st.success(f"Successfully removed {qty_to_remove} {item_to_remove}")
                    st.rerun()
                else:
                    error_msg = res.json().get('error', 'Insufficient stock or error')
                    st.error(f"Failed: {error_msg}")
