import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf

# 1. Page Configuration
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #00ff41; font-family: monospace; }
    div[data-testid="stMetric"] { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Google Sheets Connection with your Link
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rFlciVBKJT6AXmi_vJGwApicez4ZaTKQ0rrdUZVJ-aE/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ലൊക്കേഷൻ എറർ ഒഴിവാക്കാൻ URL നേരിട്ട് നൽകുന്നു
df = conn.read(spreadsheet=SHEET_URL, ttl="1m")

# 3. Manual RSI Calculation (No pandas-ta required)
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
                
                if current_rsi < 35: signal = "🟢 BUY"
                elif current_rsi > 65: signal = "🔴 SELL"
                else: signal = "⚪ HOLD"
                
                analysis[sym] = {"LTP": current_price, "RSI": current_rsi, "Signal": signal}
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0, "Signal": "N/A"}
    return analysis

# 4. Main UI Layout
left, mid, right = st.columns([1, 10, 1])

with mid:
    st.title("📊 NSE Portfolio & RSI Tracker")
    
    if not df.empty and 'Stock' in df.columns:
        with st.spinner('Updating Live Prices...'):
            live_data = get_market_data(df['Stock'].tolist())
            
            df['LTP'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('LTP', 0))
            df['RSI'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('RSI', 0))
            df['Signal'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('Signal', 'N/A'))
            
            df['P&L'] = (df['LTP'] - df['Buy Price']) * df['Qty']
            df['Change %'] = ((df['LTP'] - df['Buy Price']) / df['Buy Price']) * 100

        # Metrics Row
        m1, m2, m3 = st.columns(3)
        total_pl = df['P&L'].sum()
        m1.metric("Total P&L", f"₹ {total_pl:,.0f}", f"{total_pl:,.2f}")
        m2.metric("Active Stocks", len(df))
        m3.metric("Status", "LIVE")

        # 5. Formatted Table (Zero Decimals & Clean)
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
        st.info("ഷീറ്റിൽ ഡാറ്റയൊന്നും കാണുന്നില്ല. സൈഡ്ബാറിൽ നിന്ന് സ്റ്റോക്കുകൾ ചേർക്കുക.")

# 6. Sidebar
with st.sidebar:
    st.header("Settings")
    if st.button("Refresh Data"):
        st.rerun()
    
    st.divider()
    with st.form("add_stock"):
        s = st.text_input("Stock Symbol (eg: SBIN)")
        q = st.number_input("Qty", min_value=1)
        p = st.number_input("Buy Price", min_value=0.0)
        if st.form_submit_button("Add to Sheet"):
            new_row = pd.DataFrame([{"Stock": s.upper(), "Qty": q, "Buy Price": p}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            st.success("Added!")
            st.rerun()
