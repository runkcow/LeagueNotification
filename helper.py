
import config

def get_elo (tier: str, rank: str, lp: int) -> int:
    return config.TIER_LP[tier] + config.RANK_LP[rank] + lp

def get_elo_parts (elo: int) -> tuple[str, str, int]:
    (tier, rank) = config.ELO_DISPLAY[-1] if elo // 100 >= len(config.ELO_DISPLAY) else config.ELO_DISPLAY[elo // 100]
    lp = elo - config.TIER_LP[tier] - config.RANK_LP[rank]
    return (tier, rank, lp)

def display_elo (elo: int) -> str:
    tier, rank, lp = get_elo_parts(elo)
    return f'{tier} {rank} {lp}LP'

def second_str_display(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return (f'{h:02}:' if h > 0 else "") + f'{m:02}:{s:02}'


