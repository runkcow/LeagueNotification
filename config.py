
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

DEV_SERVERS = [ 909589494490087494, 415003906951610378 ]

REGIONS = {
    "br1"  : "americas",
    "la1"  : "americas",
    "la2"  : "americas",
    "na1"  : "americas",
    "oc1"  : "americas",
    "eun1" : "europe",
    "euw1" : "europe",
    "tr1"  : "europe",
    "ru"   : "europe",
    "jp1"  : "asia",
    "kr"   : "asia",
    "ph2"  : "sea",
    "sg2"  : "sea",
    "th2"  : "sea",
    "tw2"  : "sea",
    "vn2"  : "sea",
}

# TODO: generate grandmaster and challenger cutoffs on the fly
TIER_LP = {
    "IRON"        : 300,
    "BRONZE"      : 700,
    "SILVER"      : 1100,
    "GOLD"        : 1500,
    "PLATINUM"    : 1900,
    "EMERALD"     : 2300,
    "DIAMOND"     : 2700,
    "MASTER"      : 2800, 
    "GRANDMASTER" : 2800,
    "CHALLENGER"  : 2800,
}
L_TIER_LP = { k : v for k, v in TIER_LP.items() if k != "MASTER" and k != "GRANDMASTER" and k != "CHALLENGER" }

RANK_LP = {
    "IV"  : -300,
    "III" : -200,
    "II"  : -100,
    "I"   : 0,
}

# index 0 means 0 elo, index 15 means 1500 elo
ELO_DISPLAY = [ (T, R) for T in L_TIER_LP for R in RANK_LP ]
ELO_DISPLAY.append(("MASTER", "I")) # 2800 elo and above is MASTER I

RANK_NUMERICAL = {
    "I"   : 1,
    "II"  : 2,
    "III" : 3,
    "IV"  : 4
}

TRANSLATE_ACCOUNT_DTO = {
    "puuid"    : "puuid",
    "gameName" : "username",
    "tagLine"  : "tag"
}

PC_TEXT_WRAP = 45

TEAM_NAME_LEN = 4
TEAM_ID = {
    100 : "BLUE",
    200 : "RED",
}

SUB_TEAM_LEN = 8
SUB_TEAM_ID = {
    0 : None,
    1 : "PORO",
    2 : "MINION",
    3 : "SCUTTLE",
    4 : "KRUGS",
    5 : "RAPTOR",
    6 : "SENTINEL",
    7 : "WOLVES",
    8 : "GROMP",
}

TEAM_DISPLAY_NAME = {
    **TEAM_ID,
    **SUB_TEAM_ID,
}
