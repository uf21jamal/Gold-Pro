import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
import datetime
import pytz

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Gold Sniper 1:3", layout="wide")

# --- JUDUL ---
st.title("🎯 Gold Sniper Intraday (H1)")
st.markdown("**Strategy:** Trend EMA + Risk Reward 1:3 (Set & Forget)")

# --- FUNGSI TARIK DATA ---
def get_data():
    # Guna 'try-except' supaya tak blank kalau error
    try:
        ticker = "GC=F"
        # Tarik data 1 Jam (H1) untuk 5 hari
        df = yf.download(ticker, period="5d", interval="1h", progress=False)
        
        if df.empty:
            return None

        # Cuci Data
        df.reset_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        # Timezone Malaysia
        kl_tz = pytz.timezone('Asia/Kuala_Lumpur')
        if df['Datetime'].dt.tz is None:
             df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert(kl_tz)
        else:
             df['Datetime'] = df['Datetime'].dt.tz_convert(kl_tz)
             
        return df
    except Exception as e:
        st.error(f"Error Data: {e}")
        return None

# --- LOAD DATA ---
with st.spinner('Sedang tarik data market live...'):
    df = get_data()

if df is not None:
    # --- KIRA INDIKATOR ---
    # 1. Trend (EMA 50 & 200)
    df["EMA_50"] = EMAIndicator(close=df["Close"], window=50).ema_indicator()
    df["EMA_200"] = EMAIndicator(close=df["Close"], window=200).ema_indicator()
    
    # 2. Volatility (ATR untuk SL)
    df["ATR"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14).average_true_range()

    # Ambil Candle Terkini (Last Closed Candle)
    last = df.iloc[-1]
    curr_price = last["Close"]
    atr = last["ATR"]

    # --- LOGIC SIGNAL (1:3) ---
    bias = "NEUTRAL"
    color = "gray"
    
    # Logic: Kalau EMA 50 > EMA 200 = UPTREND
    if last["EMA_50"] > last["EMA_200"]:
        bias = "BUY ZONE 🟢"
        color = "green"
        # Setup Buy
        entry = curr_price
        sl = entry - (atr * 1.5)  # SL = 1.5x ATR
        risk = entry - sl
        tp = entry + (risk * 3)   # TP = 3x Risk
        
    else:
        bias = "SELL ZONE 🔴"
        color = "red"
        # Setup Sell
        entry = curr_price
        sl = entry + (atr * 1.5)  # SL = 1.5x ATR
        risk = sl - entry
        tp = entry - (risk * 3)   # TP = 3x Risk

    # --- PAPARAN DASHBOARD ---
    st.divider()
    
    # Baris 1: Status Market
    c1, c2 = st.columns(2)
    c1.metric("Harga Terkini", f"${curr_price:.2f}")
    c1.caption(f"Update: {last['Datetime'].strftime('%d %b %H:%M')}")
    
    with c2:
        st.subheader(f"SIGNAL: :{color}[{bias}]")

    # Baris 2: Nombor Entry (PENTING)
    st.info("📊 **SETUP HARI INI (Salin ke MT4/MT5)**")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("1. ENTRY PRICE", f"{entry:.2f}")
    col2.metric("2. STOP LOSS (SL)", f"{sl:.2f}", f"Risk: -${risk:.2f}")
    col3.metric("3. TAKE PROFIT (TP)", f"{tp:.2f}", f"Reward: +${risk*3:.2f}")

    # --- CARTA ---
    st.subheader("Carta Trend H1")
    fig = go.Figure()

    # Candle
    fig.add_trace(go.Candlestick(x=df['Datetime'],
                open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price'))
    
    # EMA Lines
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['EMA_50'], line=dict(color='blue', width=2), name='EMA 50 (Trend)'))
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['EMA_200'], line=dict(color='orange', width=2), name='EMA 200 (Baseline)'))

    # Entry/SL/TP Lines
    fig.add_hline(y=entry, line_dash="dot", line_color="white", annotation_text="ENTRY")
    fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="SL")
    fig.add_hline(y=tp, line_dash="dash", line_color="green", annotation_text="TP (1:3)")

    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ Data tak dapat ditarik. Mungkin pasaran tutup (Weekend) atau server Yahoo Finance sibuk. Cuba refresh browser.")
