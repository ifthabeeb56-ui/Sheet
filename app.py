import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf

# 1. Page Config & CSS (Professional Look)
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #00ff41; font-family: monospace; }
    .stDataFrame { margin: auto; }
    </style>
    """, unsafe_allow_html=True)

# 2. Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="1m")

# 3. Manual RSI Calculation (No pandas-ta required)
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stock_analysis(symbols, rsi_period):
    analysis = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            hist = ticker.history(period="1mo")
            if not hist.empty:
                # RSI കണക്കാക്കുന്നു
                rsi_values = calculate_rsi(hist['Close'], window=rsi_period)
                current_rsi = rsi_values.iloc[-1]
                current_price = hist['Close'].iloc[-1]
                
                # Signal Logic
                if current_rsi < 30: signal = "🟢 BUY"
                elif current_rsi > 70: signal = "🔴 SELL"
                else: signal = "⚪ HOLD"
                
                analysis[sym] = {"LTP": current_price, "RSI": current_rsi, "Signal": signal}
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0, "Signal": "N/A"}
    return analysis

# 4. Horizontal Align Center
left, mid, right = st.columns([1, 10, 1])

with mid:
    st.title("📊 NSE Portfolio Tracker")
    
    if not df.empty and 'Stock' in df.columns:
        with st.spinner('Updating Live Data...'):
            results = get_stock_analysis(df['Stock'].tolist(), 14)
            
            df['LTP'] = df['Stock'].map(lambda x: results.get(x, {}).get('LTP', 0))
            df['RSI'] = df['Stock'].map(lambda x: results.get(x, {}).get('RSI', 0))
            df['Signal'] = df['Stock'].map(lambda x: results.get(x, {}).get('Signal', 'N/A'))
            
            df['P&L'] = (df['LTP'] - df['Buy Price']) * df['Qty']
            df['Change %'] = ((df['LTP'] - df['Buy Price']) / df['Buy Price']) * 100

        # Metrics Display
        total_pl = df['P&L'].sum()
        st.metric("Total P&L", f"₹ {total_pl:,.2f}", f"{total_pl:,.2f}")

        # 5. Table Formatting (No extra decimals & Centered)
        st.subheader("Live Insights")
        st.dataframe(
            df.style.format({
                "Buy Price": "{:.0f}",
                "LTP": "{:.0f}",
                "P&L": "{:.0f}",
                "Change %": "{:.2f}%",
                "RSI": "{:.0f}",
                "Qty": "{:.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Portfolio empty. Add stocks from sidebar.")

# 6. Sidebar for Auto-Save
with st.sidebar:
    st.subheader("Add Stock")
    with st.form("add_form", clear_on_submit=True):
        s = st.text_input("Symbol")
        q = st.number_input("Qty", min_value=1, step=1)
        p = st.number_input("Price")
        if st.form_submit_button("Save Automatically"):
            new_row = pd.DataFrame([{"Stock": s.upper(), "Qty": q, "Buy Price": p}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.rerun()
