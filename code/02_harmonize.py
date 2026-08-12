"""
02_harmonize.py -- Resolve ~13k raw institution strings across 10 ranking systems
into stable institution IDs.

Entity resolution is the largest source of error in cross-ranking work, so this is
deliberately CONSERVATIVE and, crucially, uses a hard structural check:

    A ranking system publishes each institution AT MOST ONCE per edition.
    Therefore any merge that would put two rows in the same (system, year) cell
    is wrong, and is rejected.

That single constraint catches the failure mode that sinks naive fuzzy matching
("University of Florida" swallowing "Florida State University", "University of
Tokyo" swallowing "Tokyo Institute of Technology"), because those pairs co-occur
in almost every edition.

Pipeline
  1. Normalize: transliterate, lowercase, expand abbreviations, strip stop words,
     canonicalize country. Curated alias table for acronyms.
  2. Block on (country, sorted full token set).
  3. Fuzzy attachment pass, single-link, non-transitive, collision-checked.
  4. Subset pass ("University of Michigan" <- "University of Michigan-Ann Arbor"),
     only where the superset partner is unique or dominant, collision-checked.

Outputs: crosswalk.csv, panel_long.csv, harmonization_report.txt
"""
import os, re, sys
from collections import defaultdict
import numpy as np
import pandas as pd
from unidecode import unidecode
from rapidfuzz import fuzz, process

W = os.path.expanduser("~/uniranks/work")
long = pd.read_csv(f"{W}/raw_long.csv")
REPORT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s); REPORT.append(s)


# ============================================================ country canonical
ISO2 = {"us": "United States", "gb": "United Kingdom", "cn": "China", "de": "Germany",
        "fr": "France", "jp": "Japan", "ca": "Canada", "au": "Australia", "nl": "Netherlands",
        "se": "Sweden", "ch": "Switzerland", "it": "Italy", "es": "Spain", "kr": "South Korea",
        "il": "Israel", "dk": "Denmark", "be": "Belgium", "no": "Norway", "fi": "Finland",
        "at": "Austria", "ru": "Russia", "br": "Brazil", "in": "India", "sg": "Singapore",
        "hk": "Hong Kong", "tw": "Taiwan", "za": "South Africa", "ie": "Ireland",
        "nz": "New Zealand", "pl": "Poland", "pt": "Portugal", "gr": "Greece",
        "cz": "Czechia", "hu": "Hungary", "tr": "Turkey", "mx": "Mexico", "ar": "Argentina",
        "cl": "Chile", "sa": "Saudi Arabia", "ir": "Iran", "eg": "Egypt", "my": "Malaysia",
        "th": "Thailand", "sk": "Slovakia", "si": "Slovenia", "hr": "Croatia", "rs": "Serbia",
        "ee": "Estonia", "is": "Iceland", "lu": "Luxembourg", "cy": "Cyprus",
        "ae": "United Arab Emirates", "qa": "Qatar", "pk": "Pakistan", "co": "Colombia",
        "uy": "Uruguay", "lb": "Lebanon", "jo": "Jordan", "ng": "Nigeria", "ua": "Ukraine",
        "by": "Belarus", "bg": "Bulgaria", "ro": "Romania", "lt": "Lithuania",
        "lv": "Latvia", "mo": "Macau", "id": "Indonesia", "ph": "Philippines",
        "vn": "Vietnam", "kz": "Kazakhstan", "cr": "Costa Rica", "pe": "Peru",
        "ec": "Ecuador", "ve": "Venezuela", "mt": "Malta", "ma": "Morocco", "tn": "Tunisia",
        "ke": "Kenya", "gh": "Ghana", "et": "Ethiopia", "ug": "Uganda", "tz": "Tanzania"}
# SCImago (and a few other sources) label countries with ISO-3166 alpha-3 codes.
# Without this map those rows land in an unknown-country block and lose the
# in-country matching that the subset and nesting passes depend on.
ISO3 = {"usa": "United States", "gbr": "United Kingdom", "chn": "China",
        "deu": "Germany", "fra": "France", "jpn": "Japan", "can": "Canada",
        "aus": "Australia", "nld": "Netherlands", "swe": "Sweden",
        "che": "Switzerland", "ita": "Italy", "esp": "Spain", "kor": "South Korea",
        "isr": "Israel", "dnk": "Denmark", "bel": "Belgium", "nor": "Norway",
        "fin": "Finland", "aut": "Austria", "rus": "Russia", "bra": "Brazil",
        "ind": "India", "sgp": "Singapore", "hkg": "Hong Kong", "twn": "Taiwan",
        "zaf": "South Africa", "irl": "Ireland", "nzl": "New Zealand",
        "pol": "Poland", "prt": "Portugal", "grc": "Greece", "cze": "Czechia",
        "hun": "Hungary", "tur": "Turkey", "mex": "Mexico", "arg": "Argentina",
        "chl": "Chile", "sau": "Saudi Arabia", "irn": "Iran", "egy": "Egypt",
        "mys": "Malaysia", "tha": "Thailand", "svk": "Slovakia", "svn": "Slovenia",
        "hrv": "Croatia", "srb": "Serbia", "est": "Estonia", "isl": "Iceland",
        "lux": "Luxembourg", "cyp": "Cyprus", "are": "United Arab Emirates",
        "qat": "Qatar", "pak": "Pakistan", "col": "Colombia", "ury": "Uruguay",
        "lbn": "Lebanon", "jor": "Jordan", "nga": "Nigeria", "ukr": "Ukraine",
        "blr": "Belarus", "bgr": "Bulgaria", "rou": "Romania", "ltu": "Lithuania",
        "lva": "Latvia", "mac": "Macau", "idn": "Indonesia", "phl": "Philippines",
        "vnm": "Vietnam", "kaz": "Kazakhstan", "cri": "Costa Rica", "per": "Peru",
        "ecu": "Ecuador", "ven": "Venezuela", "mlt": "Malta", "mar": "Morocco",
        "tun": "Tunisia", "ken": "Kenya", "gha": "Ghana", "eth": "Ethiopia",
        "uga": "Uganda", "tza": "Tanzania", "bgd": "Bangladesh", "lka": "Sri Lanka",
        "npl": "Nepal", "omn": "Oman", "kwt": "Kuwait", "bhr": "Bahrain",
        "dza": "Algeria", "irq": "Iraq", "syr": "Syria", "yem": "Yemen",
        "cub": "Cuba", "pan": "Panama", "gtm": "Guatemala", "bol": "Bolivia",
        "pry": "Paraguay", "dom": "Dominican Republic", "mkd": "North Macedonia",
        "alb": "Albania", "bih": "Bosnia and Herzegovina", "mne": "Montenegro",
        "geo": "Georgia", "arm": "Armenia", "aze": "Azerbaijan", "uzb": "Uzbekistan"}
CMAP = {"usa": "United States", "u s a": "United States", "united states": "United States",
        "united states of america": "United States", "america": "United States",
        "united states of america usa": "United States",
        "uk": "United Kingdom", "united kingdom": "United Kingdom", "england": "United Kingdom",
        "scotland": "United Kingdom", "wales": "United Kingdom", "great britain": "United Kingdom",
        "northern ireland": "United Kingdom",
        "united kingdom of great britain and northern ireland": "United Kingdom",
        "russian federation": "Russia", "russia": "Russia",
        "republic of korea": "South Korea", "korea rep": "South Korea", "korea": "South Korea",
        "korea south": "South Korea", "south korea": "South Korea",
        "china mainland": "China", "peoples republic of china": "China", "china": "China",
        "hong kong sar": "Hong Kong", "hong kong sar china": "Hong Kong",
        "macau sar": "Macau", "chinese taipei": "Taiwan", "taiwan china": "Taiwan",
        "czech republic": "Czechia", "the netherlands": "Netherlands",
        "iran islamic republic of": "Iran", "turkiye": "Turkey", "viet nam": "Vietnam",
        "brunei darussalam": "Brunei", "slovak republic": "Slovakia",
        "uae": "United Arab Emirates", "germany fed rep of": "Germany", "fr germany": "Germany",
        "north america": np.nan, "europe": np.nan, "asia": np.nan, "oceania": np.nan,
        "africa": np.nan, "latin america": np.nan, "south america": np.nan,
        "middle east": np.nan, "central asia": np.nan}


def norm_country(c):
    if pd.isna(c):
        return np.nan
    s = unidecode(str(c)).lower().strip()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return np.nan
    if len(s) == 2 and s in ISO2:
        return ISO2[s]
    if s in CMAP:
        return CMAP[s]
    if len(s) == 3 and s in ISO3:
        return ISO3[s]
    return s.title()


long["country"] = long["country_raw"].map(norm_country)

# ============================================================ name normalizer
ABBR = [(r"\buniv\b|\buniversite\b|\buniversitat\b|\buniversitaet\b|\buniversidad\b|"
         r"\buniversidade\b|\buniversita\b|\buniversiteit\b|\buniversitet\w*\b|"
         r"\buniwersytet\b|\buniversitas\b|\buniversiti\b|\buniversity\b|\buniversities\b",
         "university"),
        (r"\btech\b|\btechnological\b|\btechnische\b|\btechnical\b|\btechnology\b|"
         r"\btechnologies\b|\btecnologia\b|\bteknologi\b|\btecnologica\b", "technology"),
        (r"\binst\b|\binstitut\b|\binstitutes\b|\binstitute\b|\binstituto\b|"
         r"\binstitution\b|\binstituut\b|\binstitutet\b|\binstitutt\b|"
         r"\bistituto\b", "institute"),
        (r"\bcoll\b|\bcollege\b|\bcolegio\b", "college"),
        (r"\bsci\b|\bsciences\b|\bscience\b|\bciencias\b|\bwissenschaft\w*\b", "science"),
        (r"\bmed\b|\bmedicine\b|\bmedizin\w*\b|\bmedical\b|\bmedicina\b", "medical"),
        (r"\bagri\w*\b", "agriculture"),
        (r"\bnatl\b|\bnational\b|\bnacional\b|\bnationale\b|\bnationaal\b", "national"),
        (r"\bestadual\b|\bestatal\b", "state"),
        (r"\bacad\b|\bacademy\b|\bakademi\w*\b|\bacademia\b|\bakademia\b", "academy"),
        (r"\bhochschule\b|\bfachhochschule\b", "university"),
        (r"\bpolytechnic\b|\bpolitecnico\b|\bpolytechnique\b|\bpolitehnica\b|"
         r"\bpolytechnical\b", "polytechnic"),
        (r"\bst\b", "saint"), (r"\bmt\b", "mount"),
        (r"\bres\b|\bresearch\b|\bforschung\w*\b", "research"),
        (r"\bctr\b|\bcentre\b|\bcenter\b|\bcentro\b|\bzentrum\b", "center"),
        (r"\bhosp\b|\bhospital\b|\bhospitalar\b", "hospital"),
        (r"\bsch\b|\bschool\b|\becole\b|\bescuela\b|\bescola\b|\bhogeschool\b", "school")]

ALIAS = {
    "mit": "massachusetts institute technology",
    "massachusetts institute technology mit": "massachusetts institute technology",
    "caltech": "california institute technology",
    "california institute technology caltech": "california institute technology",
    "ucl": "university college london",
    "university college london ucl": "university college london",
    "lse": "london school economics political science",
    "london school economics political science lse": "london school economics political science",
    "eth zurich": "eth zurich",
    "eth zurich swiss federal institute technology": "eth zurich",
    "eth zurich swiss federal institute technology zurich": "eth zurich",
    "swiss federal institute technology zurich": "eth zurich",
    "swiss federal institute technology": "eth zurich",
    "eth zurich eidgenossische technology hochschule zurich": "eth zurich",
    "eidgenossische technology university zurich": "eth zurich",
    "eidgenossische technology hochschule zurich": "eth zurich",
    "technology university munich": "technology university munich",
    "technology university muenchen": "technology university munich",
    "epfl": "epfl lausanne",
    "swiss federal institute technology lausanne": "epfl lausanne",
    "ecole polytechnic federale lausanne": "epfl lausanne",
    "ecole polytechnic federale lausanne epfl": "epfl lausanne",
    "nus": "national university singapore",
    "national university singapore nus": "national university singapore",
    "nanyang technology university": "nanyang technology university singapore",
    "nanyang technology university ntu": "nanyang technology university singapore",
    "nanyang technology university ntu singapore": "nanyang technology university singapore",
    "kaist": "kaist", "korea advanced institute science technology": "kaist",
    "korea advanced institute science technology kaist": "kaist",
    "kaist korea advanced institute science technology": "kaist",
    "hkust": "hong kong university science technology",
    "hong kong university science technology hkust": "hong kong university science technology",
    "chinese university hong kong cuhk": "chinese university hong kong",
    "university hong kong hku": "university hong kong",
    "ucla": "university california los angeles",
    "university california los angeles ucla": "university california los angeles",
    "ucsd": "university california san diego",
    "ucsf": "university california san francisco",
    "ucsb": "university california santa barbara",
    "ku leuven": "ku leuven", "katholieke university leuven": "ku leuven",
    "ku leuven katholieke university leuven": "ku leuven",
    "kth royal institute technology": "kth royal institute technology",
    "royal institute technology kth": "kth royal institute technology",
    "unsw sydney": "university new south wales",
    "university new south wales unsw sydney": "university new south wales",
    "unsw": "university new south wales",
    "anu": "australian national university",
    "utrecht university": "utrecht university",
    # --- renames and legacy names surfaced by the split-entity diagnostic
    "imperial college science": "imperial college london",
    "imperial college science technology medical": "imperial college london",
    "imperial college science technology": "imperial college london",
    "university catholique louvain": "catholic university louvain",
    "institute science tokyo": "tokyo institute technology",
    "national yang ming chiao tung university": "national chiao tung university",
    "catholic university leuven": "ku leuven",
    "university roma sapienza": "sapienza university rome",
    "sapienza university roma": "sapienza university rome",
    "university rome sapienza": "sapienza university rome",
    "vu university amsterdam": "vrije university amsterdam",
    "vrije university amsterdam": "vrije university amsterdam",
    "university wageningen": "wageningen university research",
    "wageningen university": "wageningen university research",
    "karolinska institute": "karolinska institute",
    "pierre marie curie university paris 6": "pierre marie curie university",
    "university pierre marie curie": "pierre marie curie university",
    "paris diderot university paris 7": "paris diderot university",
    "university paris diderot": "paris diderot university",
    "university psl": "paris science lettres psl research university",
    "psl university": "paris science lettres psl research university",
    "paris science lettres psl research university paris":
        "paris science lettres psl research university",
    "ecole normale superieure paris": "ecole normale superieure paris",
    "university medicine dentistry new jersey": "rutgers university",
}

# ============================================================ curated decisions
# Reviewed by hand from entity_review_candidates.csv. Each pair is two display
# names that a human judged to be one institution: transliteration variants,
# official renames, and translated forms. Every merge below is still subject to
# the one-row-per-edition collision check, so a pair that turns out to be
# co-listed is refused and reported rather than forced.
#
# Deliberately NOT merged: institutional mergers whose predecessors and successor
# overlap in time (Osaka City + Osaka Prefecture -> Osaka Metropolitan 2022;
# National Chiao Tung + National Yang Ming -> NYCU 2021; Tampere UT + University
# of Tampere -> Tampere University 2019). Two institutions becoming one is a real
# discontinuity, not a naming artefact, and splicing them would invent a history.
CURATED_MERGES = [
    # --- campus / legal-name variants
    ("Ohio State University (Main campus)", "Ohio State University"),
    ("University at Albany (State University of New York)", "University at Albany SUNY"),
    ("BINGHAMTON UNIVERSITY, STATE UNIVERSITY OF NEW YORK", "Binghamton University"),
    ("SUNY Upstate Medical University", "State University of New York Upstate Medical University"),
    ("Mizzou - University of Missouri", "University of Missouri - Columbia"),
    ("Rutgers", "Rutgers University–New Brunswick"),
    ("Rutgers University", "Rutgers University–New Brunswick"),
    ("Rutgers, The State University of New Jersey", "Rutgers University–New Brunswick"),
    ("Rutgers State University New Brunswick", "Rutgers University–New Brunswick"),
    ("Rutgers, The State University of New Jersey - Newark", "Rutgers University–Newark"),
    ("The University of Texas M. D. Anderson Cancer Center",
     "University of Texas MD Anderson Cancer Center"),
    ("University of Colorado Anschutz Medical Campus",
     "University of Colorado, Anschutz Medical Campus"),
    # --- transliteration / diacritics / translated forms
    ("University of Hawaii at Manoa", "University of Hawaiʻi at Mānoa"),
    ("University of Genova", "University of Genoa"),
    ("University of Milan-Bicocca", "University of Milano-Bicocca"),
    ("Free University of Berlin", "Freie Universitaet Berlin"),
    ("Polytechnic University of Valencia", "Universitat Politecnica de Valencia"),
    ("Xian Jiao Tong University", "Xi’an Jiaotong University"),
    ("Paul Sabatier University (Toulouse 3)", "Université Paul Sabatier Toulouse III"),
    ("Ankara University", "Ankara Üniversitesi"),
    ("Akdeniz University", "Akdeniz Üniversitesi"),
    ("Dokuz Eylul Universitesi", "Dokuz Eylül University"),
    ("Federico Santa María Technical University",
     "Universidad Técnica Federico Santa María (USM)"),
    ("Pontifical Catholic University of Valparaíso",
     "Pontificia Universidad Católica de Valparaíso"),
    ("Universidad Catlica de la Santsima Concepcin",
     "Universidad Católica de la Santísima Concepción"),
    ("Universidad de las Fuerzas Armadas ESPE (Ex Espe)",
     "Universidad de las Fuerzas Armadas – ESPE"),
    ("Mackenzie Presbyterian University", "Universidade Presbiteriana Mackenzie"),
    ("AL IMAM MOHAMMAD IBN SAUD ISLAMIC UNIVERSITY", "Imam Mohammad Ibn Saud Islamic University"),
    ("University of Sri Jayewardenapura", "University of Sri Jayewardenepura"),
    ("Northern Border University", "Northern Borders University"),
    ("ENS Paris-Saclay", "École normale supérieure Paris-Saclay"),
    ("Paris City University", "Université Paris Cité"),
    ("NOVA University of Lisbon", "New University of Lisbon"),
    ("Polytechnic University of Madrid", "Technical University of Madrid"),
    ("Northwest A&F University", "Northwest Agriculture and Forestry University"),
    ("Northeastern University (Shenyang)", "Northeastern University, China"),
    ("China University of Petroleum (East China)", "China University of Petroleum (Huadong)"),
    ("VU Amsterdam", "Vrije Universiteit Amsterdam"),
    ("Aalto University / Aalto-yliopisto", "Aalto University"),
    ("Tampere University (TUT+UoT) / Tampereen korkeakouluyhteisö", "Tampere University"),
    ("Monash University, Melbourne", "Monash University"),   # SCImago's label
    # --- official renames
    ("Chonbuk National University", "Jeonbuk National University"),            # 2020
    ("AUT University", "Auckland University of Technology"),
    ("HSE University", "National Research University Higher School of Economics"),
    ("AGH University of Science and Technology", "AGH University of Krakow"),   # 2023
    ("Lappeenranta University of Technology", "LUT University"),               # 2019
    ("University of Massachusetts Medical School",
     "University of Massachusetts Chan Medical School"),                        # 2021
    ("National Research Nuclear University MEPhI",
     "National Research Nuclear University MEPhI (Moscow Engineering Physics Institute)"),
    ("Third Military Medical University", "Army Medical University"),           # 2017
    ("The Second Military Medical University", "Naval Medical University"),     # 2017
]

# University-SYSTEM aggregates (and similar umbrella bodies) are reported by a few
# bibliometric rankings but are not universities: "University of California System"
# is the sum of ten campuses that are separately ranked. Keeping them would double
# count and would put a non-institution in the league table.
SYSTEM_AGGREGATE = re.compile(r"\bsystem\b\s*\)?\s*$", re.I)

STOP = set("""the of at for in and a an de del della di du des der das den dos da do los las
el la le les und y e ed als am zu zur im von van der die pour aux dell degli con per
sur fur mit""".split())
# words that appear in thousands of names and identify nothing on their own
WEAK = set("""university institute college school technology science national state
polytechnic academy medical research center studies higher education federal""".split())


CJK = re.compile(r"[　-鿿가-힯＀-￯Ѐ-ӿ؀-ۿ]+")


ACRONYM = re.compile(r"^[A-Z0-9\.\-]{2,8}$")


def _strip_parens(s):
    """Drop parentheticals that are bare acronyms -- '(MIT)', '(NTU)' -- but KEEP
    disambiguating content -- '(Taichung)', '(Wuhan)', '(Main campus)' -- because
    that is exactly what separates co-listed same-named institutions."""
    def rep(m):
        inner = m.group(1).strip()
        return " " if ACRONYM.match(inner.replace(" ", "")) else " " + inner + " "
    return re.sub(r"\(([^)]*)\)", rep, s)


def norm_name(s):
    s = str(s)
    if CJK.search(s):                    # co-listed CJK/Cyrillic/Arabic form
        stripped = CJK.sub(" ", s)
        if len(re.findall(r"[A-Za-z]{2,}", stripped)) >= 2:
            s = stripped.split("/")[0].split("|")[0]
    s = _strip_parens(s)                 # while case still distinguishes "(NYU)"
    s = unidecode(s).lower()
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = s.replace("&", " and ").replace("'", "").replace("-", " ").replace("/", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^tu ", "technology university ", s)
    for pat, rep in ABBR:
        s = re.sub(pat, rep, s)
    # keep single characters (the "A&M" / "A&F" problem) but drop stop words
    toks = [t for t in s.split() if t not in STOP]
    out, prev = [], None
    for t in toks:
        if t != prev:
            out.append(t)
        prev = t
    s = " ".join(out)
    return ALIAS.get(s, s)


long["nname"] = long["name_raw"].map(norm_name)
long = long[long.nname.str.len() > 1].copy()

# ============================================================ record table
rec = (long.groupby("nname", as_index=False)
       .agg(n_obs=("rank", "size"), name_raw=("name_raw", lambda x: x.value_counts().index[0]),
            n_sys=("system", "nunique")))
ctry = (long.dropna(subset=["country"]).groupby("nname")["country"]
        .agg(lambda x: x.value_counts().index[0]))
rec["country"] = rec["nname"].map(ctry)
rec["tok"] = rec["nname"].map(lambda s: frozenset(s.split()))
rec["tkey"] = rec["tok"].map(lambda t: " ".join(sorted(t)))
say(f"{len(rec)} distinct normalized names; {rec.country.notna().mean():.1%} carry a country")

# (system, year) footprint of every normalized name -- the collision check
foot = defaultdict(set)
for nn, sy in zip(long.nname, zip(long.system, long.year)):
    foot[nn].add(sy)

# ---- step 1: block on (country, full token key)
rec["blk"] = rec["country"].fillna("?") + "||" + rec["tkey"]
tk_c = rec.dropna(subset=["country"]).groupby("tkey")["country"].nunique()
uniq = set(tk_c[tk_c == 1].index)
tk2c = rec.dropna(subset=["country"]).drop_duplicates("tkey").set_index("tkey")["country"].to_dict()
m = rec.country.isna() & rec.tkey.isin(uniq)
rec.loc[m, "country"] = rec.loc[m, "tkey"].map(tk2c)
rec.loc[m, "blk"] = rec.loc[m, "country"] + "||" + rec.loc[m, "tkey"]
say("blocks after exact token-key match:", rec.blk.nunique())

# ---- step 1b: transliteration-variant pass. "Goettingen" and "Goettingen"
# (from "Göttingen") only differ by how the source spelled the umlaut. Collapse
# vowel digraphs and doubled letters into a SQUEEZED key and require exact
# equality of that key -- exactness keeps "Queen" from colliding with anything.
def squeeze(tk):
    out = []
    for t in tk.split():
        u = t.replace("oe", "o").replace("ue", "u").replace("ae", "a")
        u = re.sub(r"(.)\1+", r"\1", u)
        out.append(u)
    return " ".join(sorted(set(out)))


rec["sq"] = rec["tkey"].map(squeeze)
sq_map = {}
n_sq = 0
for (c, sq), g in rec.groupby([rec["country"].fillna("?"), "sq"]):
    blks = list(dict.fromkeys(g["blk"]))
    if len(blks) < 2:
        continue
    tgt = g.groupby("blk")["n_obs"].sum().idxmax()
    fp = set().union(*[set().union(*[foot[n] for n in rec.nname[rec.blk == b]])
                       for b in [tgt]])
    for b in blks:
        if b == tgt:
            continue
        bf = set().union(*[foot[n] for n in rec.nname[rec.blk == b]])
        if bf & fp:
            continue
        sq_map[b] = tgt; fp |= bf; n_sq += 1
rec["blk"] = rec["blk"].map(lambda b: sq_map.get(b, b))
say(f"blocks after transliteration-variant pass: {rec.blk.nunique()} ({n_sq} merged)")

blk_foot = defaultdict(set)
for nn, b in zip(rec.nname, rec.blk):
    blk_foot[b] |= foot[nn]

# ---- step 2 & 3: attachment passes with the one-row-per-edition collision check
bl = (rec.groupby("blk").agg(w=("n_obs", "sum"), tkey=("tkey", "first"),
                             country=("country", "first")).reset_index()
      .sort_values("w", ascending=False).reset_index(drop=True))
bl["tok"] = bl["tkey"].map(lambda s: frozenset(s.split()))
tok_of = dict(zip(bl.blk, bl.tok))
w_of = dict(zip(bl.blk, bl.w))

attach = {}
n_rej_collide = 0


def try_attach(small, big):
    """Attach block `small` to block `big` unless it double-books an edition."""
    global n_rej_collide
    if small in attach or big in attach or small == big:
        return False
    if blk_foot[small] & blk_foot[big]:
        n_rej_collide += 1
        return False
    attach[small] = big
    blk_foot[big] |= blk_foot[small]
    return True


# --- 2a. fuzzy near-duplicates (spelling, word order, small edits)
for c, g in bl.groupby(bl["country"].fillna("?")):
    if len(g) < 2:
        continue
    keys, blks = list(g["tkey"]), list(g["blk"])
    sim = process.cdist(keys, keys, scorer=fuzz.token_sort_ratio, score_cutoff=88, workers=-1)
    ii, jj = np.where(sim >= 88)
    for a, b in zip(ii, jj):
        if a <= b:                       # g is weight-sorted: b is the larger block
            continue
        A, B = tok_of[blks[a]], tok_of[blks[b]]
        if A <= B or B <= A:             # subsets handled separately below
            continue
        if len(A | B) and len(A & B) / len(A | B) >= 0.80 and abs(len(A) - len(B)) <= 1:
            try_attach(blks[a], blks[b])
say(f"after fuzzy pass: {len(set(bl.blk) - set(attach))} blocks "
    f"({len(attach)} attached, {n_rej_collide} rejected by the edition-collision check)")

# --- 2b. subset pass: "university michigan" <- "university michigan ann arbor",
#     but only when one superset partner clearly dominates.
before = len(attach)
sub_rej = 0
for c, g in bl.groupby(bl["country"].fillna("?")):
    if len(g) < 2:
        continue
    blks, toks, ws = list(g["blk"]), list(g["tok"]), list(g["w"])
    for a in range(len(blks)):
        A = toks[a]
        if len(A - WEAK) < 1:
            continue
        # extra tokens must be real words ("arbor", "dearborn"), not initials,
        # or we merge "Northwest University" into "Northwest A&F University"
        cands = [(b, ws[b]) for b in range(len(blks))
                 if b != a and A < toks[b] and len(toks[b] - A) <= 2
                 and all(len(t) >= 3 or t.isdigit() for t in toks[b] - A)]
        if not cands:
            continue
        cands.sort(key=lambda x: -x[1])
        top, topw = cands[0]
        rest = sum(w for _, w in cands[1:])
        if len(cands) == 1 or topw >= 3 * max(rest, 1):
            small, big = (blks[a], blks[top]) if ws[a] <= topw else (blks[top], blks[a])
            if not try_attach(small, big):
                sub_rej += 1
say(f"after subset pass: {len(set(bl.blk) - set(attach))} blocks "
    f"({len(attach)-before} attached, {sub_rej} rejected)")


before = len(attach)
n2c = 0
bl2 = bl.copy()
bl2["cur"] = bl2["blk"]
order = list(bl2.sort_values("w", ascending=False)["blk"])
for c, g in bl2.groupby(bl2["country"].fillna("?")):
    if len(g) < 2:
        continue
    blks, toks, ws = list(g["blk"]), list(g["tok"]), list(g["w"])
    rank = {b: k for k, b in enumerate(blks)}
    for a in sorted(range(len(blks)), key=lambda k: -ws[k]):
        A = toks[a]
        cands = [b for b in range(len(blks)) if b != a
                 and (A < toks[b] or toks[b] < A)
                 and len(toks[b] ^ A) <= 3
                 and not (blk_foot[blks[a]] & blk_foot[blks[b]])]
        if not cands:
            continue
        if len(cands) > 1:
            # several compatible partners ("University of Washington" nests inside
            # Seattle, Tacoma and Bothell). Take the dominant one, or none.
            cands.sort(key=lambda k: -ws[k])
            if ws[cands[0]] < 3 * max(sum(ws[k] for k in cands[1:]), 1):
                continue
        b = cands[0]
        small, big = (blks[b], blks[a]) if ws[a] >= ws[b] else (blks[a], blks[b])
        if try_attach(small, big):
            n2c += 1
say(f"after disjoint-footprint nesting pass: {len(set(bl.blk) - set(attach))} blocks "
    f"({n2c} attached)")


def resolve(b):
    seen = set()
    while b in attach and b not in seen:
        seen.add(b); b = attach[b]
    return b


rec["blk2"] = rec["blk"].map(resolve)

# ---- step 4: split blocks that still double-book an edition. Identical token
# sets in different word order ("Jinan University" vs "University of Jinan") are
# distinct institutions whenever a single edition lists both.
grp = defaultdict(list)
for nn, b in zip(rec.nname, rec.blk2):
    grp[b].append(nn)
splits = 0
final = {}
for b, names in grp.items():
    names = sorted(names, key=lambda n: -len(foot[n]))
    buckets = []                       # list of (footprint, [names])
    for n in names:
        placed = False
        for bu in buckets:
            if not (bu[0] & foot[n]):
                bu[0] |= foot[n]; bu[1].append(n); placed = True; break
        if not placed:
            buckets.append([set(foot[n]), [n]])
    if len(buckets) > 1:
        splits += len(buckets) - 1
    for k, bu in enumerate(buckets):
        for n in bu[1]:
            final[n] = b if k == 0 else f"{b}#{k}"
rec["blk2"] = rec["nname"].map(final)
say(f"after collision split: {rec.blk2.nunique()} entities ({splits} splits)")

# ---- step 5: curated merges reviewed by hand (see CURATED_MERGES above)
name_of = {}
for nn, b in zip(rec.nname, rec.blk2):
    name_of.setdefault(b, []).append(nn)
raw_by_nn = dict(zip(rec.nname, rec.name_raw))
blk_by_display = {}
for b, nns in name_of.items():
    for nn in nns:
        blk_by_display.setdefault(str(raw_by_nn[nn]).strip().lower(), b)

blk_foot2 = defaultdict(set)
for nn, b in zip(rec.nname, rec.blk2):
    blk_foot2[b] |= foot[nn]

cur_map, cur_done, cur_refused, cur_missing = {}, 0, [], []


def _res2(b):
    seen = set()
    while b in cur_map and b not in seen:
        seen.add(b); b = cur_map[b]
    return b


for a_name, b_name in CURATED_MERGES:
    ba = blk_by_display.get(a_name.strip().lower())
    bb = blk_by_display.get(b_name.strip().lower())
    if ba is None or bb is None:
        cur_missing.append((a_name, b_name)); continue
    ba, bb = _res2(ba), _res2(bb)
    if ba == bb:
        continue
    if blk_foot2[ba] & blk_foot2[bb]:
        cur_refused.append((a_name, b_name)); continue
    cur_map[ba] = bb
    blk_foot2[bb] |= blk_foot2[ba]
    cur_done += 1
rec["blk2"] = rec["blk2"].map(_res2)
say(f"curated merges: {cur_done} applied, {len(cur_refused)} refused by the "
    f"collision check, {len(cur_missing)} names not found")
for a_name, b_name in cur_refused:
    say(f"   REFUSED (co-listed in some edition, so genuinely distinct): {a_name} | {b_name}")
for a_name, b_name in cur_missing:
    say(f"   NOT FOUND: {a_name} | {b_name}")

# ============================================================ label & write
lab = (rec.sort_values(["n_sys", "n_obs"], ascending=False)
       .groupby("blk2").agg(inst_name=("name_raw", "first"),
                            inst_country=("country", "first")).reset_index()
       .sort_values("inst_name").reset_index(drop=True))
lab["inst_id"] = ["U%05d" % i for i in range(1, len(lab) + 1)]
rec = rec.merge(lab, on="blk2")

rec[["nname", "name_raw", "inst_id", "inst_name", "inst_country", "n_obs", "n_sys"]] \
    .to_csv(f"{W}/crosswalk.csv", index=False)

panel = long.merge(rec[["nname", "inst_id", "inst_name", "inst_country"]], on="nname", how="left")
agg = panel["inst_name"].astype(str).str.contains(SYSTEM_AGGREGATE)
say(f"dropping {agg.sum()} observations from {panel.loc[agg,'inst_id'].nunique()} "
    f"university-system aggregates (e.g. "
    f"{', '.join(sorted(panel.loc[agg,'inst_name'].unique())[:3])})")
panel = panel[~agg]
ic = (panel.dropna(subset=["country"]).groupby("inst_id")["country"]
      .agg(lambda x: x.value_counts().index[0]))
panel["inst_country"] = panel["inst_id"].map(ic).fillna(panel["inst_country"])
panel.to_csv(f"{W}/panel_long.csv", index=False)

say(f"\n{panel.inst_id.nunique()} institutions / {len(panel)} observations")
dups = panel.duplicated(["inst_id", "system", "year"]).sum()
say(f"duplicate (institution, system, edition) cells: {dups}  "
    f"({dups/len(panel):.3%}) -- should be ~0")
ns = panel.groupby("inst_id")["system"].nunique()
say("institutions by number of ranking systems that ever list them:")
for k in range(1, 11):
    say(f"   >= {k:2d}: {(ns >= k).sum():5d}")

say("\nLargest entities (obs should not exceed the max possible ~120 editions):")
chk = (panel.groupby(["inst_id", "inst_name"])
       .agg(obs=("rank", "size"), variants=("name_raw", "nunique"), systems=("system", "nunique"))
       .sort_values("obs", ascending=False).head(15))
say(chk.to_string())

say("\nSpot checks (each probe should split into the right number of real entities):")
for probe in ["Harvard", "Tokyo", "Oxford", "Michigan", "Florida", "California",
              "Zurich", "Seoul", "Tsinghua"]:
    sub = panel[panel.inst_name.str.contains(probe, case=False, na=False)]
    g = (sub.groupby(["inst_id", "inst_name"])
         .agg(obs=("rank", "size"), sys=("system", "nunique"))
         .sort_values("obs", ascending=False))
    say(f"  -- {probe}: {len(g)} entities; top 5:")
    say(g.head(5).to_string())

open(f"{W}/harmonization_report.txt", "w").write("\n".join(REPORT))
