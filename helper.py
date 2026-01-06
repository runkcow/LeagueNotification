
import config

def get_elo (tier: str, rank: str, lp: int) -> int:
    return config.TIER_LP[tier] + config.RANK_LP[rank] + lp

def display_elo (elo) -> tuple:
    lp = elo % 100
    rank = config.N_RANK_LP[elo - lp]
    tier = config.N_TIER_LP[elo - config.RANK_LP[rank]] 
    return (tier, rank, lp)
