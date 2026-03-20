import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import pandas_ta as ta  # RSI കണക്കാക്കാൻ ഇത് ആവശ്യമാണ്

# 1. Page Configuration
st.set_page_config(page_title="NSE Pro Portfolio", layout="wide")

# 2. Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="1m")

# 3. Function to get Live Data & RSI
def get_stock_analysis(symbols, rsi_period):
    analysis = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            # കഴിഞ്ഞ 30 ദിവസത്തെ ഡാറ്റ എടുക്കുന്നു (RSI കണക്കാക്കാൻ ഇത് വേണം)
            hist = ticker.history(period="1mo")
            
            if not hist.empty:
                # RSI കണക്കാക്കുന്നു
                rsi_series = ta.rsi(hist['Close'], length=rsi_period)
                current_rsi = rsi_series.iloc[-1]
                current_price = hist['Close'].iloc[-1]
                
                # Buy/Sell Signal Logic
                if current_rsi < 30:
                    signal = "🟢 BUY (Oversold)"
                elif current_rsi > 70:
                    signal = "🔴 SELL (Overbought)"
                else:
                    signal = "⚪ HOLD (Neutral)"
                
                analysis[sym] = {
                    "LTP": current_price,
                    "RSI": current_rsi,
                    "Signal": signal
                }
        except:
            analysis[sym] = {"LTP": 0, "RSI": 0, "Signal": "Error"}
    return analysis

# 4. Center Alignment Layout
left_co, cent_co, last_co = st.columns([1, 10, 1])

with cent_co:
    st.title("📊 NSE Portfolio & RSI Live Tracker")
    
    # Sidebar Settings
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        rsi_p = st.slider("RSI Period", 5, 30, 14)
        st.divider()
        
        # Add Stock Form
        st.subheader("➕ Add New Stock")
        with st.form("add_stock", clear_on_submit=True):
            s = st.text_input("NSE Symbol (eg: RELIANCE)")
            q = st.number_input("Qty", min_value=1, step=1)
            p = st.number_input("Buy Price", min_value=0.1)
            if st.form_submit_button("Save & Sync"):
                new_row = pd.DataFrame([{"Stock": s.upper(), "Qty": q, "Buy Price": p}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.rerun()

    # 5. Data Processing & Display
    if not df.empty and 'Stock' in df.columns:
        with st.spinner('Updating Market Signals...'):
            results = get_stock_analysis(df['Stock'].tolist(), rsi_p)
            
            # Mapping results to Dataframe
            df['LTP'] = df['Stock'].map(lambda x: results.get(x, {}).get('LTP', 0))
            df['RSI'] = df['Stock'].map(lambda x: results.get(x, {}).get('RSI', 0))
            df['Signal'] = df['Stock'].map(lambda x: results.get(x, {}).get('Signal', 'N/A'))
            
            df['P&L'] = (df['LTP'] - df['Buy Price']) * df['Qty']
            df['Change %'] = ((df['LTP'] - df['Buy Price']) / df['Buy Price']) * 100

        # Metrics Row
        total_pl = df['P&L'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Portfolio P&L", f"₹{total_pl:,.2f}", f"{total_pl:,.2f}")
        m2.metric("Active Stocks", len(df))
        m3.metric("Market Status", "🟢 OPEN" if total_pl >=0 else "🔴 DOWN")

        # Professional Styled Table
        st.subheader("Live Market Insights")
        st.dataframe(
            df.style.format({
                "Buy Price": "{:.2f}",
                "LTP": "{:.2f}",
                "P&L": "{:.2f}",
                "Change %": "{:.2f}%",
                "RSI": "{:.2f}"
            }).applymap(lambda x: 'color: #00ff41' if 'BUY' in str(x) else ('color: #ff4b4b' if 'SELL' in str(x) else ''), subset=['Signal']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Portfolio empty. Please add stocks from sidebar.")
