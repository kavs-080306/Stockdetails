import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://localhost:5001/api"

st.set_page_config(page_title="Stock History", page_icon="📋", layout="wide")
st.title("📋 **Stocks Given History**")
st.caption("👥 Complete log: Who took what + when | Auto-refreshes")

@st.cache_data(ttl=10)
def get_history():
    try:
        resp = requests.get(f"{API_BASE}/history")
        return resp.json() if resp.status_code == 200 else []
    except:
        return []

history = get_history()

if not history:
    st.info("📝 **No transactions yet!** ➕ Add stock or ➖ take out to see history.")
    st.balloons()
else:
    df = pd.DataFrame(history)
    
    # 🔍 Filters (Top row)
    col1, col2, col3 = st.columns(3)
    with col1:
        person_filter = st.selectbox("👤 Person:", ['All'] + sorted(df['person'].unique()))
    with col2:
        action_filter = st.selectbox("🔄 Action:", ['All'] + df['action'].unique())
    with col3:
        st.empty()
    
    # Filter data
    df_filtered = df[
        (df['person'] == person_filter) | (person_filter == 'All')
    ].copy()
    
    if action_filter != 'All':
        df_filtered = df_filtered[df_filtered['action'] == action_filter]
    
    # 📊 Metrics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Total", len(df_filtered))
    col2.metric("➕ Added", len(df_filtered[df_filtered['action'] == 'ADD']))
    col3.metric("➖ Removed", len(df_filtered[df_filtered['action'] == 'REMOVE']))
    col4.metric("👥 People", len(df_filtered['person'].unique())-1)
    
    st.markdown("---")
    
    # 📋 Full History Table
    st.subheader("📋 **Transaction History**")
    
    df_display = df_filtered.copy()
    df_display['date_time'] = pd.to_datetime(df_display['date_time']).dt.strftime('%d/%m %H:%M')
    df_display = df_display.sort_values('date_time', ascending=False)
    
    st.dataframe(
        df_display[['date_time', 'stock_name', 'quantity', 'person', 'action']],
        column_config={
            "date_time": "Date & Time",
            "stock_name": "📦 Item", 
            "quantity": st.column_config.NumberColumn("Qty", format="%.0f"),
            "person": st.column_config.SelectboxColumn("👤 Person"),
            "action": st.column_config.SelectboxColumn("🔄 Action")
        },
        use_container_width=True,
        hide_index=True
    )
    
    # 🔥 Latest 5 transactions
    st.markdown("---")
    st.subheader("🔥 **Latest 5 Transactions**")
    recent = df_display.head(5)
    
    for _, row in recent.iterrows():
        action_emoji = "➕" if row['action'] == 'ADD' else "➖"
        color = "🟢" if row['action'] == 'ADD' else "🔴"
        st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin: 5px 0;">
                **{action_emoji} {row['quantity']}** units **{row['stock_name']}** 
                {'' if row['action'] == 'ADD' else 'given to'} **{row['person']}**
                <span style="color: gray; font-size: 0.9em;">{row['date_time']}</span>
            </div>
        """, unsafe_allow_html=True)
