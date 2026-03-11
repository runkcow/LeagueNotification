
import helper

def convert_ranked_data(data: dict = None) -> dict:
    if data is None:
        return {
            "elo": 0,
            "wins": 0,
            "losses": 0,
        }
    return {
        "elo": helper.get_elo(data["tier"], data["rank"], data["leaguePoints"]),
        "wins": data["wins"],
        "losses": data["losses"], 
    }
