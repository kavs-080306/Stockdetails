import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Backend API URL
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
            }, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                st.session_state.logged_in = True
                st.session_state.role = data['role']
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
        except Exception as e:
            st.error(f"Could not connect to Backend: {e}")
    st.stop()

# ---------------- BACKEND UTILITIES ---------------- #
def test_backend():
    try:
        # Increase timeout for cloud wake-up
        resp = requests.get(f"{API_BASE}/stocks", timeout=10)
        if resp.status_code == 200:
            return True, "🟢 Cloud API Live"
        return False, f"🔴 API Error {resp.status_code}"
    except:
        return False, "🔴 Backend Offline (Check Terminal)"

def add_stock(name, quantity, category):
    try:
        # We send a POST request to the Vercel URL
        response = requests.post(
            f"{API_BASE}/stocks", 
            json={
                "name": name,
                "quantity": int(quantity),
                "category": category,
                "role": st.session_state.role # IMPORTANT: Must send the role!
            },
            timeout=10
        )
        return response.status_code == 201
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return False

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
col4.metric("👥 Staff Active", len(set([h.get('person', 'Unknown') for h in history])))

st.markdown("---")

# Main Content
col_left, col_right = st.columns([2, 1.2])

with col_left:
    st.subheader("📦 Current Stock")
    if not stocks:
        st.info("No items found. Add items in the Add Stock tab.")
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
                            border-left: 8px solid {border}; margin-bottom: 10px;">
                    <h4 style="margin:0;">{row['name']} <small style="color: #666;">({row.get('category', 'General')})</small></h4>
                    <p style="font-size: 20px; font-weight: bold; margin: 5px 0;">Qty: {q}</p>
                </div>
            """, unsafe_allow_html=True)

with col_right:
    st.subheader("📋 Recent History")
    if history:
        df_h = pd.DataFrame(history)
        # Clean dates for display
        df_h['date_time'] = pd.to_datetime(df_h['date_time']).dt.strftime('%b %d, %H:%M')
        st.dataframe(df_h[['date_time', 'stock_name', 'quantity', 'person']], height=400, use_container_width=True)
    else:
        st.write("No transactions logged.")

# ---------------- ACTIONS ---------------- #
st.markdown("---")
PERSON_LIST = ["Abul", "Balaji", "Vibin"]

# Tabs based on permissions
if st.session_state.role == "admin":
    t1, t2 = st.tabs(["➕ Add Stock", "➖ Remove Stock"])
else:
    t2 = st.tabs(["➖ Remove Stock"])[0]
    t1 = None

if t1:
    with t1:
        with st.form("add_stock"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Item Name")
            q = c2.number_input("Quantity", min_value=1)
            cat = c3.selectbox("Category", ["Stationery", "Electronics", "Pantry", "General"])
            if st.form_submit_button("Add to Cloud"):
                res = requests.post(f"{API_BASE}/stocks", json={
                    "name": n, "quantity": q, "category": cat, "role": "admin"
                }, timeout=15)
                if res.status_code == 201 or res.status_code == 200:
                    st.success("Cloud Updated!")
                    st.rerun()

with t2:
    with st.form("remove_stock"):
        c1, c2, c3 = st.columns(3)
        p = c1.selectbox("Person", PERSON_LIST + ["Other"])
        if p == "Other": p = st.text_input("Name")
        
        # Get list of names for dropdown
        s_names = [s['name'] for s in stocks] if stocks else ["No items"]
        item = c2.selectbox("Item", s_names)
        amt = c3.number_input("How many?", min_value=1)
        
        if st.form_submit_button("Confirm Removal"):
            res = requests.post(f"{API_BASE}/stocks/remove", json={
                "name": item, "quantity": amt, "person": p, "role": st.session_state.role
            }, timeout=15)
            if res.status_code == 200:
                st.success(f"Removed {amt} {item}")
                st.rerun()
            else:
                st.error(res.json().get('error', 'Failed'))
