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
except Exception:
    df = pd.DataFrame(columns=['Date', 'Name', 'Buy pr', 'QTY'])

# 3. RSI കണക്കാക്കാനുള്ള ഫംഗ്ഷൻ
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# മാർക്കറ്റ് ഡാറ്റ എടുക്കാനുള്ള ഫംഗ്ഷൻ
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

# 4. പ്രധാന ഡിസ്‌പ്ലേ ഭാഗം
st.title("📊 NSE Portfolio & RSI Tracker")

if not df.empty and 'Name' in df.columns:
    with st.spinner('Updating Live Prices...'):
        # --- എറർ ഒഴിവാക്കാൻ ഡാറ്റാ ടൈപ്പ് മാറ്റുന്നു (Crucial Fix) ---
        df['Buy pr'] = pd.to_numeric(df['Buy pr'], errors='coerce')
        df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce')
        
        # ലൈവ് ഡാറ്റ എടുക്കുന്നു
        live_data = get_market_data(df['Name'].tolist())
        
        df['LTP'] = df['Name'].map(lambda x: live_data.get(x, {}).get('LTP', 0))
        df['RSI'] = df['Name'].map(lambda x: live_data.get(x, {}).get('RSI', 0))
        df['Signal'] = df['Name'].map(lambda x: live_data.get(x, {}).get('Signal', 'N/A'))
        
        # ലാഭവും നഷ്ടവും കണക്കാക്കുന്നു
        df['P&L'] = (df['LTP'] - df['Buy pr']) * df['QTY']
        df['Change %'] = ((df['LTP'] - df['Buy pr']) / df['Buy pr']) * 100

    # മെട്രിക്സ് (Metrics)
    m1, m2, m3 = st.columns(3)
    total_pl = df['P&L'].sum()
    m1.metric("Total P&L", f"₹ {total_pl:,.0f}")
    m2.metric("Active Stocks", len(df))
    m3.metric("Status", "LIVE")

    # ഡാറ്റാ ടേബിൾ
    st.subheader("Live Portfolio Insights")
    st.dataframe(
        df.style.format({
            "Buy pr": "{:.1f}",
            "LTP": "{:.1f}",
            "P&L": "{:.1f}",
            "Change %": "{:.2f}%",
            "RSI": "{:.0f}",
            "QTY": "{:.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ഷീറ്റിൽ ഡാറ്റയൊന്നും കാണുന്നില്ല. സൈഡ്ബാറിൽ നിന്ന് സ്റ്റോക്കുകൾ ചേർക്കുക.")

# 5. സൈഡ്ബാർ (Add New Stock)
with st.sidebar:
    st.header("Settings")
    if st.button("Refresh Data"):
        st.rerun()
    
    st.divider()
    st.subheader("Add New Stock")
    with st.form("add_stock"):
        s = st.text_input("Stock Symbol (eg: RELIANCE)")
        q = st.number_input("Quantity", min_value=1)
        p = st.number_input("Buy Price", min_value=0.0)
        
        if st.form_submit_button("Add to Sheet"):
            today = date.today().strftime("%d/%m/%y")
            new_row = pd.DataFrame([{
                "Date": today, 
                "Name": s.upper().replace(".NS", ""), 
                "Buy pr": p, 
                "QTY": q
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                # ഷീറ്റിലേക്ക് സേവ് ചെയ്യുന്നു
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success(f"{s.upper()} ചേർത്തു!")
                st.rerun()
            except Exception:
                st.error("സേവ് ചെയ്യാൻ കഴിഞ്ഞില്ല. Streamlit Secrets-ൽ Service Account നൽകിയിട്ടുണ്ടോ?")
