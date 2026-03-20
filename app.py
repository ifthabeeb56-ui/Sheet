import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import date

# 1. Page Config
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

# 2. Connection
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rFlciVBKJT6AXmi_vJGwApicez4ZaTKQ0rrdUZVJ-aE/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Data Loading
try:
    # ഷീറ്റിൽ നിന്ന് ഡാറ്റ വായിക്കുന്നു
    df = conn.read(spreadsheet=SHEET_URL, ttl="1m")
    # കോളം പേരുകളിലെ സ്പേസ് ഒഴിവാക്കുന്നു
    df.columns = df.columns.str.strip()
    
    # --- ഡീബഗ്ഗിംഗ് സെക്ഷൻ (ഇത് താൽക്കാലികമാണ്) ---
    if df.empty:
        st.error("ഗൂഗിൾ ഷീറ്റിൽ ഡാറ്റയൊന്നും കണ്ടെത്തിയില്ല!")
    else:
        st.sidebar.success(f"ഷീറ്റ് കണക്ട് ആയി! {len(df)} വരികൾ കണ്ടെത്തി.")
except Exception as e:
    st.error(f"കണക്ഷൻ എറർ: {e}")
    df = pd.DataFrame()

# 4. RSI & Market Data Functions
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_data(symbols):
    analysis = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            hist = ticker.history(period="1mo")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                rsi_vals = calculate_rsi(hist['Close'])
                current_rsi = rsi_vals.iloc[-1]
                analysis[sym] = {"LTP": current_price, "RSI": current_rsi}
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0}
    return analysis

# 5. Main Display
st.title("📊 NSE Portfolio & RSI Tracker")

# ഷീറ്റിലെ ഹെഡിംഗുകൾ പരിശോധിക്കുന്നു
required = ['Name', 'Buy pr', 'QTY']
if not df.empty and all(col in df.columns for col in required):
    
    # സംഖ്യകളിലേക്ക് മാറ്റുന്നു
    df['Buy pr'] = pd.to_numeric(df['Buy pr'], errors='coerce')
    df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce')
    
    with st.spinner('Updating Market Prices...'):
        live = get_market_data(df['Name'].tolist())
        df['LTP'] = df['Name'].map(lambda x: live.get(x, {}).get('LTP', 0))
        df['RSI'] = df['Name'].map(lambda x: live.get(x, {}).get('RSI', 0))
        
        # കണക്കുകൂട്ടലുകൾ
        df['P&L'] = (df['LTP'] - df['Buy pr']) * df['QTY']
        df['Change %'] = ((df['LTP'] - df['Buy pr']) / df['Buy pr']) * 100

    # മെട്രിക്സ്
    c1, c2 = st.columns(2)
    c1.metric("Total P&L", f"₹ {df['P&L'].sum():,.0f}")
    c2.metric("Stocks", len(df))

    # ടേബിൾ
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("കാത്തിരിക്കൂ... ഷീറ്റിലെ കോളം പേരുകൾ ശരിയാണെന്ന് ഉറപ്പാക്കുക (Name, Buy pr, QTY).")
    # കോളം പേരുകൾ കാണിക്കുന്നു (പ്രശ്നം കണ്ടെത്താൻ)
    if not df.empty:
        st.write("നിങ്ങളുടെ ഷീറ്റിലുള്ള കോളങ്ങൾ ഇവയാണ്:", df.columns.tolist())

# 6. Sidebar Add
with st.sidebar:
    st.header("Add Stock")
    with st.form("add"):
        name = st.text_input("Symbol (eg: SBIN)")
        qty = st.number_input("Qty", min_value=1)
        pr = st.number_input("Price", min_value=0.0)
        if st.form_submit_button("Save"):
            new = pd.DataFrame([{"Date": date.today().strftime("%d/%m/%y"), "Name": name.upper(), "Buy pr": pr, "QTY": qty}])
            updated = pd.concat([df, new], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, data=updated)
            st.success("സേവ് ചെയ്തു!")
            st.rerun()
