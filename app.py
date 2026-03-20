import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import date

# 1. Page Config
st.set_page_config(page_title="NSE Pro Tracker", layout="wide")

# 2. Connection
# ശ്രദ്ധിക്കുക: Secrets-ൽ കണക്ഷൻ സെറ്റ് ചെയ്തിട്ടുണ്ടെങ്കിൽ SHEET_URL ഇവിടെ നൽകേണ്ടതില്ല.
# എങ്കിലും സുരക്ഷയ്ക്കായി താഴെ നൽകുന്നു.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1rFlciVBKJT6AXmi_vJGwApicez4ZaTKQ0rrdUZVJ-aE/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Market Data Function (Rounding to Integers)
@st.cache_data(ttl=300)
def get_market_data(symbols):
    analysis = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            hist = ticker.history(period="1mo")
            if not hist.empty:
                # ദശാംശം ഒഴിവാക്കി പൂർണ്ണസംഖ്യയാക്കുന്നു
                current_price = int(round(hist['Close'].iloc[-1]))
                analysis[sym] = {"LTP": current_price}
            else:
                analysis[sym] = {"LTP": 0}
        except:
            analysis[sym] = {"LTP": 0}
    return analysis

# 4. Main Display
st.title("📊 NSE Portfolio Tracker")

try:
    # ഗൂഗിൾ ഷീറ്റിൽ നിന്ന് ഡാറ്റ വായിക്കുന്നു
    df = conn.read(spreadsheet=SHEET_URL, ttl="1m")
    
    # കോളം പേരുകളിലെ സ്പേസ് ഒഴിവാക്കുന്നു
    df.columns = df.columns.str.strip()
    
    if not df.empty:
        # ഡാറ്റ ക്ലീനിംഗ്: Buy Price, QTY എന്നിവ ഇന്റിജർ ആക്കുന്നു
        df['Buy pr'] = pd.to_numeric(df['Buy pr'], errors='coerce').fillna(0).astype(int)
        df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0).astype(int)
        
        with st.spinner('Updating Market Prices...'):
            unique_stocks = df['Name'].unique().tolist()
            live_data = get_market_data(unique_stocks)
            
            # ലൈവ് പ്രൈസ് (LTP) ചേർക്കുന്നു
            df['LTP'] = df['Name'].map(lambda x: live_data.get(x, {}).get('LTP', 0))
            
            # കണക്കുകൂട്ടലുകൾ (എല്ലാം ഇന്റിജർ രൂപത്തിൽ)
            df['Invested'] = df['Buy pr'] * df['QTY']
            df['Current Value'] = df['LTP'] * df['QTY']
            df['P&L'] = df['Current Value'] - df['Invested']
            
        # പ്രധാന മെട്രിക്സുകൾ (ഇന്ത്യൻ കോമ ഫോർമാറ്റിൽ)
        m1, m2 = st.columns(2)
        total_value = int(df['Current Value'].sum())
        total_pnl = int(df['P&L'].sum())
        
        m1.metric("Total Portfolio Value", f"₹ {total_value:,}")
        m2.metric("Total P&L", f"₹ {total_pnl:,}", delta=f"{total_pnl:,}")

        # പോർട്ട്‌ഫോളിയോ ടേബിൾ
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 5. Sidebar: Add New Stock
    with st.sidebar:
        st.header("➕ Add New Stock")
        with st.form("add_stock_form", clear_on_submit=True):
            name = st.text_input("Symbol (eg: SBIN)").upper()
            qty = st.number_input("Quantity", min_value=1, step=1)
            price = st.number_input("Buy Price", min_value=0, step=1)
            
            if st.form_submit_button("Save to Google Sheet"):
                if name and price > 0:
                    # പുതിയ സ്റ്റോക്ക് വിവരങ്ങൾ
                    new_entry = pd.DataFrame([{
                        "Date": date.today().strftime("%d/%m/%y"),
                        "Name": name,
                        "Buy pr": int(price),
                        "QTY": int(qty)
                    }])
                    
                    # നിലവിലെ ഡാറ്റയുമായി ചേർക്കുന്നു
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    
                    try:
                        # ഗൂഗിൾ ഷീറ്റിലേക്ക് സേവ് ചെയ്യുന്നു
                        conn.update(spreadsheet=SHEET_URL, data=updated_df)
                        st.success(f"{name} വിജയകരമായി ചേർത്തു!")
                        st.rerun()
                    except Exception as e:
                        st.error("സേവ് ചെയ്യാൻ കഴിഞ്ഞില്ല. Service Account Key സെറ്റ് ചെയ്തിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")
                else:
                    st.warning("ദയവായി എല്ലാ വിവരങ്ങളും കൃത്യമായി നൽകുക.")

except Exception as e:
    st.error(f"കണക്ഷൻ എറർ: {e}")
