import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Crypto Agent IA", layout="wide")

# =========================
# STYLE
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
# SIDEBAR
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
    ["1h", "4h", "12h", "1 jour", "7 jours", "30 jours"]
)

mode = st.sidebar.selectbox(
    "Mode d'analyse",
    ["Long + Short", "Long uniquement", "Short uniquement"]
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
    10,
    1
)

use_futures_confirm = st.sidebar.checkbox(
    "Activer OI + Funding",
    value=False
)

scan_button = st.sidebar.button("Scanner maintenant")

if use_futures_confirm:
    st.sidebar.caption(
        "Mode complet : bougies + OI + funding. Plus lourd pour Coinalyze."
    )
else:
    st.sidebar.caption(
        "Mode stable : bougies / PA réelle uniquement. OI + funding désactivés pour éviter les erreurs 429."
    )

# =========================
# HEADER
# =========================

st.title("Crypto Agent IA — Scanner PA + OI + Funding")

futures_status = "activés" if use_futures_confirm else "désactivés"

st.markdown(f"""
<div class="top-box">
    <div class="top-title">Dashboard trading crypto</div>
    <div class="top-sub">
        Sources : <span class="yellow">CoinMarketCap + Coinalyze</span> —
        Temporalité : <span class="yellow">{comparison_label}</span> —
        Mode : <span class="yellow">{mode}</span> —
        Stop : <span class="yellow">{stop_percent} %</span> —
        OI/Funding : <span class="yellow">{futures_status}</span>
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
# SECRETS
# =========================

def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return None

# =========================
# API COINMARKETCAP
# =========================

@st.cache_data(ttl=120)
def fetch_cmc_quotes(symbols_csv, api_key):
    url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key
    }

    params = {
        "symbol": symbols_csv,
        "convert": "USD"
    }

    response = requests.get(url, headers=headers, params=params, timeout=20)

    if response.status_code != 200:
        raise Exception(f"Erreur CoinMarketCap {response.status_code}: {response.text}")

    return response.json()


def extract_first_coin(data, symbol):
    symbol = symbol.upper()

    if "data" not in data or symbol not in data["data"]:
        return None

    item = data["data"][symbol]

    if isinstance(item, list):
        if len(item) == 0:
            return None
        return item[0]

    return item

# =========================
# API COINALYZE
# =========================

def coinalyze_get(endpoint, params, api_key):
    base_url = "https://api.coinalyze.net/v1"
    url = f"{base_url}/{endpoint}"

    request_params = dict(params)
    request_params["api_key"] = api_key

    response = requests.get(url, params=request_params, timeout=20)

    st.session_state[f"debug_last_{endpoint}_status"] = response.status_code
    st.session_state[f"debug_last_{endpoint}_text"] = response.text[:800]

    if response.status_code != 200:
        raise Exception(f"Erreur Coinalyze {response.status_code}: {response.text}")

    return response.json()


@st.cache_data(ttl=1800)
def fetch_coinalyze_future_markets(api_key):
    return coinalyze_get("future-markets", {}, api_key)


@st.cache_data(ttl=600)
def fetch_coinalyze_funding(symbols_csv, api_key):
    if not symbols_csv:
        return []

    return coinalyze_get(
        "funding-rate",
        {"symbols": symbols_csv},
        api_key
    )


@st.cache_data(ttl=600)
def fetch_coinalyze_open_interest(symbols_csv, api_key):
    if not symbols_csv:
        return []

    return coinalyze_get(
        "open-interest",
        {
            "symbols": symbols_csv,
            "convert_to_usd": "true"
        },
        api_key
    )


@st.cache_data(ttl=600)
def fetch_coinalyze_oi_history(symbols_csv, interval, from_ts, to_ts, api_key):
    if not symbols_csv:
        return []

    return coinalyze_get(
        "open-interest-history",
        {
            "symbols": symbols_csv,
            "interval": interval,
            "from": from_ts,
            "to": to_ts,
            "convert_to_usd": "true"
        },
        api_key
    )


@st.cache_data(ttl=600)
def fetch_coinalyze_ohlcv_history(symbols_csv, interval, from_ts, to_ts, api_key):
    if not symbols_csv:
        return []

    return coinalyze_get(
        "ohlcv-history",
        {
            "symbols": symbols_csv,
            "interval": interval,
            "from": from_ts,
            "to": to_ts
        },
        api_key
    )

# =========================
# TIMEFRAMES
# =========================

def rounded_now():
    now = int(time.time())
    return now - (now % 300)


def get_pa_interval_and_range(comparison_label):
    now = rounded_now()

    if comparison_label == "1h":
        return "15min", now - 24 * 3600, now

    if comparison_label == "4h":
        return "30min", now - 3 * 24 * 3600, now

    if comparison_label == "12h":
        return "1hour", now - 5 * 24 * 3600, now

    if comparison_label == "1 jour":
        return "1hour", now - 7 * 24 * 3600, now

    if comparison_label == "7 jours":
        return "4hour", now - 21 * 24 * 3600, now

    if comparison_label == "30 jours":
        return "daily", now - 90 * 24 * 3600, now

    return "1hour", now - 7 * 24 * 3600, now


def get_oi_interval_and_range(comparison_label):
    now = rounded_now()

    if comparison_label == "1h":
        return "1hour", now - 3 * 3600, now

    if comparison_label == "4h":
        return "1hour", now - 8 * 3600, now

    if comparison_label == "12h":
        return "1hour", now - 18 * 3600, now

    if comparison_label == "1 jour":
        return "1hour", now - 30 * 3600, now

    if comparison_label == "7 jours":
        return "daily", now - 10 * 24 * 3600, now

    if comparison_label == "30 jours":
        return "daily", now - 40 * 24 * 3600, now

    return "1hour", now - 30 * 3600, now


def get_perf_from_quote(quote, comparison_label):
    if comparison_label in ["1h", "4h", "12h"]:
        return quote.get("percent_change_1h", 0) or 0

    if comparison_label == "1 jour":
        return quote.get("percent_change_24h", 0) or 0

    if comparison_label == "7 jours":
        return quote.get("percent_change_7d", 0) or 0

    if comparison_label == "30 jours":
        return quote.get("percent_change_30d", 0) or 0

    return 0

# =========================
# OUTILS
# =========================

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def map_list_by_symbol(items):
    result = {}

    for item in items:
        symbol = item.get("symbol")
        if symbol:
            result[symbol] = item

    return result


def fetch_ohlcv_in_chunks(coinalyze_symbols, api_key):
    if not coinalyze_symbols:
        return []

    interval, from_ts, to_ts = get_pa_interval_and_range(comparison_label)

    st.session_state["debug_ohlcv_interval"] = interval
    st.session_state["debug_ohlcv_from"] = from_ts
    st.session_state["debug_ohlcv_to"] = to_ts

    all_data = []
    chunk_size = 20

    for i in range(0, len(coinalyze_symbols), chunk_size):
        chunk = coinalyze_symbols[i:i + chunk_size]
        symbols_csv = ",".join(chunk)

        try:
            data = fetch_coinalyze_ohlcv_history(
                symbols_csv,
                interval,
                from_ts,
                to_ts,
                api_key
            )

            if isinstance(data, list):
                all_data.extend(data)

        except Exception as e:
            st.session_state["debug_ohlcv_error"] = str(e)

    return all_data

# =========================
# MATCHING COINALYZE
# =========================

def select_coinalyze_market(symbol, markets):
    symbol = symbol.upper()
    candidates = []

    for market in markets:
        base_asset = str(market.get("base_asset", "")).upper()
        quote_asset = str(market.get("quote_asset", "")).upper()
        is_perpetual = market.get("is_perpetual", False)
        margined = str(market.get("margined", "")).upper()

        if base_asset != symbol:
            continue

        if quote_asset not in ["USDT", "USD"]:
            continue

        if is_perpetual is not True:
            continue

        if margined not in ["STABLE", "USDT", "USD"]:
            continue

        candidates.append(market)

    if not candidates:
        return None

    def score_market(m):
        exchange = str(m.get("exchange", "")).lower()
        quote_asset = str(m.get("quote_asset", "")).upper()
        score = 0

        if quote_asset == "USDT":
            score += 30

        if m.get("has_ohlcv_data"):
            score += 30

        if m.get("has_buy_sell_data"):
            score += 10

        if m.get("has_long_short_ratio_data"):
            score += 10

        if m.get("is_perpetual"):
            score += 20

        if "binance" in exchange:
            score += 100
        elif "bybit" in exchange:
            score += 90
        elif "okx" in exchange:
            score += 80
        elif "bitget" in exchange:
            score += 70
        elif "gate" in exchange:
            score += 50

        return score

    candidates = sorted(candidates, key=score_market, reverse=True)
    return candidates[0]


def build_coinalyze_symbol_map(symbols, api_key):
    try:
        markets = fetch_coinalyze_future_markets(api_key)
    except Exception as e:
        st.session_state["debug_future_markets_error"] = str(e)
        markets = []

    st.session_state["debug_markets_count"] = len(markets)
    st.session_state["debug_markets_sample"] = markets[:5] if isinstance(markets, list) else markets

    result = {}

    for symbol in symbols:
        market = select_coinalyze_market(symbol, markets)

        if market is None:
            result[symbol] = {
                "coinalyze_symbol": None,
                "exchange": "N/A",
                "raw_market": None
            }
        else:
            result[symbol] = {
                "coinalyze_symbol": market.get("symbol"),
                "exchange": market.get("exchange", "N/A"),
                "raw_market": market
            }

    st.session_state["debug_symbol_map"] = result

    return result

# =========================
# PRICE ACTION RÉELLE
# =========================

def empty_pa_data():
    return {
        "PA réelle": "N/A",
        "Tendance bougies": "N/A",
        "Dernière bougie": "N/A",
        "Breakout réel": "N/A",
        "Position range réel %": "N/A",
        "Score PA Réel Long": 0,
        "Score PA Réel Short": 0,
        "High PA": "N/A",
        "Low PA": "N/A"
    }


def analyze_real_price_action(ohlcv_item):
    if not ohlcv_item:
        return empty_pa_data()

    history = ohlcv_item.get("history", [])

    if not history or len(history) < 8:
        data = empty_pa_data()
        data["PA réelle"] = "Données insuffisantes"
        return data

    candles = []

    for c in history:
        o = safe_float(c.get("o"))
        h = safe_float(c.get("h"))
        l = safe_float(c.get("l"))
        close = safe_float(c.get("c"))
        v = safe_float(c.get("v"))

        if o is None or h is None or l is None or close is None:
            continue

        candles.append({
            "o": o,
            "h": h,
            "l": l,
            "c": close,
            "v": v if v is not None else 0
        })

    if len(candles) < 8:
        data = empty_pa_data()
        data["PA réelle"] = "Données insuffisantes"
        return data

    last = candles[-1]
    previous = candles[:-1]

    highs = [x["h"] for x in candles]
    lows = [x["l"] for x in candles]
    volumes = [x["v"] for x in candles]

    high_range = max(highs)
    low_range = min(lows)
    close = last["c"]

    previous_high = max([x["h"] for x in previous[-8:]])
    previous_low = min([x["l"] for x in previous[-8:]])

    first_half = candles[:len(candles)//2]
    second_half = candles[len(candles)//2:]

    first_high = max([x["h"] for x in first_half])
    second_high = max([x["h"] for x in second_half])

    first_low = min([x["l"] for x in first_half])
    second_low = min([x["l"] for x in second_half])

    score_long = 0
    score_short = 0

    if second_high > first_high and second_low > first_low:
        trend = "HH/HL haussier"
        score_long += 18
    elif second_high < first_high and second_low < first_low:
        trend = "LH/LL baissier"
        score_short += 18
    elif second_high > first_high and second_low < first_low:
        trend = "Range élargi"
        score_long += 5
        score_short += 5
    else:
        trend = "Range / compression"
        score_long += 4
        score_short += 4

    if close > previous_high * 1.002:
        breakout = "Breakout réel"
        score_long += 18
    elif close < previous_low * 0.998:
        breakout = "Breakdown réel"
        score_short += 18
    else:
        breakout = "Pas de cassure"

    if high_range != low_range:
        range_position = ((close - low_range) / (high_range - low_range)) * 100
        range_position = round(range_position, 2)
    else:
        range_position = "N/A"

    if range_position != "N/A":
        if range_position > 75:
            score_long += 8
        elif range_position < 25:
            score_short += 8
        else:
            score_long += 3
            score_short += 3

    body = abs(last["c"] - last["o"])
    candle_range = last["h"] - last["l"]

    if candle_range > 0:
        body_ratio = body / candle_range
    else:
        body_ratio = 0

    if last["c"] > last["o"] and body_ratio > 0.55:
        last_candle = "Bougie impulsive verte"
        score_long += 10
    elif last["c"] < last["o"] and body_ratio > 0.55:
        last_candle = "Bougie impulsive rouge"
        score_short += 10
    elif last["c"] > last["o"]:
        last_candle = "Bougie verte modérée"
        score_long += 5
    elif last["c"] < last["o"]:
        last_candle = "Bougie rouge modérée"
        score_short += 5
    else:
        last_candle = "Doji / neutre"

    if len(volumes) >= 8:
        avg_volume = sum(volumes[-8:-1]) / len(volumes[-8:-1])
        last_volume = volumes[-1]

        if avg_volume > 0 and last_volume > avg_volume * 1.4:
            if last["c"] > last["o"]:
                score_long += 8
            elif last["c"] < last["o"]:
                score_short += 8

    if score_long >= 38 and score_long > score_short:
        pa_profile = "PA haussière forte"
    elif score_short >= 38 and score_short > score_long:
        pa_profile = "PA baissière forte"
    elif score_long >= 25 and score_long >= score_short:
        pa_profile = "PA haussière en construction"
    elif score_short >= 25 and score_short > score_long:
        pa_profile = "PA baissière en construction"
    else:
        pa_profile = "PA neutre"

    return {
        "PA réelle": pa_profile,
        "Tendance bougies": trend,
        "Dernière bougie": last_candle,
        "Breakout réel": breakout,
        "Position range réel %": range_position,
        "Score PA Réel Long": score_long,
        "Score PA Réel Short": score_short,
        "High PA": round(high_range, 6),
        "Low PA": round(low_range, 6)
    }

# =========================
# OI / FUNDING
# =========================

def get_oi_change_from_history(history_item):
    if not history_item:
        return "N/A"

    history = history_item.get("history", [])

    if not history or len(history) < 2:
        return "N/A"

    first = history[0].get("c")
    last = history[-1].get("c")

    try:
        first = float(first)
        last = float(last)

        if first == 0:
            return "N/A"

        return round(((last / first) - 1) * 100, 2)

    except Exception:
        return "N/A"


def classify_funding_bias(funding_value):
    if funding_value == "N/A" or funding_value is None:
        return "Neutre"

    try:
        value = float(funding_value)
    except Exception:
        return "Neutre"

    if value > 0.03:
        return "Haussier"

    if value < -0.02:
        return "Baissier"

    return "Neutre"


def classify_oi_bias(oi_change):
    if oi_change == "N/A" or oi_change is None:
        return "Neutre"

    try:
        value = float(oi_change)
    except Exception:
        return "Neutre"

    if value > 5:
        return "Haussier"

    if value < -5:
        return "Baissier"

    return "Neutre"


def calculate_futures_scores(funding_bias, oi_bias):
    if funding_bias == "Haussier":
        funding_long = 8
        funding_short = 4
    elif funding_bias == "Baissier":
        funding_long = 4
        funding_short = 8
    else:
        funding_long = 6
        funding_short = 6

    if oi_bias == "Haussier":
        oi_score = 8
    elif oi_bias == "Baissier":
        oi_score = 3
    else:
        oi_score = 5

    return funding_long + oi_score, funding_short + oi_score


def get_fallback_futures_data():
    data = {
        "Coinalyze symbol": "N/A",
        "Futures exchange": "N/A",
        "Funding %": "N/A",
        "Funding biais": "Neutre",
        "Open Interest": "N/A",
        "OI tendance": "Neutre",
        "OI variation %": "N/A",
        "Score Futures Long": 0,
        "Score Futures Short": 0
    }

    data.update(empty_pa_data())
    return data


def get_futures_data_for_symbols(symbols, api_key):
    if not api_key:
        return {symbol: get_fallback_futures_data() for symbol in symbols}

    symbol_map = build_coinalyze_symbol_map(symbols, api_key)

    coinalyze_symbols = [
        data["coinalyze_symbol"]
        for data in symbol_map.values()
        if data["coinalyze_symbol"]
    ]

    st.session_state["debug_coinalyze_symbols_used"] = coinalyze_symbols

    if not coinalyze_symbols:
        return {symbol: get_fallback_futures_data() for symbol in symbols}

    symbols_csv = ",".join(coinalyze_symbols)

    # Bougies toujours actives
    try:
        ohlcv_history = fetch_ohlcv_in_chunks(coinalyze_symbols, api_key)
    except Exception as e:
        st.session_state["debug_ohlcv_error"] = str(e)
        ohlcv_history = []

    # OI + funding optionnels
    if use_futures_confirm:
        try:
            funding_data = fetch_coinalyze_funding(symbols_csv, api_key)
        except Exception as e:
            st.session_state["debug_funding_error"] = str(e)
            funding_data = []

        try:
            oi_data = fetch_coinalyze_open_interest(symbols_csv, api_key)
        except Exception as e:
            st.session_state["debug_oi_error"] = str(e)
            oi_data = []

        interval, from_ts, to_ts = get_oi_interval_and_range(comparison_label)

        try:
            oi_history = fetch_coinalyze_oi_history(
                symbols_csv,
                interval,
                from_ts,
                to_ts,
                api_key
            )
        except Exception as e:
            st.session_state["debug_oi_history_error"] = str(e)
            oi_history = []
    else:
        funding_data = []
        oi_data = []
        oi_history = []

        st.session_state["debug_funding_error"] = "Désactivé"
        st.session_state["debug_oi_error"] = "Désactivé"
        st.session_state["debug_oi_history_error"] = "Désactivé"

    st.session_state["debug_funding_count"] = len(funding_data) if isinstance(funding_data, list) else "N/A"
    st.session_state["debug_oi_count"] = len(oi_data) if isinstance(oi_data, list) else "N/A"
    st.session_state["debug_oi_history_count"] = len(oi_history) if isinstance(oi_history, list) else "N/A"
    st.session_state["debug_ohlcv_count"] = len(ohlcv_history) if isinstance(ohlcv_history, list) else "N/A"

    funding_map = map_list_by_symbol(funding_data)
    oi_map = map_list_by_symbol(oi_data)
    oi_history_map = map_list_by_symbol(oi_history)
    ohlcv_history_map = map_list_by_symbol(ohlcv_history)

    result = {}

    for symbol in symbols:
        cz_symbol = symbol_map[symbol]["coinalyze_symbol"]
        exchange = symbol_map[symbol]["exchange"]

        if not cz_symbol:
            result[symbol] = get_fallback_futures_data()
            continue

        funding_item = funding_map.get(cz_symbol, {})
        oi_item = oi_map.get(cz_symbol, {})
        oi_history_item = oi_history_map.get(cz_symbol, {})
        ohlcv_item = ohlcv_history_map.get(cz_symbol, {})

        pa_real_data = analyze_real_price_action(ohlcv_item)

        funding_value = funding_item.get("value", "N/A")
        oi_value = oi_item.get("value", "N/A")
        oi_change = get_oi_change_from_history(oi_history_item)

        try:
            funding_value_clean = round(float(funding_value), 4)
        except Exception:
            funding_value_clean = "N/A"

        try:
            oi_value_clean = round(float(oi_value), 2)
        except Exception:
            oi_value_clean = "N/A"

        funding_bias = classify_funding_bias(funding_value_clean)
        oi_bias = classify_oi_bias(oi_change)

        if use_futures_confirm:
            futures_long, futures_short = calculate_futures_scores(
                funding_bias,
                oi_bias
            )
        else:
            futures_long, futures_short = 0, 0

        result[symbol] = {
            "Coinalyze symbol": cz_symbol,
            "Futures exchange": exchange,
            "Funding %": funding_value_clean,
            "Funding biais": funding_bias,
            "Open Interest": oi_value_clean,
            "OI tendance": oi_bias,
            "OI variation %": oi_change,
            "Score Futures Long": futures_long,
            "Score Futures Short": futures_short
        }

        result[symbol].update(pa_real_data)

    return result

# =========================
# SCORING
# =========================

def classify_structure(perf, force_vs_btc, comparison_label):
    if perf > 8 and force_vs_btc > 3:
        return f"Momentum haussier fort {comparison_label}", "Breakout relatif", 24, 2

    if perf > 3 and force_vs_btc > 0:
        return f"Pression acheteuse {comparison_label}", "Haut de momentum", 18, 5

    if perf < -8 and force_vs_btc < -3:
        return f"Momentum baissier fort {comparison_label}", "Breakdown relatif", 2, 24

    if perf < -3 and force_vs_btc < 0:
        return f"Pression vendeuse {comparison_label}", "Bas de momentum", 5, 18

    if -2 <= perf <= 2:
        return f"Range neutre {comparison_label}", "Milieu de range", 8, 8

    if perf > 0:
        return f"Léger biais haussier {comparison_label}", "Milieu de range", 12, 7

    return f"Léger biais baissier {comparison_label}", "Milieu de range", 7, 12


def calculate_volume_score(volume_24h, market_cap):
    if not market_cap or market_cap <= 0:
        return 3, "N/A"

    volume_ratio = (volume_24h / market_cap) * 100

    if volume_ratio > 20:
        return 15, round(volume_ratio, 2)

    if volume_ratio > 10:
        return 10, round(volume_ratio, 2)

    if volume_ratio > 3:
        return 6, round(volume_ratio, 2)

    return 2, round(volume_ratio, 2)


def calculate_momentum_scores(perf):
    if perf > 15:
        long_score = 20
    elif perf > 7:
        long_score = 15
    elif perf > 0:
        long_score = 10
    else:
        long_score = 3

    if perf < -15:
        short_score = 20
    elif perf < -7:
        short_score = 15
    elif perf < 0:
        short_score = 10
    else:
        short_score = 3

    return long_score, short_score


def calculate_force_scores(force_vs_btc):
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

    return force_score_long, force_score_short


def calculate_trend_scores(quote, force_vs_btc, funding_bias, oi_bias):
    perf_1h = quote.get("percent_change_1h", 0) or 0
    perf_24h = quote.get("percent_change_24h", 0) or 0
    perf_7d = quote.get("percent_change_7d", 0) or 0
    perf_30d = quote.get("percent_change_30d", 0) or 0

    trend_long = 0
    trend_short = 0
    trend_notes = []

    if comparison_label == "30 jours":
        if perf_30d > 0:
            trend_long += 8
            trend_notes.append("30j positif")
        elif perf_30d < 0:
            trend_short += 8

    if perf_7d > 0:
        trend_long += 7
        trend_notes.append("7j positif")
    elif perf_7d < 0:
        trend_short += 7

    if perf_24h > 0:
        trend_long += 5
        trend_notes.append("24h positif")
    elif perf_24h < 0:
        trend_short += 5

    if perf_1h > -1:
        trend_long += 3
        trend_notes.append("1h stable")
    elif perf_1h < 1:
        trend_short += 3

    if force_vs_btc > 0:
        trend_long += 5
        trend_notes.append("force vs BTC positive")
    elif force_vs_btc > -2:
        trend_long += 3
        trend_notes.append("force vs BTC correcte")

    if force_vs_btc < 0:
        trend_short += 5
    elif force_vs_btc < 2:
        trend_short += 3

    if use_futures_confirm and oi_bias == "Haussier":
        trend_long += 3
        trend_short += 3
        trend_notes.append("OI actif")

    if use_futures_confirm and funding_bias in ["Neutre", "Haussier"]:
        trend_long += 2

    if use_futures_confirm and funding_bias in ["Neutre", "Baissier"]:
        trend_short += 2

    if trend_long >= 18 and trend_long > trend_short:
        trend_profile = "Tendance haussière propre"
    elif trend_short >= 18 and trend_short > trend_long:
        trend_profile = "Tendance baissière propre"
    elif trend_long >= 14 and trend_long >= trend_short:
        trend_profile = "Biais haussier en construction"
    elif trend_short >= 14 and trend_short > trend_long:
        trend_profile = "Biais baissier en construction"
    else:
        trend_profile = "Tendance peu claire"

    return trend_long, trend_short, trend_profile, " / ".join(trend_notes)


def define_bias(score_long, score_short, mode):
    if mode == "Long uniquement":
        if score_long >= 110:
            return "Long spot potentiel", "Chercher entrée pullback long", "LONG"
        if score_long >= 80:
            return "Surveillance long", "Attendre confirmation long", "LONG"
        return "Pas prioritaire", "Rien à faire", "NONE"

    if mode == "Short uniquement":
        if score_short >= 110:
            return "Short potentiel", "Chercher entrée rebond short", "SHORT"
        if score_short >= 80:
            return "Surveillance short", "Attendre confirmation short", "SHORT"
        return "Pas prioritaire", "Rien à faire", "NONE"

    if score_long >= 110 and score_long > score_short:
        return "Long spot potentiel", "Chercher entrée pullback long", "LONG"

    if score_short >= 110 and score_short > score_long:
        return "Short potentiel", "Chercher entrée rebond short", "SHORT"

    if score_long >= 80 and score_long >= score_short:
        return "Surveillance long", "Attendre confirmation long", "LONG"

    if score_short >= 80 and score_short > score_long:
        return "Surveillance short", "Attendre confirmation short", "SHORT"

    return "Pas prioritaire", "Rien à faire", "NONE"

# =========================
# PLAN TRADING
# =========================

def trade_plan_long(price, stop_percent):
    entry = price * 0.99
    stop = entry * (1 - stop_percent / 100)
    risk_unit = entry - stop

    return {
        "Sens": "LONG",
        "Entrée": round(entry, 6),
        "Stop": round(stop, 6),
        "TP1": round(entry + risk_unit * 2, 6),
        "TP2": round(entry + risk_unit * 3, 6),
        "Cible range": round(price * 1.04, 6),
        "R/R TP1": 2.0,
        "R/R TP2": 3.0
    }


def trade_plan_short(price, stop_percent):
    entry = price * 1.01
    stop = entry * (1 + stop_percent / 100)
    risk_unit = stop - entry

    return {
        "Sens": "SHORT",
        "Entrée": round(entry, 6),
        "Stop": round(stop, 6),
        "TP1": round(entry - risk_unit * 2, 6),
        "TP2": round(entry - risk_unit * 3, 6),
        "Cible range": round(price * 0.96, 6),
        "R/R TP1": 2.0,
        "R/R TP2": 3.0
    }


def decision_reason(
    biais,
    sens,
    force_vs_btc,
    score_long,
    score_short,
    funding_bias,
    oi_bias,
    trend_profile,
    pa_real
):
    reasons = []

    if biais == "Pas prioritaire":
        if score_long < 80 and score_short < 80:
            reasons.append("Scores long/short trop faibles")

        if pa_real not in ["N/A", "Données insuffisantes"]:
            reasons.append(pa_real)

        if trend_profile != "Tendance peu claire":
            reasons.append(trend_profile)

        if -2 <= force_vs_btc <= 2:
            reasons.append("Suit trop BTC")

        if force_vs_btc < -2:
            reasons.append("Faible vs BTC")

        if force_vs_btc > 2:
            reasons.append("Surperforme BTC mais setup insuffisant")

        if use_futures_confirm:
            if funding_bias == "Neutre":
                reasons.append("Funding neutre")

            if oi_bias == "Neutre":
                reasons.append("OI neutre")

        if not reasons:
            reasons.append("Pas de confirmation suffisante")

        return " / ".join(reasons)

    if sens == "LONG":
        reasons.append("Setup long détecté")

        if pa_real in ["PA haussière forte", "PA haussière en construction"]:
            reasons.append(pa_real)

        if trend_profile in ["Tendance haussière propre", "Biais haussier en construction"]:
            reasons.append(trend_profile)

        reasons.append("Surperformance vs BTC" if force_vs_btc > 0 else "Force BTC faible")

        if use_futures_confirm:
            if funding_bias == "Haussier":
                reasons.append("Funding haussier")
            elif funding_bias == "Baissier":
                reasons.append("Funding baissier")

            if oi_bias == "Haussier":
                reasons.append("OI en hausse")
            elif oi_bias == "Baissier":
                reasons.append("OI en baisse")

        return " / ".join(reasons)

    if sens == "SHORT":
        reasons.append("Setup short détecté")

        if pa_real in ["PA baissière forte", "PA baissière en construction"]:
            reasons.append(pa_real)

        if trend_profile in ["Tendance baissière propre", "Biais baissier en construction"]:
            reasons.append(trend_profile)

        reasons.append("Faiblesse vs BTC" if force_vs_btc < 0 else "Short malgré force relative")

        return " / ".join(reasons)

    return "Pas de signal clair"


def build_row(symbol, coin, btc_perf, futures_data):
    quote = coin["quote"]["USD"]

    price = quote.get("price", 0) or 0
    perf = get_perf_from_quote(quote, comparison_label)
    force_vs_btc = perf - btc_perf

    volume_24h = quote.get("volume_24h", 0) or 0
    market_cap = quote.get("market_cap", 0) or 0

    structure, position_range, score_pa_long, score_pa_short = classify_structure(
        perf,
        force_vs_btc,
        comparison_label
    )

    volume_score, volume_ratio = calculate_volume_score(volume_24h, market_cap)

    momentum_long, momentum_short = calculate_momentum_scores(perf)
    force_long, force_short = calculate_force_scores(force_vs_btc)

    score_long_spot = score_pa_long + momentum_long + volume_score
    score_short_spot = score_pa_short + momentum_short + volume_score

    futures_long = futures_data.get("Score Futures Long", 0)
    futures_short = futures_data.get("Score Futures Short", 0)

    pa_real_long = futures_data.get("Score PA Réel Long", 0)
    pa_real_short = futures_data.get("Score PA Réel Short", 0)

    trend_long, trend_short, trend_profile, trend_notes = calculate_trend_scores(
        quote,
        force_vs_btc,
        futures_data.get("Funding biais", "Neutre"),
        futures_data.get("OI tendance", "Neutre")
    )

    score_long_total = (
        score_long_spot
        + force_long
        + futures_long
        + trend_long
        + pa_real_long
    )

    score_short_total = (
        score_short_spot
        + force_short
        + futures_short
        + trend_short
        + pa_real_short
    )

    biais, action, sens = define_bias(score_long_total, score_short_total, mode)

    if sens == "NONE":
        if mode == "Long uniquement":
            sens_plan = "LONG"
        elif mode == "Short uniquement":
            sens_plan = "SHORT"
        else:
            sens_plan = "LONG" if score_long_total >= score_short_total else "SHORT"
    else:
        sens_plan = sens

    if sens_plan == "LONG":
        plan = trade_plan_long(price, stop_percent)
    elif sens_plan == "SHORT":
        plan = trade_plan_short(price, stop_percent)
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

    if sens == "NONE":
        plan["Sens"] = f"{sens_plan} indicatif"

    reason = decision_reason(
        biais,
        sens,
        force_vs_btc,
        score_long_total,
        score_short_total,
        futures_data.get("Funding biais", "Neutre"),
        futures_data.get("OI tendance", "Neutre"),
        trend_profile,
        futures_data.get("PA réelle", "N/A")
    )

    row = {
        "Crypto": f"{symbol}/USD",
        "Nom": coin.get("name", symbol),
        "Prix": round(price, 6),
        f"Perf {comparison_label}": round(perf, 2),
        f"Force vs BTC {comparison_label}": round(force_vs_btc, 2),
        "Structure PA CMC": structure,
        "Position Range CMC": position_range,
        "PA réelle": futures_data.get("PA réelle", "N/A"),
        "Tendance bougies": futures_data.get("Tendance bougies", "N/A"),
        "Dernière bougie": futures_data.get("Dernière bougie", "N/A"),
        "Breakout réel": futures_data.get("Breakout réel", "N/A"),
        "Position range réel %": futures_data.get("Position range réel %", "N/A"),
        "High PA": futures_data.get("High PA", "N/A"),
        "Low PA": futures_data.get("Low PA", "N/A"),
        "Profil tendance": trend_profile,
        "Notes tendance": trend_notes,
        "Volume / Market Cap %": volume_ratio,
        "Score PA CMC Long": score_pa_long,
        "Score PA CMC Short": score_pa_short,
        "Score PA Réel Long": pa_real_long,
        "Score PA Réel Short": pa_real_short,
        "Score Volume": volume_score,
        "Score Momentum Long": momentum_long,
        "Score Momentum Short": momentum_short,
        "Score Force Long": force_long,
        "Score Force Short": force_short,
        "Score Long Spot": score_long_spot,
        "Score Short Spot": score_short_spot,
        "Score Futures Long": futures_long,
        "Score Futures Short": futures_short,
        "Score Tendance Long": trend_long,
        "Score Tendance Short": trend_short,
        "Score Long Total": score_long_total,
        "Score Short Total": score_short_total,
        "Priority Score": max(score_long_total, score_short_total),
        "Biais": biais,
        "Raison décision": reason,
        "Action": action,
        "Distance stop %": stop_percent,
        "Market Cap": round(market_cap, 2) if market_cap else "N/A",
        "Volume 24h": round(volume_24h, 2) if volume_24h else "N/A",
    }

    row.update(futures_data)
    row.update(plan)

    return row

# =========================
# SCAN
# =========================

if scan_button:
    cmc_api_key = get_secret("CMC_API_KEY")
    coinalyze_api_key = get_secret("COINALYZE_API_KEY")

    if not cmc_api_key:
        st.error("Clé API CoinMarketCap absente. Ajoute CMC_API_KEY dans les secrets Streamlit.")
        st.stop()

    if not coinalyze_api_key:
        st.warning("Clé API Coinalyze absente. L'app continue sans bougies/OI/funding.")

    symbols = [c.strip().upper() for c in watchlist.split(",") if c.strip()]
    symbols = symbols[:max_tokens]

    if "BTC" not in symbols:
        request_symbols = symbols + ["BTC"]
    else:
        request_symbols = symbols

    rows = []
    errors = []

    try:
        cmc_data = fetch_cmc_quotes(",".join(request_symbols), cmc_api_key)

        btc_coin = extract_first_coin(cmc_data, "BTC")
        if btc_coin is None:
            raise Exception("BTC non récupéré depuis CoinMarketCap.")

        btc_quote = btc_coin["quote"]["USD"]
        btc_perf = get_perf_from_quote(btc_quote, comparison_label)

        futures_map = get_futures_data_for_symbols(symbols, coinalyze_api_key)

        with st.expander("Debug Coinalyze", expanded=False):
            st.write("OI + Funding activés :")
            st.write(use_futures_confirm)

            st.write("Nombre de marchés futures Coinalyze trouvés :")
            st.write(st.session_state.get("debug_markets_count", "Non récupéré"))

            st.write("Matching symboles :")
            st.write(st.session_state.get("debug_symbol_map", {}))

            st.write("Symboles Coinalyze utilisés pour les endpoints :")
            st.write(st.session_state.get("debug_coinalyze_symbols_used", []))

            st.write("Nombre de réponses Funding / OI / OI history / OHLCV :")
            st.write({
                "funding": st.session_state.get("debug_funding_count", "N/A"),
                "oi": st.session_state.get("debug_oi_count", "N/A"),
                "oi_history": st.session_state.get("debug_oi_history_count", "N/A"),
                "ohlcv": st.session_state.get("debug_ohlcv_count", "N/A"),
            })

            st.write("Erreurs éventuelles :")
            st.write({
                "future_markets": st.session_state.get("debug_future_markets_error", None),
                "funding": st.session_state.get("debug_funding_error", None),
                "oi": st.session_state.get("debug_oi_error", None),
                "oi_history": st.session_state.get("debug_oi_history_error", None),
                "ohlcv": st.session_state.get("debug_ohlcv_error", None),
            })

        for symbol in symbols:
            try:
                coin = extract_first_coin(cmc_data, symbol)

                if coin is None:
                    errors.append(f"{symbol}: non trouvé sur CoinMarketCap")
                    continue

                futures_data = futures_map.get(symbol, get_fallback_futures_data())
                rows.append(build_row(symbol, coin, btc_perf, futures_data))

            except Exception as e:
                errors.append(f"{symbol}: {e}")

    except Exception as e:
        st.error(str(e))

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
            "PA réelle",
            "Tendance bougies",
            "Dernière bougie",
            "Breakout réel",
            "Position range réel %",
            "Profil tendance",
            "Funding biais",
            "OI tendance",
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

        st.subheader("Classement PA réelle + OI + Funding")
        st.dataframe(df_light, use_container_width=True)

        best = df.iloc[0]

        st.subheader("Stats du meilleur setup")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Crypto", best["Crypto"])
            st.metric("Sens", best["Sens"])

        with col2:
            st.metric("Score Long", f"{best['Score Long Total']}/170")
            st.metric("Score Short", f"{best['Score Short Total']}/170")

        with col3:
            st.metric("Perf", f"{best[perf_column_name]} %")
            st.metric("Force vs BTC", f"{best[force_column_name]} %")

        with col4:
            st.metric("PA réelle", best["PA réelle"])
            st.metric("Bougies", best["Tendance bougies"])

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
                best["PA réelle"],
                f"{best['Tendance bougies']} / {best['Dernière bougie']} / {best['Breakout réel']}"
            )

        with exp3:
            if use_futures_confirm:
                info_card(
                    "3. Futures",
                    f"Funding {best['Funding biais']} / OI {best['OI tendance']}",
                    f"OI variation : {best['OI variation %']} %."
                )
            else:
                info_card(
                    "3. Futures",
                    "Désactivé",
                    "Active OI + Funding dans la sidebar pour confirmation."
                )

        with exp4:
            info_card(
                "4. Décision",
                f"{best['Sens']} — {best['Biais']}",
                best["Action"]
            )

        with st.expander("Calcul technique complet", expanded=False):
            tech1, tech2, tech3, tech4 = st.columns(4)

            with tech1:
                info_card("Prix actuel", best["Prix"], f"Temporalité : {comparison_label}")
                info_card("Performance", f"{best[perf_column_name]} %", "Performance CMC.")
                info_card("Force vs BTC", f"{best[force_column_name]} %", "Écart face à BTC.")

            with tech2:
                info_card("PA réelle", best["PA réelle"], "Lecture bougies OHLCV.")
                info_card("Structure bougies", best["Tendance bougies"], best["Dernière bougie"])
                info_card("Breakout", best["Breakout réel"], f"Range réel : {best['Position range réel %']} %")

            with tech3:
                info_card("Score PA réel", f"L {best['Score PA Réel Long']} / S {best['Score PA Réel Short']}", "Bougies + range + volume.")
                info_card("Score Tendance", f"L {best['Score Tendance Long']} / S {best['Score Tendance Short']}", best["Profil tendance"])
                info_card("Score Force", f"L {best['Score Force Long']} / S {best['Score Force Short']}", "Force relative BTC.")

            with tech4:
                info_card("Score Futures", f"L {best['Score Futures Long']} / S {best['Score Futures Short']}", "Funding + OI.")
                info_card("Funding / OI", f"{best['Funding biais']} / {best['OI tendance']}", f"OI variation : {best['OI variation %']} %")
                info_card("Score final", f"L {best['Score Long Total']} / S {best['Score Short Total']}", "Scores finaux.")

        st.caption(
            "Prix/perf/volume : CoinMarketCap. Bougies : Coinalyze. "
            "OI + Funding sont optionnels pour limiter les erreurs 429."
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
            Version stable : bougies OHLCV actives, OI + Funding optionnels pour éviter les limites Coinalyze.
        </div>
    </div>
    """, unsafe_allow_html=True)