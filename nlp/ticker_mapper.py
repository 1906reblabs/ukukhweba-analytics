import re
from typing import Optional


# ============================================================
# JSE TICKER KNOWLEDGE BASE
# This is the most SA-specific, highest-value part of your moat.
# No generic tool has this. You will expand this over time as
# you read SA news daily — it compounds with you.
# ============================================================

JSE_ENTITY_MAP: dict[str, list[str]] = {
    # ── Holding Companies & Conglomerates ──────────────────────
    "NPN.JO": [
        "naspers", "naspers limited", "np group",
        "tencent", "prosus",  # Naspers moves on Tencent news
    ],
    "PRX.JO": [
        "prosus", "prosus nv", "prosus group",
    ],
    "REM.JO": [
        "remgro", "remgro limited", "rupert", "remgro group",
        "rnb", "richemont",  # Remgro holds Richemont stake
    ],
    "PSG.JO": [
        "psg group", "psg konsult", "capitec psg",
    ],

    # ── Banking ────────────────────────────────────────────────
    "SBK.JO": [
        "standard bank", "stanbic", "standard bank group",
        "sbsa", "standard bank south africa",
    ],
    "FSR.JO": [
        "firstrand", "first rand", "fnb", "first national bank",
        "wesbank", "rand merchant bank", "rmb", "aldermore",
    ],
    "ABG.JO": [
        "absa", "absa group", "absa bank", "absa capital",
        "barclays africa",
    ],
    "NED.JO": [
        "nedbank", "nedbank group", "nedbank limited",
        "old mutual bank",  # Note: distinct from Old Mutual Ltd
    ],
    "CPI.JO": [
        "capitec", "capitec bank", "capitec holdings",
        "capitec bank holdings",
    ],
    "INL.JO": [
        "investec", "investec limited", "investec plc",
        "investec asset management",
    ],
    "DSY.JO": [
        "discovery", "discovery limited", "discovery health",
        "discovery vitality", "discovery insure", "discovery invest",
        "bank zero",  # Discovery's banking venture
    ],

    # ── Insurance ──────────────────────────────────────────────
    "OML.JO": [
        "old mutual", "old mutual limited", "old mutual group",
        "old mutual wealth",
    ],
    "SLM.JO": [
        "sanlam", "sanlam limited", "sanlam life",
        "sanlam investments",
    ],
    "MMI.JO": [
        "momentum", "mmi holdings", "momentum metropolitan",
        "metropolitan life",
    ],

    # ── Mining — Diversified ───────────────────────────────────
    "AGL.JO": [
        "anglo american", "anglo american plc",
        "anglo american platinum",  # Parent mention
        "kumba", "de beers",  # Anglo subsidiaries — big news
    ],
    "BHP.JO": [
        "bhp", "bhp group", "bhp billiton", "bhp plc",
        "bhp limited",
    ],
    "GLN.JO": [
        "glencore", "glencore plc", "glencore south africa",
    ],

    # ── Mining — Platinum Group Metals ────────────────────────
    "AMS.JO": [
        "amplats", "anglo american platinum",
        "anglo platinum", "amplats mining",
    ],
    "IMP.JO": [
        "impala platinum", "implats", "impala platinum holdings",
        "zimplats",
    ],
    "NHM.JO": [
        "northam platinum", "northam", "northam holdings",
        "zondereinde",
    ],
    "SGL.JO": [
        "sibanye", "sibanye stillwater", "sibanye gold",
        "stillwater mining",
    ],

    # ── Mining — Gold ─────────────────────────────────────────
    "GFI.JO": [
        "gold fields", "gold fields limited", "salares norte",
    ],
    "ANG.JO": [
        "anglogold", "anglogold ashanti",
        "anglogold ashanti limited",
    ],
    "HAR.JO": [
        "harmony gold", "harmony", "harmony gold mining",
    ],

    # ── Mining — Coal & Diversified ───────────────────────────
    "EXX.JO": [
        "exxaro", "exxaro resources", "exxaro coal",
    ],
    "TGA.JO": [
        "thungela", "thungela resources",
    ],

    # ── Resources & Chemicals ─────────────────────────────────
    "SOL.JO": [
        "sasol", "sasol limited", "sasol mining",
        "sasol chemicals", "sasol energy", "natref",
        "sasol oil",
    ],
    "ARI.JO": [
        "african rainbow minerals", "arm", "arm coal",
        "arm platinum",
    ],

    # ── Telecoms ──────────────────────────────────────────────
    "MTN.JO": [
        "mtn", "mtn group", "mtn south africa",
        "mtn nigeria", "mtn ghana", "mobile money",
        "mtn fintech",
    ],
    "VOD.JO": [
        "vodacom", "vodacom group", "vodacom south africa",
        "m-pesa south africa",
    ],
    "TLS.JO": [
        "telkom", "telkom sa", "telkom group", "openserve",
        "bcx",
    ],

    # ── Technology ────────────────────────────────────────────
    "WEZ.JO": [
        "wezizwe", "wezizwe platinum",
    ],
    "DTC.JO": [
        "datatec", "datatec limited", "logicalis",
        "westcon",
    ],
    "EOH.JO": [
        "eoh", "eoh holdings",
    ],

    # ── Retail ────────────────────────────────────────────────
    "SHP.JO": [
        "shoprite", "shoprite holdings", "shoprite checkers",
        "usave", "checker hyper", "ok franchise",
    ],
    "PIK.JO": [
        "pick n pay", "pick & pay", "picknpay",
        "boxer retail", "boxer",
    ],
    "SPP.JO": [
        "spar", "spar group", "spar south africa",
        "spar western cape",
    ],
    "WHL.JO": [
        "woolworths", "woolworths holdings",
        "woolworths food", "david jones",
    ],
    "TFG.JO": [
        "tfg", "the foschini group", "foschini",
        "jet", "exact!", "markham", "american swiss",
    ],
    "MRP.JO": [
        "mr price", "mr price group", "mrp",
        "mr price sport", "sheet street",
    ],

    # ── Real Estate ───────────────────────────────────────────
    "GRT.JO": [
        "growthpoint", "growthpoint properties",
    ],
    "EMI.JO": [
        "emira", "emira property fund",
    ],
    "REI.JO": [
        "redefine", "redefine properties",
    ],

    # ── Healthcare ────────────────────────────────────────────
    "MEI.JO": [
        "mediclinic", "mediclinic international",
        "hirslanden", "al noor",
    ],
    "NTC.JO": [
        "netcare", "netcare limited",
    ],
    "LHC.JO": [
        "life healthcare", "life healthcare group",
    ],

    # ── Food & Beverages ──────────────────────────────────────
    "TBS.JO": [
        "tiger brands", "tiger brands limited",
        "tiger brands consumer goods",
    ],
    "APN.JO": [
        "aspen pharmacare", "aspen", "aspen holdings",
    ],
    "RFG.JO": [
        "rhodes food group", "rhodes food",
    ],

    # ── SA Macro / Broad Market Signals ───────────────────────
    "_MACRO_POSITIVE": [
        "gdp growth", "economic growth", "rand strengthens",
        "rand rally", "load shedding eases", "stage 0",
        "eskom recovery", "current account surplus",
        "sarb rate cut", "interest rate cut", "inflation falls",
        "sa investment grade", "rating upgrade",
    ],
    "_MACRO_NEGATIVE": [
        "load shedding", "stage 4", "stage 6", "stage 8",
        "eskom breakdown", "power cuts", "rolling blackouts",
        "rand weakens", "rand collapse", "rand falls",
        "junk status", "rating downgrade", "sarb rate hike",
        "inflation surge", "fuel price increase",
        "strike action", "wage strike", "numsa strike",
        "municipal debt", "state capture",
    ],
    # Load shedding stages directly hit industrials, retail, mining
    "_LOAD_SHEDDING": [
        "load shedding", "loadshedding", "load-shedding",
        "stage 1", "stage 2", "stage 3", "stage 4",
        "stage 5", "stage 6", "eskom", "power cuts",
        "rolling blackouts", "power outage",
    ],
}

# Build reverse index: keyword → list of tickers
_REVERSE_INDEX: dict[str, list[str]] = {}
for ticker, keywords in JSE_ENTITY_MAP.items():
    for kw in keywords:
        _REVERSE_INDEX.setdefault(kw.lower(), []).append(ticker)


def map_article_to_tickers(title: str, body: str) -> list[str]:
    """
    Map an article to JSE tickers based on entity mentions.
    Returns list of matched tickers (deduplicated, sorted).
    
    Algorithm:
    1. Combine title (weighted) + body text
    2. Lowercase and search for all keywords
    3. Longer/more-specific matches take priority
    4. Return unique tickers found
    
    This is O(n*k) but fast enough for hundreds of articles/day.
    """
    combined = f"{title.lower()} {title.lower()} {body.lower()}"

    matched = set()

    # Sort by keyword length descending so "standard bank group"
    # matches before "bank" — prevents false positives
    sorted_keywords = sorted(_REVERSE_INDEX.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        # Whole-word match — avoid "arm" matching "farm" or "harm"
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, combined):
            for ticker in _REVERSE_INDEX[keyword]:
                matched.add(ticker)

    return sorted(matched)


def get_load_shedding_stage(text: str) -> Optional[int]:
    """
    Extract load shedding stage from article — this is uniquely SA.
    Load shedding has measurable impact on JSE industrials/mining.
    This signal alone is worth building the engine for.
    """
    text_lower = text.lower()
    for stage in range(8, 0, -1):  # check highest first
        if f"stage {stage}" in text_lower:
            return stage
    return None
