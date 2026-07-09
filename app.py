import streamlit as st
import pandas as pd
import ccxt
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Crypto Agent IA", layout="wide")

# =========================
# STYLE TYPE BINANCE
# =========================

st.markdown("""
<style>
    .stApp {
        background-color: #0B0E11;
        color: #EAECEF;
    }

    section[data-testid="stSidebar"] {
        background-color: #181A20;
        border-right: 1px solid #2B3139;
    }

    h1, h2, h3 {
        color: #F0B90B !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background-color: #181A20;
        border: 1px solid #2B3139;
        padding: 16px;
        border-radius: 12px;
    }

    div[data-testid="stMetricLabel"] {
        color: #848E9C !important;
    }

    div[data-testid="stMetricValue"] {
        color: #EAECEF !important;
        font-size: 1.05rem;
    }

    .binance-card {
        background-color: #181A20;
        border: 1px solid #2B3139;
        border-radius: 12px;
        padding: 16px;
        min-height: 115px;
        margin-bottom: 12px;
    }

    .binance-card-title {
        color: #848E9C;
        font-size: 0.85rem;
        margin-bottom: 8px;
    }

    .binance-card-value {
        color: #EAECEF;
        font-size: 1.05rem;
        font-weight: 600;
    }

    .yellow {
        color: #F0B90B;
        font-weight: 700;
    }

    .green {
        color: #0ECB81;
        font-weight: 700;
    }

    .red {
        color: #F6465D;
        font-weight: 700;
    }

    .small-text {
        color: #848E9C;
        font-size: 0.88rem;
    }

    .stButton > button {
        background-color: #F0B90B;
        color: #0B0E11;
        border: none;
        font-weight: 700;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        width: 100%;
    }

    .stButton > button:hover {
        background-color: #FFD33D;
        color: #0B0E11;
        border: none;
    }

    div[data-testid="stDataFrame"] {
        background-color: #181A20;
        border-radius: 12px;
    }

    .top-box {
        background-color: #181A20;
        border: 1px solid #2B3139;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
    }

    .top-title {
        color: #F0B90B;
        font-weight: 700;
        font-size: 1rem;
    }

    .top-sub {
        color: #848E9C;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# EXCHANGES
# =========================

spot_exchange = ccxt.binance({"enableRateLimit": True})
futures_exchange = ccxt.binanceusdm({"enableRateLimit": True})

# =========================
# SIDEBAR PARAMÈTRES
# =========================

st.sidebar.title("Paramètres")

default_watchlist = (
    "ENA, SUI, IMX, NEIRO, AUCTION, PENGU, TON, LINK, ADA, HYPER, TAO, WLFI, "
    "BNB, ONDO, SOL, SYRUP, ZEC, NEAR, SUN, RENDER, MORPHO, BCH, DASH"
)

with st.sidebar.expander("Watchlist", expanded=False):
    watchlist = st.text_area(
        "Panier de cryptos",
        default_watchlist,
        height=180
    )

comparison_label = st.sidebar.selectbox(
    "Temporalité d'analyse",
    ["1h", "4h", "12h", "1 jour", "3 jours", "7 jours"]
)

timeframe_map = {
    "1h": {"timeframe": "1h", "candles": 1},
    "4h": {"timeframe": "4h", "candles": 1},
    "12h": {"timeframe": "12h", "candles": 1},
    "1 jour": {"timeframe": "1d", "candles": 1},
    "3 jours": {"timeframe": "1d", "candles": 3},
    "7 jours": {"timeframe": "1d", "candles": 7},
}

analysis_timeframe = timeframe_map[comparison_label]["timeframe"]
comparison_candles = timeframe_map[comparison_label]["candles"]

mode = st.sidebar.selectbox(
    "Mode d'analyse",
    ["Long + Short", "Long uniquement", "Short uniquement"]
)

scan_mode = st.sidebar.selectbox(
    "Vitesse du scan",
    ["Rapide", "Complet"]
)

stop_percent = st.sidebar.slider(
    "Distance du stop depuis l'entrée (%)",
    0.25,
    5.0,
    1.0,
    0.25
)

max_tokens = st.sidebar.slider(
    "Nombre max de cryptos à scanner",
    5,
    30,
    20,
    1
)

scan_button = st.sidebar.button("Scanner maintenant")

st.sidebar.caption(
    "Rapide = spot + PA + force BTC. Complet = ajoute funding + open interest."
)

# =========================
# HEADER PRINCIPAL
# =========================

st.title("Crypto Agent IA — Scanner Price Action + Futures")

st.markdown(f"""
<div class="top-box">
    <div class="top-title">Dashboard trading crypto</div>
    <div class="top-sub">
        Temporalité : <span class="yellow">{comparison_label}</span> —
        Mode : <span class="yellow">{mode}</span> —
        Scan : <span class="yellow">{scan_mode}</span> —
        Stop : <span class="yellow">{stop_percent} %</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# AFFICHAGE
# =========================

def info_card(title, value, extra=""):
    st.markdown(f"""
    <div class="binance-card">
        <div class="binance-card-title">{title}</div>
        <div class="binance-card-value">{value}</div>
        <div class="small-text">{extra}</div>
    </div>
    """, unsafe_allow_html=True)


# =========================
# CACHE API
# =========================

@st.cache_data(ttl=60)
def cached_ohlcv(symbol, timeframe, limit):
    return spot_exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


@st.cache_data(ttl=60)
def cached_funding_rate(symbol):
    return futures_exchange.fetch_funding_rate(symbol)


@st.cache_data(ttl=60)
def cached_open_interest(symbol):
    return futures_exchange.fetch_open_interest(symbol)


@st.cache_data(ttl=120)
def cached_open_interest_history(symbol, timeframe, limit):
    return futures_exchange.fetch_open_interest_history(
        symbol,
        timeframe=timeframe,
        limit=limit
    )


# =========================
# DATA
# =========================

def get_ohlcv(symbol, timeframe="1d", limit=120):
    return cached_ohlcv(symbol, timeframe, limit)


def classify_funding_direction(funding_percent):
    if funding_percent == "N/A" or funding_percent is None:
        return "Neutre"

    try:
        funding_float = float(funding_percent)
    except Exception:
        return "Neutre"

    if funding_float > 0.03:
        return "Haussier"
    elif funding_float < -0.02:
        return "Baissier"
    else:
        return "Neutre"


def classify_open_interest_direction(symbol, analysis_timeframe, comparison_candles):
    pair = f"{symbol}/USDT"

    try:
        history = cached_open_interest_history(
            pair,
            analysis_timeframe,
            comparison_candles + 1
        )

        if not history or len(history) < 2:
            return "Neutre", "N/A"

        first = history[0]
        last = history[-1]

        first_oi = (
            first.get("openInterestAmount")
            or first.get("openInterestValue")
            or first.get("openInterest")
        )

        last_oi = (
            last.get("openInterestAmount")
            or last.get("openInterestValue")
            or last.get("openInterest")
        )

        if first_oi is None or last_oi is None or float(first_oi) == 0:
            return "Neutre", "N/A"

        oi_change = ((float(last_oi) / float(first_oi)) - 1) * 100

        if oi_change > 5:
            return "Haussier", round(oi_change, 2)
        elif oi_change < -5:
            return "Baissier", round(oi_change, 2)
        else:
            return "Neutre", round(oi_change, 2)

    except Exception:
        return "Neutre", "N/A"


def calculate_price_action_structure(df, comparison_candles, comparison_label):
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]

    price = close.iloc[-1]

    previous_high = high.iloc[-(comparison_candles + 1):-1].max()
    previous_low = low.iloc[-(comparison_candles + 1):-1].min()

    period_high = high.tail(comparison_candles).max()
    period_low = low.tail(comparison_candles).min()

    last_open = open_.iloc[-1]
    last_close = close.iloc[-1]
    last_high = high.iloc[-1]
    last_low = low.iloc[-1]

    candle_range = last_high - last_low
    close_position = (last_close - last_low) / candle_range if candle_range > 0 else 0.5

    range_total = previous_high - previous_low
    position_range = (price - previous_low) / range_total if range_total > 0 else 0.5

    if price > previous_high:
        structure = f"Breakout haussier {comparison_label}"
        position_label = "Breakout"
        long_pa_score = 24
        short_pa_score = 2

    elif price < previous_low:
        structure = f"Breakdown baissier {comparison_label}"
        position_label = "Breakdown"
        long_pa_score = 2
        short_pa_score = 24

    elif last_close > last_open and close_position > 0.70:
        structure = f"Pression acheteuse {comparison_label}"
        long_pa_score = 18
        short_pa_score = 5

        if position_range > 0.75:
            position_label = "Haut de range"
        elif position_range < 0.25:
            position_label = "Bas de range"
        else:
            position_label = "Milieu de range"

    elif last_close < last_open and close_position < 0.30:
        structure = f"Pression vendeuse {comparison_label}"
        long_pa_score = 5
        short_pa_score = 18

        if position_range > 0.75:
            position_label = "Haut de range"
        elif position_range < 0.25:
            position_label = "Bas de range"
        else:
            position_label = "Milieu de range"

    else:
        if position_range > 0.75:
            structure = f"Haut de range {comparison_label}"
            position_label = "Haut de range"
            long_pa_score = 8
            short_pa_score = 13

        elif position_range < 0.25:
            structure = f"Bas de range {comparison_label}"
            position_label = "Bas de range"
            long_pa_score = 13
            short_pa_score = 8

        else:
            structure = f"Range neutre {comparison_label}"
            position_label = "Milieu de range"
            long_pa_score = 8
            short_pa_score = 8

    return {
        "Structure PA": structure,
        "Position Range": position_label,
        "Score PA Long": long_pa_score,
        "Score PA Short": short_pa_score,
        "High période": round(period_high, 6),
        "Low période": round(period_low, 6),
        "High précédent": round(previous_high, 6),
        "Low précédent": round(previous_low, 6),
    }


def calculate_spot(symbol):
    pair = f"{symbol}/USDT"
    data = get_ohlcv(pair, timeframe=analysis_timeframe)

    df = pd.DataFrame(
        data,
        columns=["time", "open", "high", "low", "close", "volume"]
    )

    close = df["close"]
    volume = df["volume"]

    price = close.iloc[-1]

    perf_period = ((close.iloc[-1] / close.iloc[-(comparison_candles + 1)]) - 1) * 100

    pa = calculate_price_action_structure(df, comparison_candles, comparison_label)

    volume_period = max(comparison_candles, 3)
    avg_volume_period = volume.tail(volume_period).mean()
    volume_ratio = volume.iloc[-1] / avg_volume_period if avg_volume_period > 0 else 0

    if volume_ratio > 1.8:
        volume_score = 15
    elif volume_ratio > 1.2:
        volume_score = 10
    elif volume_ratio > 0.8:
        volume_score = 6
    else:
        volume_score = 2

    if perf_period > 15:
        long_momentum_score = 20
    elif perf_period > 7:
        long_momentum_score = 15
    elif perf_period > 0:
        long_momentum_score = 10
    else:
        long_momentum_score = 3

    if perf_period < -15:
        short_momentum_score = 20
    elif perf_period < -7:
        short_momentum_score = 15
    elif perf_period < 0:
        short_momentum_score = 10
    else:
        short_momentum_score = 3

    score_long_spot = pa["Score PA Long"] + long_momentum_score + volume_score
    score_short_spot = pa["Score PA Short"] + short_momentum_score + volume_score

    result = {
        "Crypto": pair,
        "Prix": round(price, 6),
        f"Perf {comparison_label}": round(perf_period, 2),
        f"Volume x Moy.{volume_period} bougies": round(volume_ratio, 2),
        "Score Volume": volume_score,
        "Score Momentum Long": long_momentum_score,
        "Score Momentum Short": short_momentum_score,
        "Score Long Spot": score_long_spot,
        "Score Short Spot": score_short_spot,
    }

    result.update(pa)

    return result


def calculate_futures(symbol):
    if scan_mode == "Rapide":
        return {
            "Funding %": "N/A",
            "Funding biais": "Neutre",
            "Open Interest": "N/A",
            "OI tendance": "Neutre",
            "OI variation %": "N/A",
            "Score Futures Long": 0,
            "Score Futures Short": 0,
            "Futures": "Mode rapide"
        }

    pair = f"{symbol}/USDT"

    funding_score_long = 0
    funding_score_short = 0
    oi_score = 0
    futures_status = "Non dispo"

    try:
        funding = cached_funding_rate(pair)
        funding_rate = funding.get("fundingRate", None)

        if funding_rate is not None:
            funding_percent = funding_rate * 100

            if -0.02 <= funding_percent <= 0.03:
                funding_score_long = 10
            elif funding_percent < -0.02:
                funding_score_long = 12
            elif funding_percent <= 0.07:
                funding_score_long = 6
            else:
                funding_score_long = 2

            if funding_percent > 0.07:
                funding_score_short = 12
            elif funding_percent > 0.03:
                funding_score_short = 8
            elif -0.02 <= funding_percent <= 0.03:
                funding_score_short = 6
            else:
                funding_score_short = 2
        else:
            funding_percent = None

    except Exception:
        funding_percent = None

    funding_bias = classify_funding_direction(
        round(funding_percent, 4) if funding_percent is not None else "N/A"
    )

    try:
        oi = cached_open_interest(pair)
        oi_value = oi.get("openInterestAmount", None)

        if oi_value is not None and oi_value > 0:
            oi_score = 10
            futures_status = "OK"
        else:
            oi_score = 3
            futures_status = "OI faible/inconnu"

    except Exception:
        oi_value = None
        oi_score = 0

    oi_trend, oi_change = classify_open_interest_direction(
        symbol,
        analysis_timeframe,
        comparison_candles
    )

    return {
        "Funding %": round(funding_percent, 4) if funding_percent is not None else "N/A",
        "Funding biais": funding_bias,
        "Open Interest": round(oi_value, 2) if oi_value is not None else "N/A",
        "OI tendance": oi_trend,
        "OI variation %": oi_change,
        "Score Futures Long": funding_score_long + oi_score,
        "Score Futures Short": funding_score_short + oi_score,
        "Futures": futures_status
    }


def trade_plan_long(price, low_period, high_period, stop_percent):
    entry = max(low_period, price * 0.97) if low_period < price else price * 0.97
    stop = entry * (1 - stop_percent / 100)
    risk_unit = entry - stop

    return {
        "Sens": "LONG",
        "Entrée": round(entry, 6),
        "Stop": round(stop, 6),
        "TP1": round(entry + risk_unit * 2, 6),
        "TP2": round(entry + risk_unit * 3, 6),
        "Cible range": round(high_period, 6) if high_period > entry else "N/A",
        "R/R TP1": 2.0,
        "R/R TP2": 3.0
    }


def trade_plan_short(price, low_period, high_period, stop_percent):
    entry = min(high_period, price * 1.03) if high_period > price else price * 1.03
    stop = entry * (1 + stop_percent / 100)
    risk_unit = stop - entry

    return {
        "Sens": "SHORT",
        "Entrée": round(entry, 6),
        "Stop": round(stop, 6),
        "TP1": round(entry - risk_unit * 2, 6),
        "TP2": round(entry - risk_unit * 3, 6),
        "Cible range": round(low_period, 6) if low_period < entry else "N/A",
        "R/R TP1": 2.0,
        "R/R TP2": 3.0
    }


def define_bias(score_long, score_short, mode):
    if mode == "Long uniquement":
        if score_long >= 80:
            return "Long spot potentiel", "Chercher entrée pullback long", "LONG"
        elif score_long >= 60:
            return "Surveillance long", "Attendre confirmation long", "LONG"
        else:
            return "Pas prioritaire", "Rien à faire", "NONE"

    if mode == "Short uniquement":
        if score_short >= 80:
            return "Short potentiel", "Chercher entrée rebond short", "SHORT"
        elif score_short >= 60:
            return "Surveillance short", "Attendre confirmation short", "SHORT"
        else:
            return "Pas prioritaire", "Rien à faire", "NONE"

    if score_long >= 80 and score_long > score_short:
        return "Long spot potentiel", "Chercher entrée pullback long", "LONG"

    if score_short >= 80 and score_short > score_long:
        return "Short potentiel", "Chercher entrée rebond short", "SHORT"

    if score_long >= 60 and score_long >= score_short:
        return "Surveillance long", "Attendre confirmation long", "LONG"

    if score_short >= 60 and score_short > score_long:
        return "Surveillance short", "Attendre confirmation short", "SHORT"

    return "Pas prioritaire", "Rien à faire", "NONE"


def decision_reason(
    biais,
    sens,
    force_vs_btc,
    structure_pa,
    position_range,
    score_long,
    score_short,
    funding_bias,
    oi_trend
):
    reasons = []

    if biais == "Pas prioritaire":
        if score_long < 60 and score_short < 60:
            reasons.append("Scores long/short trop faibles")

        if -2 <= force_vs_btc <= 2:
            reasons.append("Suit trop BTC")

        if force_vs_btc < -2:
            reasons.append("Faible vs BTC")
        elif force_vs_btc > 2:
            reasons.append("Surperforme BTC mais setup insuffisant")

        if "Range neutre" in structure_pa:
            reasons.append("Structure PA neutre")

        if position_range == "Milieu de range":
            reasons.append("Prix au milieu du range")

        if funding_bias == "Haussier":
            reasons.append("Funding haussier")
        elif funding_bias == "Baissier":
            reasons.append("Funding baissier")

        if oi_trend == "Neutre":
            reasons.append("OI neutre")

        if not reasons:
            reasons.append("Pas de confirmation suffisante")

        return " / ".join(reasons)

    if sens == "LONG":
        reasons.append("Setup long détecté")
        reasons.append("Surperformance vs BTC" if force_vs_btc > 0 else "Force BTC faible")

        if "Breakout haussier" in structure_pa:
            reasons.append("Breakout haussier")
        elif "Pression acheteuse" in structure_pa:
            reasons.append("Pression acheteuse")
        elif position_range == "Bas de range":
            reasons.append("Potentiel rebond bas de range")

        return " / ".join(reasons)

    if sens == "SHORT":
        reasons.append("Setup short détecté")
        reasons.append("Faiblesse vs BTC" if force_vs_btc < 0 else "Short malgré force relative")

        if "Breakdown baissier" in structure_pa:
            reasons.append("Breakdown baissier")
        elif "Pression vendeuse" in structure_pa:
            reasons.append("Pression vendeuse")
        elif position_range == "Haut de range":
            reasons.append("Potentiel rejet haut de range")

        return " / ".join(reasons)

    return "Pas de signal clair"


def scan_crypto(crypto, btc_perf_period):
    spot = calculate_spot(crypto)
    futures = calculate_futures(crypto)

    perf_col = f"Perf {comparison_label}"
    force_vs_btc = spot[perf_col] - btc_perf_period

    if force_vs_btc > 10:
        force_score_long = 20
    elif force_vs_btc > 5:
        force_score_long = 15
    elif force_vs_btc > 0:
        force_score_long = 10
    else:
        force_score_long = 3

    if force_vs_btc < -10:
        force_score_short = 20
    elif force_vs_btc < -5:
        force_score_short = 15
    elif force_vs_btc < 0:
        force_score_short = 10
    else:
        force_score_short = 3

    score_long_total = (
        spot["Score Long Spot"]
        + force_score_long
        + futures["Score Futures Long"]
    )

    score_short_total = (
        spot["Score Short Spot"]
        + force_score_short
        + futures["Score Futures Short"]
    )

    biais, action, sens = define_bias(score_long_total, score_short_total, mode)

    if sens == "LONG":
        plan = trade_plan_long(
            spot["Prix"],
            spot["Low période"],
            spot["High période"],
            stop_percent
        )
    elif sens == "SHORT":
        plan = trade_plan_short(
            spot["Prix"],
            spot["Low période"],
            spot["High période"],
            stop_percent
        )
    else:
        plan = {
            "Sens": "NONE",
            "Entrée": "N/A",
            "Stop": "N/A",
            "TP1": "N/A",
            "TP2": "N/A",
            "Cible range": "N/A",
            "R/R TP1": "N/A",
            "R/R TP2": "N/A"
        }

    raison_decision = decision_reason(
        biais,
        sens,
        force_vs_btc,
        spot["Structure PA"],
        spot["Position Range"],
        score_long_total,
        score_short_total,
        futures["Funding biais"],
        futures["OI tendance"]
    )

    row = {}
    row.update(spot)
    row.update({
        f"Force vs BTC {comparison_label}": round(force_vs_btc, 2),
        "Score Force Long": force_score_long,
        "Score Force Short": force_score_short,
    })
    row.update(futures)
    row.update({
        "Score Long Total": score_long_total,
        "Score Short Total": score_short_total,
        "Priority Score": max(score_long_total, score_short_total),
        "Biais": biais,
        "Raison décision": raison_decision,
        "Action": action,
        "Distance stop %": stop_percent,
    })
    row.update(plan)

    return row


# =========================
# SCAN
# =========================

if scan_button:
    cryptos = [c.strip().upper() for c in watchlist.split(",") if c.strip()]
    cryptos = cryptos[:max_tokens]

    rows = []
    errors = []

    try:
        btc_data = get_ohlcv("BTC/USDT", timeframe=analysis_timeframe)
        btc_df = pd.DataFrame(
            btc_data,
            columns=["time", "open", "high", "low", "close", "volume"]
        )

        btc_perf_period = (
            (btc_df["close"].iloc[-1] / btc_df["close"].iloc[-(comparison_candles + 1)]) - 1
        ) * 100

    except Exception:
        btc_perf_period = 0

    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_crypto = {
            executor.submit(scan_crypto, crypto, btc_perf_period): crypto
            for crypto in cryptos
        }

        for index, future in enumerate(as_completed(future_to_crypto)):
            crypto = future_to_crypto[future]

            try:
                rows.append(future.result())
            except Exception as e:
                errors.append(f"{crypto}: {e}")

            progress.progress((index + 1) / len(cryptos))

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("Priority Score", ascending=False)

        force_column_name = f"Force vs BTC {comparison_label}"
        perf_column_name = f"Perf {comparison_label}"

        visible_columns = [
            "Crypto",
            "Prix",
            perf_column_name,
            force_column_name,
            "Structure PA",
            "Position Range",
            "Score Long Total",
            "Score Short Total",
            "Biais",
            "Raison décision",
            "Sens",
            "Entrée",
            "Stop",
            "TP1",
            "TP2",
            "Cible range",
        ]

        df_light = df[visible_columns]

        st.subheader("Classement Price Action + Futures")
        st.dataframe(df_light, use_container_width=True)

        best = df.iloc[0]

        st.subheader("Stats du meilleur setup")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Crypto", best["Crypto"])
            st.metric("Sens", best["Sens"])

        with col2:
            st.metric("Score Long", f"{best['Score Long Total']}/99")
            st.metric("Score Short", f"{best['Score Short Total']}/99")

        with col3:
            st.metric("Perf", f"{best[f'Perf {comparison_label}']} %")
            st.metric("Force vs BTC", f"{best[force_column_name]} %")

        with col4:
            st.metric("Structure", best["Structure PA"])
            st.metric("Range", best["Position Range"])

        with col5:
            st.metric("Funding", best["Funding biais"])
            st.metric("Open Interest", best["OI tendance"])

        with col6:
            st.metric("Biais", best["Biais"])
            st.metric("Action", best["Action"])

        st.subheader("Plan proposé")

        plan_col1, plan_col2, plan_col3, plan_col4, plan_col5, plan_col6 = st.columns(6)

        with plan_col1:
            st.metric("Entrée", best["Entrée"])

        with plan_col2:
            st.metric("Stop", best["Stop"])

        with plan_col3:
            st.metric("TP1", best["TP1"])

        with plan_col4:
            st.metric("TP2", best["TP2"])

        with plan_col5:
            st.metric("Cible range", best["Cible range"])

        with plan_col6:
            st.metric("Distance stop", f"{best['Distance stop %']} %")

        st.subheader("Comment le résultat est obtenu")

        exp1, exp2, exp3, exp4 = st.columns(4)

        with exp1:
            info_card(
                "1. Force relative",
                f"{best[force_column_name]} %",
                f"Performance {best['Crypto']} comparée à BTC sur {comparison_label}."
            )

        with exp2:
            info_card(
                "2. Price Action",
                best["Structure PA"],
                f"Position actuelle : {best['Position Range']}."
            )

        with exp3:
            info_card(
                "3. Futures",
                f"Funding {best['Funding biais']} / OI {best['OI tendance']}",
                "Filtre de confirmation futures."
            )

        with exp4:
            info_card(
                "4. Décision",
                f"{best['Sens']} — {best['Biais']}",
                best["Action"]
            )

        st.markdown(f"""
        <div class="binance-card">
            <div class="binance-card-title">Résumé rapide</div>
            <div class="binance-card-value">
                Le token <span class="yellow">{best['Crypto']}</span> ressort en premier car son score dominant est le plus élevé de la watchlist.
            </div>
            <div class="small-text">
                Raison : {best['Raison décision']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Calcul technique complet", expanded=False):
            tech1, tech2, tech3, tech4 = st.columns(4)

            with tech1:
                info_card("Prix actuel", best["Prix"], f"Temporalité : {comparison_label}")
                info_card("Performance", f"{best[f'Perf {comparison_label}']} %", "Performance du token.")
                info_card("Force vs BTC", f"{best[force_column_name]} %", "Écart face à BTC.")

            with tech2:
                info_card("Structure PA", best["Structure PA"], "Lecture price action.")
                info_card("Position range", best["Position Range"], "Zone actuelle du prix.")
                info_card("Range période", f"{best['Low période']} → {best['High période']}", "Low / High période.")

            with tech3:
                info_card("Score Long Spot", best["Score Long Spot"], "PA + momentum + volume.")
                info_card("Score Short Spot", best["Score Short Spot"], "PA + momentum + volume.")
                info_card("Score Force", f"L {best['Score Force Long']} / S {best['Score Force Short']}", "Force relative BTC.")

            with tech4:
                info_card("Futures", f"L {best['Score Futures Long']} / S {best['Score Futures Short']}", "Funding + OI.")
                info_card("Funding / OI", f"{best['Funding biais']} / {best['OI tendance']}", f"OI variation : {best['OI variation %']} %")
                info_card("Score final", f"L {best['Score Long Total']} / S {best['Score Short Total']}", "Scores finaux.")

            tech5, tech6, tech7, tech8 = st.columns(4)

            with tech5:
                info_card("High précédent", best["High précédent"], "Référence breakout.")
                info_card("Low précédent", best["Low précédent"], "Référence breakdown.")

            with tech6:
                info_card("Funding brut", f"{best['Funding %']} %", f"Biais : {best['Funding biais']}")
                info_card("Open Interest brut", best["Open Interest"], f"Tendance : {best['OI tendance']}")

            with tech7:
                info_card("Entrée", best["Entrée"], f"Sens : {best['Sens']}")
                info_card("Stop", best["Stop"], f"Distance : {best['Distance stop %']} %")

            with tech8:
                info_card("TP1 / TP2", f"{best['TP1']} / {best['TP2']}", "Objectifs en R/R.")
                info_card("Cible range", best["Cible range"], "Objectif basé sur le range.")

        st.caption(
            "Le cache évite de rappeler Binance pendant 60 secondes. "
            "Le scan parallèle accélère le traitement de la watchlist."
        )

    if errors:
        st.subheader("Cryptos non récupérées")
        for error in errors:
            st.write(error)

else:
    st.markdown("""
    <div class="binance-card">
        <div class="binance-card-title">En attente</div>
        <div class="binance-card-value">Configure les paramètres dans la sidebar, puis lance le scan.</div>
        <div class="small-text">
            Le tableau apparaîtra ici directement, sans prendre toute la hauteur avec les réglages.
        </div>
    </div>
    """, unsafe_allow_html=True)