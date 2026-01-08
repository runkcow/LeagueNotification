
import config

def get_elo (tier: str, rank: str, lp: int) -> int:
    return config.TIER_LP[tier] + config.RANK_LP[rank] + lp

def _get_tier (elo) -> tuple:
    lp = elo % 100
    rank = config.N_RANK_LP[elo - lp]
    tier = config.N_TIER_LP[elo - config.RANK_LP[rank]] 
    return (tier, rank, lp)

def display_elo (elo) -> str:
    tier, rank, lp = _get_tier(elo)
    return f'{tier} {rank} {lp}LP'

def display_elo_short (elo) ->str:
    tier, rank, lp = _get_tier(elo)
    return f'{tier[0]}{config.RANK_NUMERICAL[rank]} {lp:>2}LP'

def second_str_display(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return (f'{h:02}:' if h > 0 else "") + f'{m:02}:{s:02}'
