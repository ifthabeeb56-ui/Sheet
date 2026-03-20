import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import date

# 1. പേജ് സെറ്റിംഗ്സ്
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

# കസ്റ്റം ഡിസൈൻ (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #00ff41; font-family: monospace; }
    div[data-testid="stMetric"] { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. ഗൂഗിൾ ഷീറ്റ് കണക്ഷൻ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rFlciVBKJT6AXmi_vJGwApicez4ZaTKQ0rrdUZVJ-aE/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ഷീറ്റിൽ നിന്ന് ഡാറ്റ വായിക്കുന്നു
try:
    df = conn.read(spreadsheet=SHEET_URL, ttl="1m")
    # കോളം പേരുകളിലെ അനാവശ്യ സ്പേസുകൾ നീക്കം ചെയ്യുന്നു (KeyError ഒഴിവാക്കാൻ)
    df.columns = df.columns.str.strip()
except Exception:
    df = pd.DataFrame(columns=['Date', 'Name', 'Buy pr', 'QTY'])

# 3. RSI കണക്കാക്കാനുള്ള ഫംഗ്ഷൻ
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# മാർക്കറ്റ് ഡാറ്റ എടുക്കാനുള്ള ഫ
