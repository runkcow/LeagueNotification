
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

DEV_SERVERS = [ 909589494490087494, 415003906951610378 ]

REGIONS = {
    "BR1"  : "br1.api.riotgames.com",
    "EUN1" : "eun1.api.riotgames.com",
    "EUW1" : "euw1.api.riotgames.com",
    "JP1"  : "jp1.api.riotgames.com",
    "KR"   : "kr.api.riotgames.com",
    "LA1"  : "la1.api.riotgames.com",
    "LA2"  : "la2.api.riotgames.com",
    "NA1"  : "na1.api.riotgames.com",
    "OC1"  : "oc1.api.riotgames.com",
    "TR1"  : "tr1.api.riotgames.com",
    "RU"   : "ru.api.riotgames.com",
    "PH2"  : "ph2.api.riotgames.com",
    "SG2"  : "sg2.api.riotgames.com",
    "TH2"  : "th2.api.riotgames.com",
    "TW2"  : "tw2.api.riotgames.com",
    "VN2"  : "vn2.api.riotgames.com",
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
L_TIER_LP = { k : v for k, v in TIER_LP.items() if k != "MASTER" or k != "GRANDMASTER" or k != "CHALLENGER" }

RANK_LP = {
    "IV"  : -300,
    "III" : -200,
    "II"  : -100,
    "I"   : 0,
}

# index 0 means 0 elo, index 15 means 1500 elo
ELO_DISPLAY = [ (T, R) for R in RANK_LP for T in L_TIER_LP ]
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
