import time
import requests
import pandas as pd
import streamlit as st

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
    ["1h", "24h", "7 jours"]
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
    20,
    1
)

scan_button = st.sidebar.button("Scanner maintenant")

st.sidebar.caption(
    "CoinMarketCap = prix/perf/volume. Coinalyze = funding + open interest."
)

# =========================
# HEADER
# =========================

st.title("Crypto Agent IA — Scanner CoinMarketCap + Coinalyze")

st.markdown(f"""
<div class="top-box">
    <div class="top-title">Dashboard trading crypto</div>
    <div class="top-sub">
        Sources : <span class="yellow">CoinMarketCap + Coinalyze</span> —
        Temporalité : <span class="yellow">{comparison_label}</span> —
        Mode : <span class="yellow">{mode}</span> —
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

@st.cache_data(ttl=60)
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

    if response.status_code != 200:
        raise Exception(f"Erreur Coinalyze {response.status_code}: {response.text}")

    return response.json()


@st.cache_data(ttl=600)
def fetch_coinalyze_future_markets(api_key):
    return coinalyze_get("future-markets", {}, api_key)


@st.cache_data(ttl=60)
def fetch_coinalyze_funding(symbols_csv, api_key):
    if not symbols_csv:
        return []

    return coinalyze_get(
        "funding-rate",
        {"symbols": symbols_csv},
        api_key
    )


@st.cache_data(ttl=60)
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


@st.cache_data(ttl=120)
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


def get_oi_interval_and_range(comparison_label):
    now = int(time.time())

    if comparison_label == "1h":
        return "1hour", now - 3 * 3600, now

    if comparison_label == "24h":
        return "1hour", now - 26 * 3600, now

    return "daily", now - 9 * 24 * 3600, now


def select_coinalyze_market(symbol, markets):
    symbol = symbol.upper()

    candidates = []

    for market in markets:
        base = str(market.get("base_asset", "")).upper()
        quote = str(market.get("quote_asset", "")).upper()
        is_perp = bool(market.get("is_perpetual", False))
        margined = str(market.get("margined", "")).upper()

        if base != symbol:
            continue

        if quote not in ["USDT", "USD"]:
            continue

        if not is_perp:
            continue

        if margined not in ["STABLE", "USD", "USDT"]:
            continue

        candidates.append(market)

    if not candidates:
        return None

    def score_market(m):
        exchange = str(m.get("exchange", "")).lower()
        score = 0

        if "binance" in exchange:
            score += 100
        elif "bybit" in exchange:
            score += 80
        elif "okx" in exchange:
            score += 70
        elif "bitget" in exchange:
            score += 60

        if m.get("has_long_short_ratio_data"):
            score += 5

        if m.get("has_ohlcv_data"):
            score += 3

        return score

    candidates = sorted(candidates, key=score_market, reverse=True)
    return candidates[0]


def build_coinalyze_symbol_map(symbols, api_key):
    try:
        markets = fetch_coinalyze_future_markets(api_key)
    except Exception:
        markets = []

    result = {}

    for symbol in symbols:
        market = select_coinalyze_market(symbol, markets)

        if market is None:
            result[symbol] = {
                "coinalyze_symbol": None,
                "exchange": "N/A"
            }
        else:
            result[symbol] = {
                "coinalyze_symbol": market.get("symbol"),
                "exchange": market.get("exchange", "N/A")
            }

    return result


def map_list_by_symbol(items):
    result = {}

    for item in items:
        symbol = item.get("symbol")
        if symbol:
            result[symbol] = item

    return result


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
    funding_long = 0
    funding_short = 0
    oi_score = 0

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


def get_futures_data_for_symbols(symbols, api_key):
    if not api_key:
        return {
            symbol: {
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
            for symbol in symbols
        }

    symbol_map = build_coinalyze_symbol_map(symbols, api_key)
    coinalyze_symbols = [
        data["coinalyze_symbol"]
        for data in symbol_map.values()
        if data["coinalyze_symbol"]
    ]

    if not coinalyze_symbols:
        return {
            symbol: {
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
            for symbol in symbols
        }

    symbols_csv = ",".join(coinalyze_symbols)

    try:
        funding_data = fetch_coinalyze_funding(symbols_csv, api_key)
    except Exception:
        funding_data = []

    try:
        oi_data = fetch_coinalyze_open_interest(symbols_csv, api_key)
    except Exception:
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
    except Exception:
        oi_history = []

    funding_map = map_list_by_symbol(funding_data)
    oi_map = map_list_by_symbol(oi_data)
    oi_history_map = map_list_by_symbol(oi_history)

    result = {}

    for symbol in symbols:
        cz_symbol = symbol_map[symbol]["coinalyze_symbol"]
        exchange = symbol_map[symbol]["exchange"]

        if not cz_symbol:
            result[symbol] = {
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
            continue

        funding_item = funding_map.get(cz_symbol, {})
        oi_item = oi_map.get(cz_symbol, {})
        oi_history_item = oi_history_map.get(cz_symbol, {})

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

        futures_long, futures_short = calculate_futures_scores(
            funding_bias,
            oi_bias
        )

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

    return result


# =========================
# ANALYSE CMC
# =========================

def get_perf_from_quote(quote, comparison_label):
    if comparison_label == "1h":
        return quote.get("percent_change_1h", 0) or 0

    if comparison_label == "24h":
        return quote.get("percent_change_24h", 0) or 0

    if comparison_label == "7 jours":
        return quote.get("percent_change_7d", 0) or 0

    return 0


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


def define_bias(score_long, score_short, mode):
    if mode == "Long uniquement":
        if score_long >= 70:
            return "Long spot potentiel", "Chercher entrée pullback long", "LONG"
        if score_long >= 55:
            return "Surveillance long", "Attendre confirmation long", "LONG"
        return "Pas prioritaire", "Rien à faire", "NONE"

    if mode == "Short uniquement":
        if score_short >= 70:
            return "Short potentiel", "Chercher entrée rebond short", "SHORT"
        if score_short >= 55:
            return "Surveillance short", "Attendre confirmation short", "SHORT"
        return "Pas prioritaire", "Rien à faire", "NONE"

    if score_long >= 70 and score_long > score_short:
        return "Long spot potentiel", "Chercher entrée pullback long", "LONG"

    if score_short >= 70 and score_short > score_long:
        return "Short potentiel", "Chercher entrée rebond short", "SHORT"

    if score_long >= 55 and score_long >= score_short:
        return "Surveillance long", "Attendre confirmation long", "LONG"

    if score_short >= 55 and score_short > score_long:
        return "Surveillance short", "Attendre confirmation short", "SHORT"

    return "Pas prioritaire", "Rien à faire", "NONE"


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
    structure_pa,
    position_range,
    score_long,
    score_short,
    funding_bias,
    oi_bias
):
    reasons = []

    if biais == "Pas prioritaire":
        if score_long < 55 and score_short < 55:
            reasons.append("Scores long/short trop faibles")

        if -2 <= force_vs_btc <= 2:
            reasons.append("Suit trop BTC")

        if force_vs_btc < -2:
            reasons.append("Faible vs BTC")

        if force_vs_btc > 2:
            reasons.append("Surperforme BTC mais setup insuffisant")

        if "Range neutre" in structure_pa:
            reasons.append("Structure neutre")

        if position_range == "Milieu de range":
            reasons.append("Prix sans excès directionnel")

        if funding_bias == "Neutre":
            reasons.append("Funding neutre")

        if oi_bias == "Neutre":
            reasons.append("OI neutre")

        if not reasons:
            reasons.append("Pas de confirmation suffisante")

        return " / ".join(reasons)

    if sens == "LONG":
        reasons.append("Setup long détecté")
        reasons.append("Surperformance vs BTC" if force_vs_btc > 0 else "Force BTC faible")

        if "Momentum haussier" in structure_pa:
            reasons.append("Momentum haussier")
        elif "Pression acheteuse" in structure_pa:
            reasons.append("Pression acheteuse")

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
        reasons.append("Faiblesse vs BTC" if force_vs_btc < 0 else "Short malgré force relative")

        if "Momentum baissier" in structure_pa:
            reasons.append("Momentum baissier")
        elif "Pression vendeuse" in structure_pa:
            reasons.append("Pression vendeuse")

        if funding_bias == "Haussier":
            reasons.append("Funding haussier")
        elif funding_bias == "Baissier":
            reasons.append("Funding baissier")

        if oi_bias == "Haussier":
            reasons.append("OI en hausse")
        elif oi_bias == "Baissier":
            reasons.append("OI en baisse")

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

    score_long_total = score_long_spot + force_long + futures_long
    score_short_total = score_short_spot + force_short + futures_short

    biais, action, sens = define_bias(score_long_total, score_short_total, mode)

    if sens == "LONG":
        plan = trade_plan_long(price, stop_percent)
    elif sens == "SHORT":
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

    reason = decision_reason(
        biais,
        sens,
        force_vs_btc,
        structure,
        position_range,
        score_long_total,
        score_short_total,
        futures_data.get("Funding biais", "Neutre"),
        futures_data.get("OI tendance", "Neutre")
    )

    row = {
        "Crypto": f"{symbol}/USD",
        "Nom": coin.get("name", symbol),
        "Prix": round(price, 6),
        f"Perf {comparison_label}": round(perf, 2),
        f"Force vs BTC {comparison_label}": round(force_vs_btc, 2),
        "Structure PA": structure,
        "Position Range": position_range,
        "Volume / Market Cap %": volume_ratio,
        "Score PA Long": score_pa_long,
        "Score PA Short": score_pa_short,
        "Score Volume": volume_score,
        "Score Momentum Long": momentum_long,
        "Score Momentum Short": momentum_short,
        "Score Force Long": force_long,
        "Score Force Short": force_short,
        "Score Long Spot": score_long_spot,
        "Score Short Spot": score_short_spot,
        "Score Futures Long": futures_long,
        "Score Futures Short": futures_short,
        "Score Long Total": score_long_total,
        "Score Short Total": score_short_total,
        "Priority Score": max(score_long_total, score_short_total),
        "Biais": biais,
        "Raison décision": reason,
        "Action": action,
        "Distance stop %": stop_percent,
        "Market Cap": round(market_cap, 2) if market_cap else "N/A",
        "Volume 24h": round(volume_24h, 2) if volume_24h else "N/A",
        "High période": "N/A",
        "Low période": "N/A",
        "High précédent": "N/A",
        "Low précédent": "N/A",
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
        st.warning("Clé API Coinalyze absente. L'app continue sans funding/open interest.")

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

        for symbol in symbols:
            try:
                coin = extract_first_coin(cmc_data, symbol)

                if coin is None:
                    errors.append(f"{symbol}: non trouvé sur CoinMarketCap")
                    continue

                futures_data = futures_map.get(symbol, {})
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
            "Structure PA",
            "Position Range",
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

        st.subheader("Classement CoinMarketCap + Coinalyze")
        st.dataframe(df_light, use_container_width=True)

        best = df.iloc[0]

        st.subheader("Stats du meilleur setup")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Crypto", best["Crypto"])
            st.metric("Sens", best["Sens"])

        with col2:
            st.metric("Score Long", f"{best['Score Long Total']}/95")
            st.metric("Score Short", f"{best['Score Short Total']}/95")

        with col3:
            st.metric("Perf", f"{best[perf_column_name]} %")
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
                "2. Momentum",
                best["Structure PA"],
                f"Position actuelle : {best['Position Range']}."
            )

        with exp3:
            info_card(
                "3. Futures",
                f"Funding {best['Funding biais']} / OI {best['OI tendance']}",
                f"OI variation : {best['OI variation %']} %."
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
                info_card("Performance", f"{best[perf_column_name]} %", "Performance du token.")
                info_card("Force vs BTC", f"{best[force_column_name]} %", "Écart face à BTC.")

            with tech2:
                info_card("Structure", best["Structure PA"], "Lecture momentum.")
                info_card("Position", best["Position Range"], "Zone actuelle du prix.")
                info_card("Volume / Market Cap", f"{best['Volume / Market Cap %']} %", "Activité relative du marché.")

            with tech3:
                info_card("Score Long Spot", best["Score Long Spot"], "Momentum + volume.")
                info_card("Score Short Spot", best["Score Short Spot"], "Momentum + volume.")
                info_card("Score Force", f"L {best['Score Force Long']} / S {best['Score Force Short']}", "Force relative BTC.")

            with tech4:
                info_card("Score Futures", f"L {best['Score Futures Long']} / S {best['Score Futures Short']}", "Funding + OI.")
                info_card("Funding / OI", f"{best['Funding biais']} / {best['OI tendance']}", f"OI variation : {best['OI variation %']} %")
                info_card("Score final", f"L {best['Score Long Total']} / S {best['Score Short Total']}", "Scores finaux.")

            tech5, tech6, tech7, tech8 = st.columns(4)

            with tech5:
                info_card("Market Cap", best["Market Cap"], "Capitalisation.")
                info_card("Volume 24h", best["Volume 24h"], "Volume spot global.")

            with tech6:
                info_card("Funding brut", f"{best['Funding %']} %", f"Biais : {best['Funding biais']}")
                info_card("Open Interest brut", best["Open Interest"], f"Exchange : {best['Futures exchange']}")

            with tech7:
                info_card("Entrée", best["Entrée"], f"Sens : {best['Sens']}")
                info_card("Stop", best["Stop"], f"Distance : {best['Distance stop %']} %")

            with tech8:
                info_card("TP1 / TP2", f"{best['TP1']} / {best['TP2']}", "Objectifs en R/R.")
                info_card("Cible range", best["Cible range"], "Objectif indicatif.")

        st.caption(
            "Prix/perf/volume : CoinMarketCap. Funding/open interest : Coinalyze. "
            "Si un token n'a pas de marché futures reconnu par Coinalyze, l'app continue avec les données spot."
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
            Cette version utilise CoinMarketCap + Coinalyze pour éviter le blocage Binance sur Streamlit Cloud.
        </div>
    </div>
    """, unsafe_allow_html=True)