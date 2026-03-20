import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf

# 1. Page Configuration (Professional Look)
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

# Custom CSS for Professional Look and Center Alignment
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #00ff41; font-family: monospace; }
    .stDataFrame { margin: auto; }
    div[data-testid="stMetric"] { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="1m")

# 3. Manual RSI Calculation (Replacing pandas-ta)
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
                
                # Signal Logic
                if current_rsi < 35: signal = "🟢 BUY"
                elif current_rsi > 65: signal = "🔴 SELL"
                else: signal = "⚪ HOLD"
                
                analysis[sym] = {"LTP": current_price, "RSI": current_rsi, "Signal": signal}
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0, "Signal": "N/A"}
    return analysis

# 4. Horizontal Align Center Layout
left_space, main_col, right_space = st.columns([1, 10, 1])

with main_col:
    st.title("📊 NSE Portfolio & RSI Tracker")
    
    if not df.empty and 'Stock' in df.columns:
        with st.spinner('Updating Live Market Prices...'):
            live_data = get_market_data(df['Stock'].tolist())
            
            df['LTP'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('LTP', 0))
            df['RSI'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('RSI', 0))
            df['Signal'] = df['Stock'].map(lambda x: live_data.get(x, {}).get('Signal', 'N/A'))
            
            df['P&L'] = (df['LTP'] - df['Buy Price']) * df['Qty']
            df['Change %'] = ((df['LTP'] - df['Buy Price']) / df['Buy Price']) * 100

        # Display Metrics
        m1, m2, m3 = st.columns(3)
        total_pl = df['P&L'].sum()
        m1.metric("Total P&L", f"₹ {total_pl:,.0f}", f"{total_pl:,.2f}")
        m2.metric("Stocks Count", len(df))
        m3.metric("Market Status", "LIVE")

        st.subheader("Live Insights")
        
        # 5. Table Formatting (Removing Decimals & Aligning)
        st.dataframe(
            df.style.format({
                "Buy Price": "₹ {:.0f}",
                "LTP": "₹ {:.0f}",
                "P&L": "₹ {:.0f}",
                "Change %": "{:.2f}%",
                "RSI": "{:.0f}",
                "Qty": "{:.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("പോർട്ട്ഫോളിയോ കാലിയാണ്. സൈഡ്ബാറിൽ നിന്ന് സ്റ്റോക്കുകൾ ചേർക്കുക.")

# 6. Sidebar for Adding Stocks & Auto-Save
with st.sidebar:
    st.header("Add New Stock")
    with st.form("stock_entry", clear_on_submit=True):
        new_stock = st.text_input("NSE Symbol (eg: RVNL)")
        new_qty = st.number_input("Quantity", min_value=1, step=1)
        new_price = st.number_input("Buy Price", min_value=0.0)
        
        if st.form_submit_button("Add & Save Automatically"):
            if new_stock:
                new_row = pd.DataFrame([{"Stock": new_stock.upper(), "Qty": new_qty, "Buy Price": new_price}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                
                # Update Google Sheet
                conn.update(data=updated_df)
                st.success(f"{new_stock} saved successfully!")
                st.rerun()

    if st.button("Refresh Data"):
        st.rerun()
