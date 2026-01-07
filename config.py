
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

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
    "VN2"  : "vn2.api.riotgames.com"
}

TIER_LP = {
    "IRON"     : 0,
    "BRONZE"   : 400,
    "SILVER"   : 800,
    "GOLD"     : 1200,
    "PLATINUM" : 1600,
    "EMERALD"  : 2000,
    "DIAMOND"  : 2400,
    "MASTER"   : 2800,
}
N_TIER_LP = { v: k for k, v in TIER_LP.items() }

RANK_LP = {
    "I"   : 300,
    "II"  : 200,
    "III" : 100,
    "IV"  : 0
}
N_RANK_LP = { v: k for k, v in RANK_LP.items() }

# RANK_NUMERICAL = {
#     "I"   : 1,
#     "II"  : 2,
#     "III" : 3,
#     "IV"  : 4
# }

TRANSLATE_ACCOUNT_DTO = {
    "puuid"    : "puuid",
    "gameName" : "username",
    "tagLine"  : "tag"
}

