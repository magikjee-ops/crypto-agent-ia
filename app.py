import time
import json
import hashlib
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Crypto Agent IA V9.2", layout="wide")

DEFAULT_WATCHLIST = (
    "ENA, SUI, IMX, NEIRO, AUCTION, PENGU, TON, LINK, ADA, HYPER, TAO, WLFI, "
    "BNB, ONDO, SOL, SYRUP, ZEC, NEAR, SUN, RENDER, MORPHO, BCH, DASH"
)

ALL_COLUMNS = [
    "Crypto", "Top surveillance", "Direction probable", "Statut tradable", "Pourquoi",
    "Structure 1h", "Structure 4h", "Structure 1j", "Force relative vs BTC",
    "Volume et momentum", "OI / Funding / Liquidité", "Plan", "Entrée idéale",
    "Zone d’invalidation", "Score risque", "Alerte mouvement avancé", "Décision finale",
    "Prix", "Score Long", "Score Short", "Range position", "Breakout",
    "Dernière bougie", "Funding %", "OI variation %"
]

DEFAULT_COLUMNS = [
    "Crypto", "Top surveillance", "Direction probable", "Statut tradable", "Pourquoi",
    "Structure 1h", "Structure 4h", "Structure 1j", "Force relative vs BTC",
    "Volume et momentum", "OI / Funding / Liquidité", "Plan", "Entrée idéale",
    "Zone d’invalidation", "Score risque", "Alerte mouvement avancé", "Décision finale"
]

COLUMN_PRESETS = {
    "Essentiel": [
        "Crypto",
        "Top surveillance",
        "Direction probable",
        "Statut tradable",
        "Pourquoi",
        "Plan",
        "Entrée idéale",
        "Zone d’invalidation",
        "Score risque",
        "Décision finale"
    ],
    "Setup trading": [
        "Crypto",
        "Direction probable",
        "Statut tradable",
        "Pourquoi",
        "Structure 1h",
        "Structure 4h",
        "Structure 1j",
        "Force relative vs BTC",
        "Volume et momentum",
        "Plan",
        "Entrée idéale",
        "Zone d’invalidation",
        "Alerte mouvement avancé",
        "Décision finale"
    ],
    "Structure": [
        "Crypto",
        "Top surveillance",
        "Structure 1h",
        "Structure 4h",
        "Structure 1j",
        "Force relative vs BTC",
        "Volume et momentum",
        "Breakout",
        "Range position",
        "Dernière bougie"
    ],
    "Risque": [
        "Crypto",
        "Direction probable",
        "Statut tradable",
        "Score risque",
        "Alerte mouvement avancé",
        "Zone d’invalidation",
        "Pourquoi",
        "Décision finale"
    ],
    "Futures": [
        "Crypto",
        "Direction probable",
        "OI / Funding / Liquidité",
        "Funding %",
        "OI variation %",
        "Score risque",
        "Décision finale"
    ],
    "Complet": ALL_COLUMNS
}

MODE_OPTIONS = ["Long + Short", "Long uniquement", "Short uniquement"]

st.markdown("""
<style>
.stApp {background-color:#0B0E11;color:#EAECEF;}
section[data-testid="stSidebar"] {background-color:#181A20;border-right:1px solid #2B3139;}
h1,h2,h3 {color:#F0B90B!important;}
.block-container {padding-top:1.5rem;}
div[data-testid="stMetric"] {background-color:#181A20;border:1px solid #2B3139;padding:16px;border-radius:12px;}
div[data-testid="stMetricLabel"] {color:#848E9C!important;}
div[data-testid="stMetricValue"] {color:#EAECEF!important;font-size:1.05rem;}
.binance-card {background-color:#181A20;border:1px solid #2B3139;border-radius:12px;padding:16px;min-height:110px;margin-bottom:12px;}
.binance-card-title {color:#848E9C;font-size:.85rem;margin-bottom:8px;}
.binance-card-value {color:#EAECEF;font-size:1rem;font-weight:600;}
.yellow {color:#F0B90B;font-weight:700;}
.small-text {color:#848E9C;font-size:.88rem;}
.stButton>button {
    background-color:#F0B90B;
    color:#0B0E11;
    border:none;
    font-weight:700;
    border-radius:10px;
    padding:.55rem .35rem;
    width:100%;
    white-space:nowrap;
    font-size:.82rem;
}
.stButton>button:hover {background-color:#FFD33D;color:#0B0E11;border:none;}
.top-box {background-color:#181A20;border:1px solid #2B3139;border-radius:12px;padding:14px 18px;margin-bottom:16px;}
.top-title {color:#F0B90B;font-weight:700;font-size:1rem;}
.top-sub {color:#848E9C;font-size:.9rem;}
.profile-box {
    background-color:#123B2A;
    border:1px solid #1F6B46;
    border-radius:12px;
    padding:12px 14px;
    color:#42F59B;
    font-weight:700;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# SECRETS / SUPABASE
# =========================

def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return None


def hash_pin(pin):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def supabase_ready():
    return bool(get_secret("SUPABASE_URL")) and bool(get_secret("SUPABASE_SERVICE_ROLE_KEY"))


def supabase_url():
    base = get_secret("SUPABASE_URL")
    if not base:
        return None
    return base.rstrip("/") + "/rest/v1/trading_profiles"


def supabase_headers(prefer=True):
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    if prefer:
        headers["Prefer"] = "return=representation"

    return headers


def parse_columns(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = DEFAULT_COLUMNS

    if not isinstance(value, list):
        value = DEFAULT_COLUMNS

    value = [c for c in value if c in ALL_COLUMNS]

    return value if value else DEFAULT_COLUMNS


def detect_columns_preset(columns):
    columns = parse_columns(columns)

    for preset_name, preset_columns in COLUMN_PRESETS.items():
        if columns == preset_columns:
            return preset_name

    if columns == ALL_COLUMNS:
        return "Complet"

    return "Essentiel"


def get_profile(profile_name, pin_hash):
    response = requests.get(
        supabase_url(),
        headers=supabase_headers(),
        params={
            "profile_name": f"eq.{profile_name}",
            "pin_hash": f"eq.{pin_hash}",
            "select": "*"
        },
        timeout=20
    )

    if response.status_code != 200:
        raise Exception(f"Erreur Supabase lecture {response.status_code}: {response.text}")

    data = response.json()

    return data[0] if data else None


def create_profile(profile_name, pin):
    if not supabase_ready():
        raise Exception("Secrets Supabase absents.")

    if not profile_name or not pin:
        raise Exception("Nom de profil et PIN obligatoires.")

    if len(pin) < 4:
        raise Exception("Le PIN doit faire au moins 4 caractères.")

    pin_hash = hash_pin(pin)
    existing = get_profile(profile_name, pin_hash)

    if existing:
        raise Exception("Ce profil existe déjà. Utilise Charger profil.")

    payload = {
        "profile_name": profile_name,
        "pin_hash": pin_hash,
        "watchlist": DEFAULT_WATCHLIST,
        "selected_columns": DEFAULT_COLUMNS,
        "mode": "Long + Short",
        "stop_percent": 1.0,
        "max_tokens": 10,
        "use_futures_confirm": False,
    }

    response = requests.post(
        supabase_url(),
        headers=supabase_headers(),
        data=json.dumps(payload),
        timeout=20
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"Erreur Supabase création {response.status_code}: {response.text}")

    return response.json()[0]


def load_profile(profile_name, pin):
    if not supabase_ready():
        raise Exception("Secrets Supabase absents.")

    if not profile_name or not pin:
        raise Exception("Nom de profil et PIN obligatoires.")

    pin_hash = hash_pin(pin)
    profile = get_profile(profile_name, pin_hash)

    if not profile:
        raise Exception("Profil introuvable ou PIN incorrect.")

    return profile


def update_profile(profile_name, pin_hash, payload):
    if not supabase_ready():
        raise Exception("Secrets Supabase absents.")

    if not profile_name or not pin_hash:
        raise Exception("Aucun profil connecté.")

    clean_payload = {
        "watchlist": payload["watchlist"],
        "selected_columns": payload["selected_columns"],
        "mode": payload["mode"],
        "stop_percent": payload["stop_percent"],
        "max_tokens": payload["max_tokens"],
        "use_futures_confirm": payload["use_futures_confirm"],
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    response = requests.patch(
        supabase_url(),
        headers=supabase_headers(),
        params={
            "profile_name": f"eq.{profile_name}",
            "pin_hash": f"eq.{pin_hash}"
        },
        data=json.dumps(clean_payload),
        timeout=20
    )

    if response.status_code not in [200, 204]:
        raise Exception(f"Erreur Supabase sauvegarde {response.status_code}: {response.text}")

    return True


def delete_profile(profile_name, pin_hash):
    if not supabase_ready():
        raise Exception("Secrets Supabase absents.")

    if not profile_name or not pin_hash:
        raise Exception("Aucun profil connecté.")

    response = requests.delete(
        supabase_url(),
        headers=supabase_headers(False),
        params={
            "profile_name": f"eq.{profile_name}",
            "pin_hash": f"eq.{pin_hash}"
        },
        timeout=20
    )

    if response.status_code not in [200, 204]:
        raise Exception(f"Erreur Supabase suppression {response.status_code}: {response.text}")

    return True


def apply_profile_to_session(profile):
    st.session_state["watchlist_input"] = profile.get("watchlist", DEFAULT_WATCHLIST)

    loaded_mode = profile.get("mode", "Long + Short")
    if loaded_mode not in MODE_OPTIONS:
        loaded_mode = "Long + Short"

    loaded_columns = parse_columns(profile.get("selected_columns", DEFAULT_COLUMNS))

    st.session_state["mode_input"] = loaded_mode
    st.session_state["stop_input"] = float(profile.get("stop_percent", 1.0))
    st.session_state["max_tokens_input"] = int(profile.get("max_tokens", 10))
    st.session_state["use_futures_confirm_input"] = bool(profile.get("use_futures_confirm", False))
    st.session_state["columns_input"] = loaded_columns
    st.session_state["columns_preset_input"] = detect_columns_preset(loaded_columns)
    st.session_state["profile_connected"] = True
    st.session_state["logged_profile_name"] = profile.get("profile_name")
    st.session_state["logged_profile_pin_hash"] = profile.get("pin_hash")


# =========================
# SESSION DEFAULTS
# =========================

for key, value in {
    "watchlist_input": DEFAULT_WATCHLIST,
    "mode_input": "Long + Short",
    "stop_input": 1.0,
    "max_tokens_input": 10,
    "use_futures_confirm_input": False,
    "columns_input": DEFAULT_COLUMNS,
    "columns_preset_input": "Essentiel",
    "profile_connected": False,
    "logged_profile_name": None,
    "logged_profile_pin_hash": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state["mode_input"] not in MODE_OPTIONS:
    st.session_state["mode_input"] = "Long + Short"

if not isinstance(st.session_state["columns_input"], list):
    st.session_state["columns_input"] = DEFAULT_COLUMNS

st.session_state["columns_input"] = [
    c for c in st.session_state["columns_input"]
    if c in ALL_COLUMNS
]

if not st.session_state["columns_input"]:
    st.session_state["columns_input"] = DEFAULT_COLUMNS

if st.session_state["columns_preset_input"] not in COLUMN_PRESETS:
    st.session_state["columns_preset_input"] = detect_columns_preset(st.session_state["columns_input"])

st.session_state["stop_input"] = max(0.25, min(5.0, float(st.session_state["stop_input"])))
st.session_state["max_tokens_input"] = max(5, min(30, int(st.session_state["max_tokens_input"])))


# =========================
# SIDEBAR
# =========================

st.sidebar.title("Paramètres V9.2")

with st.sidebar.expander("Profil utilisateur", expanded=True):
    if not st.session_state["profile_connected"]:
        profile_action = st.radio(
            "Action",
            ["Créer un profil", "Charger un profil existant"],
            horizontal=False
        )

        if profile_action == "Créer un profil":
            create_name = st.text_input("Nom du nouveau profil", key="create_profile_name")
            create_pin = st.text_input("Créer un PIN", type="password", key="create_profile_pin")
            confirm_pin = st.text_input("Confirmer le PIN", type="password", key="confirm_profile_pin")

            if st.button("Créer le profil"):
                try:
                    if create_pin != confirm_pin:
                        raise Exception("Les deux PIN ne correspondent pas.")

                    profile = create_profile(create_name, create_pin)
                    apply_profile_to_session(profile)

                    st.success("Profil créé et connecté.")
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

        else:
            load_name = st.text_input("Nom du profil", key="load_profile_name")
            load_pin = st.text_input("PIN", type="password", key="load_profile_pin")

            if st.button("Charger le profil"):
                try:
                    profile = load_profile(load_name, load_pin)
                    apply_profile_to_session(profile)

                    st.success("Profil chargé.")
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    else:
        st.markdown(
            f"<div class='profile-box'>Connecté : {st.session_state['logged_profile_name']}</div>",
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns(2, gap="small")

        with col_a:
            if st.button("Déconnexion", key="logout_btn"):
                st.session_state["profile_connected"] = False
                st.session_state["logged_profile_name"] = None
                st.session_state["logged_profile_pin_hash"] = None
                st.rerun()

        with col_b:
            if st.button("Supprimer", key="delete_profile_btn"):
                try:
                    delete_profile(
                        st.session_state["logged_profile_name"],
                        st.session_state["logged_profile_pin_hash"]
                    )

                    st.session_state["profile_connected"] = False
                    st.session_state["logged_profile_name"] = None
                    st.session_state["logged_profile_pin_hash"] = None

                    st.success("Profil supprimé.")
                    st.rerun()

                except Exception as e:
                    st.error(str(e))


with st.sidebar.expander("Watchlist", expanded=False):
    watchlist = st.text_area(
        "Panier de cryptos",
        height=180,
        key="watchlist_input"
    )

comparison_label = st.sidebar.selectbox(
    "Temporalité principale",
    ["1h", "4h", "12h", "1 jour", "7 jours", "30 jours"]
)

mode = st.sidebar.selectbox(
    "Mode d'analyse",
    MODE_OPTIONS,
    key="mode_input"
)

stop_percent = st.sidebar.slider(
    "Distance stop / invalidation (%)",
    min_value=0.25,
    max_value=5.0,
    step=0.25,
    key="stop_input"
)

max_tokens = st.sidebar.slider(
    "Nombre max de cryptos à scanner",
    min_value=5,
    max_value=30,
    step=1,
    key="max_tokens_input"
)

use_futures_confirm = st.sidebar.checkbox(
    "Activer OI + Funding",
    key="use_futures_confirm_input"
)

st.sidebar.markdown("### Affichage du tableau")

if st.sidebar.button("Reset tableau complet", key="reset_table_btn"):
    st.session_state["columns_preset_input"] = "Complet"
    st.session_state["columns_input"] = ALL_COLUMNS.copy()
    st.rerun()

display_preset = st.sidebar.selectbox(
    "Mode d'affichage",
    options=list(COLUMN_PRESETS.keys()),
    key="columns_preset_input"
)

selected_columns = COLUMN_PRESETS.get(display_preset, DEFAULT_COLUMNS)
st.session_state["columns_input"] = selected_columns

if st.session_state["profile_connected"]:
    if st.sidebar.button("Sauvegarder mes paramètres"):
        try:
            payload = {
                "watchlist": st.session_state["watchlist_input"],
                "selected_columns": selected_columns,
                "mode": st.session_state["mode_input"],
                "stop_percent": float(st.session_state["stop_input"]),
                "max_tokens": int(st.session_state["max_tokens_input"]),
                "use_futures_confirm": bool(st.session_state["use_futures_confirm_input"])
            }

            update_profile(
                st.session_state["logged_profile_name"],
                st.session_state["logged_profile_pin_hash"],
                payload
            )

            st.sidebar.success("Paramètres sauvegardés.")

        except Exception as e:
            st.sidebar.error(str(e))
else:
    st.sidebar.info("Crée ou charge un profil pour sauvegarder tes paramètres.")

scan_button = st.sidebar.button("Scanner maintenant")

if use_futures_confirm:
    st.sidebar.caption("Mode complet : PA + OI + Funding. Plus lourd pour Coinalyze.")
else:
    st.sidebar.caption("Mode stable : PA réelle uniquement. OI + Funding désactivés.")


# =========================
# HEADER
# =========================

st.title("Crypto Agent IA V9.2 — Profils + Agent Setup Trading")

futures_status = "activés" if use_futures_confirm else "désactivés"

st.markdown(f"""
<div class="top-box">
    <div class="top-title">Scanner de setups — profils propres</div>
    <div class="top-sub">
        Profil : <span class="yellow">{st.session_state["logged_profile_name"] or "non connecté"}</span><br>
        Temporalité : <span class="yellow">{comparison_label}</span> —
        Mode : <span class="yellow">{mode}</span> —
        Stop : <span class="yellow">{stop_percent} %</span> —
        OI/Funding : <span class="yellow">{futures_status}</span> —
        Affichage : <span class="yellow">{display_preset}</span>
    </div>
</div>
""", unsafe_allow_html=True)


def info_card(title, value, extra=""):
    st.markdown(f"""
    <div class="binance-card">
        <div class="binance-card-title">{title}</div>
        <div class="binance-card-value">{value}</div>
        <div class="small-text">{extra}</div>
    </div>
    """, unsafe_allow_html=True)


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
    url = f"https://api.coinalyze.net/v1/{endpoint}"

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


def get_pa_interval_and_range(label):
    now = rounded_now()

    if label == "1h":
        return "15min", now - 24 * 3600, now

    if label == "4h":
        return "15min", now - 2 * 24 * 3600, now

    if label == "12h":
        return "15min", now - 3 * 24 * 3600, now

    if label == "1 jour":
        return "15min", now - 5 * 24 * 3600, now

    if label == "7 jours":
        return "15min", now - 10 * 24 * 3600, now

    if label == "30 jours":
        return "15min", now - 20 * 24 * 3600, now

    return "15min", now - 24 * 3600, now


def get_oi_interval_and_range(label):
    now = rounded_now()

    if label in ["1h", "4h", "12h", "1 jour"]:
        return "1hour", now - 30 * 3600, now

    if label == "7 jours":
        return "daily", now - 10 * 24 * 3600, now

    if label == "30 jours":
        return "daily", now - 40 * 24 * 3600, now

    return "1hour", now - 30 * 3600, now


def get_perf_from_quote(quote, label):
    if label in ["1h", "4h", "12h"]:
        return quote.get("percent_change_1h", 0) or 0

    if label == "1 jour":
        return quote.get("percent_change_24h", 0) or 0

    if label == "7 jours":
        return quote.get("percent_change_7d", 0) or 0

    if label == "30 jours":
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
    chunk_size = 5
    total_chunks = (len(coinalyze_symbols) + chunk_size - 1) // chunk_size

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(0, len(coinalyze_symbols), chunk_size):
        chunk_number = (i // chunk_size) + 1
        chunk = coinalyze_symbols[i:i + chunk_size]
        symbols_csv = ",".join(chunk)

        status_text.info(f"Récupération bougies Coinalyze : paquet {chunk_number}/{total_chunks}")

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

        progress_bar.progress(chunk_number / total_chunks)
        time.sleep(1.2)

    status_text.success("Bougies récupérées.")

    return all_data


# =========================
# COINALYZE MATCHING
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
        score = 0

        if str(m.get("quote_asset", "")).upper() == "USDT":
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

    return sorted(candidates, key=score_market, reverse=True)[0]


def build_coinalyze_symbol_map(symbols, api_key):
    try:
        markets = fetch_coinalyze_future_markets(api_key)
    except Exception as e:
        st.session_state["debug_future_markets_error"] = str(e)
        markets = []

    st.session_state["debug_markets_count"] = len(markets)

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
# STRUCTURE / PRICE ACTION
# =========================

def candles_from_ohlcv_item(ohlcv_item):
    if not ohlcv_item:
        return []

    candles = []

    for c in ohlcv_item.get("history", []):
        o = safe_float(c.get("o"))
        h = safe_float(c.get("h"))
        l = safe_float(c.get("l"))
        close = safe_float(c.get("c"))
        v = safe_float(c.get("v"))
        t = c.get("t")

        if o is None or h is None or l is None or close is None:
            continue

        candles.append({
            "t": t,
            "o": o,
            "h": h,
            "l": l,
            "c": close,
            "v": v if v is not None else 0
        })

    return candles


def select_last_hours(candles, hours):
    if not candles:
        return []

    now = int(time.time())
    min_ts = now - hours * 3600

    timed = [c for c in candles if c.get("t") is not None]

    if timed:
        selected = [c for c in timed if int(c["t"]) >= min_ts]

        if len(selected) >= 8:
            return selected

    approx_count = max(8, int(hours * 4))

    return candles[-approx_count:]


def analyze_structure(candles, label):
    if not candles or len(candles) < 8:
        return {
            "label": label,
            "structure": "N/A",
            "score_long": 0,
            "score_short": 0,
            "range_position": "N/A",
            "last_candle": "N/A",
            "breakout": "N/A",
            "advanced": False,
            "compression": False
        }

    last = candles[-1]
    previous = candles[:-1]

    highs = [x["h"] for x in candles]
    lows = [x["l"] for x in candles]
    volumes = [x["v"] for x in candles]

    high_range = max(highs)
    low_range = min(lows)
    close = last["c"]

    first_half = candles[:len(candles) // 2]
    second_half = candles[len(candles) // 2:]

    first_high = max([x["h"] for x in first_half])
    second_high = max([x["h"] for x in second_half])

    first_low = min([x["l"] for x in first_half])
    second_low = min([x["l"] for x in second_half])

    score_long = 0
    score_short = 0

    if second_high > first_high and second_low > first_low:
        structure = "Haussière HH/HL"
        score_long += 25
    elif second_high < first_high and second_low < first_low:
        structure = "Baissière LH/LL"
        score_short += 25
    elif second_high > first_high and second_low < first_low:
        structure = "Range élargi"
        score_long += 7
        score_short += 7
    else:
        structure = "Compression / range"
        score_long += 10
        score_short += 10

    previous_high = max([x["h"] for x in previous[-8:]])
    previous_low = min([x["l"] for x in previous[-8:]])

    if close > previous_high * 1.002:
        breakout = "Breakout"
        score_long += 20
    elif close < previous_low * 0.998:
        breakout = "Breakdown"
        score_short += 20
    else:
        breakout = "Pas de cassure"

    if high_range != low_range:
        range_position = round(((close - low_range) / (high_range - low_range)) * 100, 2)
    else:
        range_position = "N/A"

    advanced = False

    if range_position != "N/A":
        if range_position > 85:
            score_long += 5
            advanced = True
        elif range_position > 65:
            score_long += 10
        elif range_position < 15:
            score_short += 5
            advanced = True
        elif range_position < 35:
            score_short += 10
        else:
            score_long += 5
            score_short += 5

    body = abs(last["c"] - last["o"])
    candle_range = last["h"] - last["l"]
    body_ratio = body / candle_range if candle_range > 0 else 0

    if last["c"] > last["o"] and body_ratio > 0.55:
        last_candle = "Impulsion verte"
        score_long += 10
    elif last["c"] < last["o"] and body_ratio > 0.55:
        last_candle = "Impulsion rouge"
        score_short += 10
    elif last["c"] > last["o"]:
        last_candle = "Verte modérée"
        score_long += 5
    elif last["c"] < last["o"]:
        last_candle = "Rouge modérée"
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

    recent_range = max([x["h"] for x in candles[-8:]]) - min([x["l"] for x in candles[-8:]])
    global_range = high_range - low_range
    compression = global_range > 0 and recent_range / global_range < 0.35

    return {
        "label": label,
        "structure": structure,
        "score_long": score_long,
        "score_short": score_short,
        "range_position": range_position,
        "last_candle": last_candle,
        "breakout": breakout,
        "advanced": advanced,
        "compression": compression
    }


def analyze_multi_tf(ohlcv_item):
    candles = candles_from_ohlcv_item(ohlcv_item)

    tf_1h = analyze_structure(select_last_hours(candles, 1), "1h")
    tf_4h = analyze_structure(select_last_hours(candles, 4), "4h")
    tf_1d = analyze_structure(select_last_hours(candles, 24), "1j")

    return tf_1h, tf_4h, tf_1d, candles


# =========================
# OI / FUNDING
# =========================

def get_oi_change_from_history(history_item):
    if not history_item:
        return "N/A"

    history = history_item.get("history", [])

    if not history or len(history) < 2:
        return "N/A"

    try:
        first = float(history[0].get("c"))
        last = float(history[-1].get("c"))

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
        return "Long crowded"

    if value < -0.02:
        return "Short crowded"

    return "Neutre"


def classify_oi_bias(oi_change):
    if oi_change == "N/A" or oi_change is None:
        return "Neutre"

    try:
        value = float(oi_change)
    except Exception:
        return "Neutre"

    if value > 5:
        return "OI en hausse"

    if value < -5:
        return "OI en baisse"

    return "Neutre"


def get_fallback_market_data():
    return {
        "Coinalyze symbol": "N/A",
        "Futures exchange": "N/A",
        "Funding %": "N/A",
        "Funding biais": "Neutre",
        "Open Interest": "N/A",
        "OI tendance": "Neutre",
        "OI variation %": "N/A",
        "OHLCV item": {}
    }


def get_market_data_for_symbols(symbols, api_key):
    if not api_key:
        return {symbol: get_fallback_market_data() for symbol in symbols}

    symbol_map = build_coinalyze_symbol_map(symbols, api_key)

    coinalyze_symbols = [
        data["coinalyze_symbol"]
        for data in symbol_map.values()
        if data["coinalyze_symbol"]
    ]

    st.session_state["debug_coinalyze_symbols_used"] = coinalyze_symbols

    if not coinalyze_symbols:
        return {symbol: get_fallback_market_data() for symbol in symbols}

    symbols_csv = ",".join(coinalyze_symbols)

    try:
        ohlcv_history = fetch_ohlcv_in_chunks(coinalyze_symbols, api_key)
    except Exception as e:
        st.session_state["debug_ohlcv_error"] = str(e)
        ohlcv_history = []

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
            result[symbol] = get_fallback_market_data()
            continue

        funding_item = funding_map.get(cz_symbol, {})
        oi_item = oi_map.get(cz_symbol, {})
        oi_history_item = oi_history_map.get(cz_symbol, {})
        ohlcv_item = ohlcv_history_map.get(cz_symbol, {})

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

        result[symbol] = {
            "Coinalyze symbol": cz_symbol,
            "Futures exchange": exchange,
            "Funding %": funding_value_clean,
            "Funding biais": classify_funding_bias(funding_value_clean),
            "Open Interest": oi_value_clean,
            "OI tendance": classify_oi_bias(oi_change),
            "OI variation %": oi_change,
            "OHLCV item": ohlcv_item
        }

    return result


# =========================
# AGENT
# =========================

def analyze_relative_strength(perf, btc_perf):
    force = perf - btc_perf

    if force > 8:
        return force, "Très forte vs BTC", 25, 0

    if force > 3:
        return force, "Forte vs BTC", 18, 2

    if force > 0:
        return force, "Légèrement forte vs BTC", 10, 5

    if force < -8:
        return force, "Très faible vs BTC", 0, 25

    if force < -3:
        return force, "Faible vs BTC", 2, 18

    if force < 0:
        return force, "Légèrement faible vs BTC", 5, 10

    return force, "Neutre vs BTC", 6, 6


def analyze_volume_momentum(quote):
    volume_24h = quote.get("volume_24h", 0) or 0
    market_cap = quote.get("market_cap", 0) or 0
    perf_1h = quote.get("percent_change_1h", 0) or 0
    perf_24h = quote.get("percent_change_24h", 0) or 0
    perf_7d = quote.get("percent_change_7d", 0) or 0

    volume_ratio = round((volume_24h / market_cap) * 100, 2) if market_cap > 0 else "N/A"

    score_long = 0
    score_short = 0

    if volume_ratio != "N/A":
        if volume_ratio > 20:
            volume_label = "Volume très actif"
            score_long += 15
            score_short += 15
        elif volume_ratio > 10:
            volume_label = "Volume actif"
            score_long += 10
            score_short += 10
        elif volume_ratio > 3:
            volume_label = "Volume correct"
            score_long += 6
            score_short += 6
        else:
            volume_label = "Volume faible"
            score_long += 2
            score_short += 2
    else:
        volume_label = "Volume N/A"

    if perf_1h > 0 and perf_24h > 0:
        momentum_label = "Momentum acheteur"
        score_long += 15
    elif perf_1h < 0 and perf_24h < 0:
        momentum_label = "Momentum vendeur"
        score_short += 15
    elif perf_24h > 0 and perf_7d > 0:
        momentum_label = "Momentum haussier lent"
        score_long += 10
    elif perf_24h < 0 and perf_7d < 0:
        momentum_label = "Momentum baissier lent"
        score_short += 10
    else:
        momentum_label = "Momentum mixte"
        score_long += 5
        score_short += 5

    return {
        "label": f"{volume_label} / {momentum_label}",
        "volume_ratio": volume_ratio,
        "score_long": score_long,
        "score_short": score_short
    }


def detect_advanced_move(direction, perf, tf_main):
    range_position = tf_main.get("range_position", "N/A")
    breakout = tf_main.get("breakout", "N/A")

    if direction == "LONG":
        if range_position != "N/A" and range_position > 85 and perf > 5:
            return True, "Mouvement déjà avancé"

        if breakout == "Breakout" and perf > 8:
            return True, "Breakout déjà loin"

    if direction == "SHORT":
        if range_position != "N/A" and range_position < 15 and perf < -5:
            return True, "Mouvement déjà avancé"

        if breakout == "Breakdown" and perf < -8:
            return True, "Breakdown déjà loin"

    return False, "Non"


def calculate_risk_score(direction, tf_main, force_label, volume_momentum, advanced, funding_bias, oi_bias):
    risk = 50
    structure = tf_main.get("structure", "")
    range_position = tf_main.get("range_position", "N/A")

    if direction == "LONG":
        if "Haussière" in structure:
            risk -= 15

        if "forte" in force_label.lower():
            risk -= 10

        if range_position != "N/A" and range_position > 85:
            risk += 20

        if range_position != "N/A" and 40 <= range_position <= 75:
            risk -= 10

    elif direction == "SHORT":
        if "Baissière" in structure:
            risk -= 15

        if "faible" in force_label.lower():
            risk -= 10

        if range_position != "N/A" and range_position < 15:
            risk += 20

        if range_position != "N/A" and 25 <= range_position <= 60:
            risk -= 10

    if "Volume faible" in volume_momentum:
        risk += 10

    if advanced:
        risk += 20

    if use_futures_confirm:
        if direction == "LONG" and funding_bias == "Long crowded":
            risk += 10

        if direction == "SHORT" and funding_bias == "Short crowded":
            risk += 10

        if oi_bias == "Neutre":
            risk += 5

    risk = max(0, min(100, risk))

    if risk <= 35:
        return risk, f"{risk}/100 — faible"

    if risk <= 60:
        return risk, f"{risk}/100 — moyen"

    return risk, f"{risk}/100 — élevé"


def build_trade_plan(direction, price, tf_main):
    if price <= 0:
        return "N/A", "N/A", "N/A"

    range_position = tf_main.get("range_position", "N/A")

    if direction == "LONG":
        entry = price * 0.99
        invalidation = entry * (1 - stop_percent / 100)

        if range_position != "N/A" and range_position > 85:
            plan = "Attendre pullback long"
        else:
            plan = "Long possible sur pullback"

    elif direction == "SHORT":
        entry = price * 1.01
        invalidation = entry * (1 + stop_percent / 100)

        if range_position != "N/A" and range_position < 15:
            plan = "Attendre rebond short"
        else:
            plan = "Short possible sur rebond"

    else:
        return "Pas de plan", "N/A", "N/A"

    return plan, round(entry, 6), round(invalidation, 6)


def decide_agent_status(direction, score_long, score_short, tf_1h, tf_4h, advanced, risk):
    aligned_long = "Haussière" in tf_1h["structure"] and (
        "Haussière" in tf_4h["structure"] or "Compression" in tf_4h["structure"]
    )

    aligned_short = "Baissière" in tf_1h["structure"] and (
        "Baissière" in tf_4h["structure"] or "Compression" in tf_4h["structure"]
    )

    if direction == "LONG":
        if advanced:
            return "Haussier mais pas tradable", "Le mouvement est déjà avancé."

        if score_long >= 115 and aligned_long and risk <= 60:
            return "Tradable long", "Setup long exploitable."

        if score_long >= 85:
            return "Setup long en préparation", "Haussier, mais attendre meilleure zone."

        return "Haussier faible / pas prioritaire", "Pas assez propre."

    if direction == "SHORT":
        if advanced:
            return "Baissier mais pas tradable", "Le mouvement est déjà avancé."

        if score_short >= 115 and aligned_short and risk <= 60:
            return "Tradable short", "Setup short exploitable."

        if score_short >= 85:
            return "Setup short en préparation", "Baissier, mais attendre meilleure zone."

        return "Baissier faible / pas prioritaire", "Pas assez propre."

    return "Pas tradable", "Aucun avantage clair."


def build_agent_row(symbol, coin, btc_perf, market_data):
    quote = coin["quote"]["USD"]
    price = quote.get("price", 0) or 0
    perf = get_perf_from_quote(quote, comparison_label)

    tf_1h, tf_4h, tf_1d, candles = analyze_multi_tf(market_data.get("OHLCV item", {}))

    if comparison_label == "1h":
        tf_main = tf_1h
    elif comparison_label in ["4h", "12h"]:
        tf_main = tf_4h
    else:
        tf_main = tf_1d

    force_vs_btc, force_label, force_long, force_short = analyze_relative_strength(perf, btc_perf)
    volume_momentum = analyze_volume_momentum(quote)

    structure_long = tf_1h["score_long"] + tf_4h["score_long"] + tf_1d["score_long"]
    structure_short = tf_1h["score_short"] + tf_4h["score_short"] + tf_1d["score_short"]

    score_long = structure_long + force_long + volume_momentum["score_long"]
    score_short = structure_short + force_short + volume_momentum["score_short"]

    if use_futures_confirm:
        funding_bias = market_data.get("Funding biais", "Neutre")
        oi_bias = market_data.get("OI tendance", "Neutre")

        if oi_bias == "OI en hausse":
            score_long += 5
            score_short += 5

        if funding_bias == "Long crowded":
            score_long -= 5
        elif funding_bias == "Short crowded":
            score_short -= 5
    else:
        funding_bias = "Désactivé"
        oi_bias = "Désactivé"

    if mode == "Long uniquement":
        direction = "LONG"
    elif mode == "Short uniquement":
        direction = "SHORT"
    else:
        if score_long > score_short:
            direction = "LONG"
        elif score_short > score_long:
            direction = "SHORT"
        else:
            direction = "NEUTRE"

    advanced, advanced_alert = detect_advanced_move(direction, perf, tf_main)

    risk_value, risk_label = calculate_risk_score(
        direction,
        tf_main,
        force_label,
        volume_momentum["label"],
        advanced,
        market_data.get("Funding biais", "Neutre"),
        market_data.get("OI tendance", "Neutre")
    )

    plan, entry, invalidation = build_trade_plan(direction, price, tf_main)

    status, status_reason = decide_agent_status(
        direction,
        score_long,
        score_short,
        tf_1h,
        tf_4h,
        advanced,
        risk_value
    )

    if "préparation" in status.lower():
        final_decision = "À surveiller"
    elif "Tradable" in status:
        final_decision = "Setup exploitable"
    elif "pas tradable" in status.lower():
        final_decision = "Non tradable maintenant"
    else:
        final_decision = "Pas prioritaire"

    if (
        "Compression" in tf_4h["structure"]
        and abs(force_vs_btc) < 5
        and volume_momentum["volume_ratio"] != "N/A"
        and volume_momentum["volume_ratio"] > 3
    ):
        preparation_note = "Moins performant, mais setup possible en préparation"
        score_agent_bonus = 15
    else:
        preparation_note = ""
        score_agent_bonus = 0

    score_agent = round(max(score_long, score_short) - risk_value + score_agent_bonus, 2)

    main_reason = f"{status_reason} {force_label}. {volume_momentum['label']}."

    if preparation_note:
        main_reason += f" {preparation_note}."

    return {
        "Crypto": f"{symbol}/USD",
        "Top surveillance": score_agent,
        "Direction probable": direction,
        "Statut tradable": status,
        "Pourquoi": main_reason,
        "Structure 1h": tf_1h["structure"],
        "Structure 4h": tf_4h["structure"],
        "Structure 1j": tf_1d["structure"],
        "Force relative vs BTC": f"{round(force_vs_btc, 2)} % — {force_label}",
        "Volume et momentum": volume_momentum["label"],
        "OI / Funding / Liquidité": f"{oi_bias} / {funding_bias}",
        "Plan": plan,
        "Entrée idéale": entry,
        "Zone d’invalidation": invalidation,
        "Score risque": risk_label,
        "Alerte mouvement avancé": advanced_alert,
        "Décision finale": final_decision,
        "Prix": round(price, 6),
        f"Perf {comparison_label}": round(perf, 2),
        "Score Long": round(score_long, 2),
        "Score Short": round(score_short, 2),
        "Range position": tf_main.get("range_position", "N/A"),
        "Breakout": tf_main.get("breakout", "N/A"),
        "Dernière bougie": tf_main.get("last_candle", "N/A"),
        "Funding %": market_data.get("Funding %", "N/A"),
        "OI variation %": market_data.get("OI variation %", "N/A")
    }


# =========================
# SCAN
# =========================

if scan_button:
    cmc_api_key = get_secret("CMC_API_KEY")
    coinalyze_api_key = get_secret("COINALYZE_API_KEY")

    if not cmc_api_key:
        st.error("Clé API CoinMarketCap absente.")
        st.stop()

    if not coinalyze_api_key:
        st.warning("Clé API Coinalyze absente.")

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

        market_map = get_market_data_for_symbols(symbols, coinalyze_api_key)

        with st.expander("Debug Coinalyze", expanded=False):
            st.write("OI + Funding activés :", use_futures_confirm)
            st.write("Nombre de marchés futures :", st.session_state.get("debug_markets_count", "N/A"))
            st.write("Matching symboles :", st.session_state.get("debug_symbol_map", {}))
            st.write("Symboles utilisés :", st.session_state.get("debug_coinalyze_symbols_used", []))
            st.write("Intervalle OHLCV :", st.session_state.get("debug_ohlcv_interval", "N/A"))
            st.write({
                "funding": st.session_state.get("debug_funding_count", "N/A"),
                "oi": st.session_state.get("debug_oi_count", "N/A"),
                "oi_history": st.session_state.get("debug_oi_history_count", "N/A"),
                "ohlcv": st.session_state.get("debug_ohlcv_count", "N/A"),
            })
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

                market_data = market_map.get(symbol, get_fallback_market_data())
                rows.append(build_agent_row(symbol, coin, btc_perf, market_data))

            except Exception as e:
                errors.append(f"{symbol}: {e}")

    except Exception as e:
        st.error(str(e))

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("Top surveillance", ascending=False)

        visible_columns = [c for c in selected_columns if c in df.columns]

        if not visible_columns:
            visible_columns = [c for c in DEFAULT_COLUMNS if c in df.columns]

        st.subheader("Top coins à surveiller — Agent V9.2")
        st.dataframe(df[visible_columns], use_container_width=True)

        best = df.iloc[0]

        st.subheader("Meilleur setup détecté")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Crypto", best["Crypto"])
            st.metric("Direction", best["Direction probable"])

        with col2:
            st.metric("Statut", best["Statut tradable"])
            st.metric("Décision", best["Décision finale"])

        with col3:
            st.metric("Score surveillance", best["Top surveillance"])
            st.metric("Risque", best["Score risque"])

        with col4:
            st.metric("Entrée idéale", best["Entrée idéale"])
            st.metric("Invalidation", best["Zone d’invalidation"])

        with col5:
            st.metric("Alerte", best["Alerte mouvement avancé"])
            st.metric("Perf", f"{best[f'Perf {comparison_label}']} %")

        st.subheader("Lecture agent")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            info_card("Structure 1h", best["Structure 1h"], "Lecture court terme.")
            info_card("Structure 4h", best["Structure 4h"], "Contexte intermédiaire.")

        with c2:
            info_card("Structure 1j", best["Structure 1j"], "Contexte principal.")
            info_card("Force vs BTC", best["Force relative vs BTC"], "Surperformance ou faiblesse relative.")

        with c3:
            info_card("Volume / Momentum", best["Volume et momentum"], "Activité + dynamique.")
            info_card("OI / Funding", best["OI / Funding / Liquidité"], "Confirmation futures si activée.")

        with c4:
            info_card("Plan", best["Plan"], f"Entrée : {best['Entrée idéale']}")
            info_card("Invalidation", best["Zone d’invalidation"], best["Pourquoi"])

        with st.expander("Table technique complète", expanded=False):
            st.dataframe(df, use_container_width=True)

    if errors:
        st.subheader("Cryptos non récupérées")

        for error in errors:
            st.write(error)

else:
    st.markdown("""
    <div class="binance-card">
        <div class="binance-card-title">En attente</div>
        <div class="binance-card-value">Crée ou charge un profil, règle tes paramètres, puis lance le scan.</div>
        <div class="small-text">
            V9.2 : boutons profil corrigés, menu d’affichage simplifié, reset tableau complet.
        </div>
    </div>
    """, unsafe_allow_html=True)