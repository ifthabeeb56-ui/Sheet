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

# 3. RSI Calculation Function (Improved)
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0)

# 4. Market Data Fetching with Caching
@st.cache_data(ttl=300)  # 5 മിനിറ്റ് ഡാറ്റ സേവ് ചെയ്തു വെക്കും
def get_market_data(symbols):
    analysis = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            # RSI കൃത്യമാകാൻ 3 മാസത്തെ ഡാറ്റ എടുക്കുന്നു
            hist = ticker.history(period="3mo")
            if not hist.empty and len(hist) > 14:
                current_price = hist['Close'].iloc[-1]
                rsi_vals = calculate_rsi(hist['Close'])
                current_rsi = rsi_vals.iloc[-1]
                analysis[sym] = {"LTP": round(current_price, 2), "RSI": round(current_rsi, 2)}
            else:
                analysis[sym] = {"LTP": 0, "RSI": 0}
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0}
    return analysis

# 5. Styling Function
def color_pnl(val):
    color = 'red' if val < 0 else 'green'
    return f'color: {color}'

# 6. Main Display
st.title("📊 NSE Portfolio & RSI Tracker")

try:
    df = conn.read(spreadsheet=SHEET_URL, ttl="1m")
    df.columns = df.columns.str.strip()
    
    required = ['Name', 'Buy pr', 'QTY']
    if not df.empty and all(col in df.columns for col in required):
        
        # Data Cleaning
        df['Buy pr'] = pd.to_numeric(df['Buy pr'], errors='coerce')
        df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce')
        
        with st.spinner('Updating Market Prices...'):
            live = get_market_data(df['Name'].unique().tolist())
            df['LTP'] = df['Name'].map(lambda x: live.get(x, {}).get('LTP', 0))
            df['RSI'] = df['Name'].map(lambda x: live.get(x, {}).get('RSI', 0))
            
            # Calculations
            df['Invested'] = df['Buy pr'] * df['QTY']
            df['Current Value'] = df['LTP'] * df['QTY']
            df['P&L'] = df['Current Value'] - df['Invested']
            df['Change %'] = ((df['LTP'] - df['Buy pr']) / df['Buy pr']) * 100

        # Metrics Summary
        m1, m2, m3 = st.columns(3)
        total_pnl = df['P&L'].sum()
        m1.metric("Total Portfolio Value", f"₹ {df['Current Value'].sum():,.0f}")
        m2.metric("Total P&L", f"₹ {total_pnl:,.0f}", delta=f"{total_pnl:,.0f}")
        m3.metric("Stock Count", len(df))

        # Styled Table
        styled_df = df.style.applymap(color_pnl, subset=['P&L', 'Change %']) \
                           .format({'LTP': "{:.2f}", 'RSI': "{:.1f}", 'Change %': "{:.2f}%"})
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    else:
        st.warning("ഷീറ്റിലെ കോളങ്ങൾ പരിശോധിക്കുക (Name, Buy pr, QTY എന്നിവ നിർബന്ധമാണ്).")

except Exception as e:
    st.error(f"Error: {e}")

# 7. Sidebar Add Form
with st.sidebar:
    st.header("➕ Add New Stock")
    with st.form("add_stock_form"):
        name = st.text_input("Symbol (eg: RELIANCE)").upper()
        qty = st.number_input("Quantity", min_value=1, step=1)
        pr = st.number_input("Buy Price", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Add to Portfolio"):
            if name and pr > 0:
                new_data = pd.DataFrame([{"Date": date.today().strftime("%d/%m/%y"), 
                                          "Name": name, "Buy pr": pr, "QTY": qty}])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success(f"{name} സേവ് ചെയ്തു!")
                st.rerun()
            else:
                st.error("വിവരങ്ങൾ കൃത്യമായി നൽകുക!")
