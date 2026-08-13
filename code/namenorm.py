"""namenorm.py -- name/country normalisation, extracted verbatim from 02_harmonize.py
so the department pipeline resolves entities identically. Do not edit here without
mirroring the change in 02_harmonize.py."""
import re
import numpy as np
import pandas as pd
from unidecode import unidecode

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


