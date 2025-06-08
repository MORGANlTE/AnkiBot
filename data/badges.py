import os

badges = {
    "clefabadge_locked": 1380968213822570497,
    "eeveebadge_locked": 1380968204310151238,
    "enteibadge_locked": 1380968191676907702,
    "flamebadge_locked": 1380968181367308381,
    "jirachibadge_locked": 1380968169191112754,
    "leafbadge_locked": 1380968155416891552,
    "lugiabadge_locked": 1380968143048147125,
    "mewtwobadge_locked": 1380968131991703562,
    "regicebadge_locked": 1380968103059521628,
    "registeelbadge_locked": 1380968085623668957,
    "snorlaxbadge_locked": 1380968072776515644,
    "staryubadge_locked": 1380968057299537930,
    "stonebadge_locked": 1380968038274171082,
    "waterbadge_locked": 1380968025334878330,
    "staryubadge": 1380913870507479061,
    "regicebadge": 1380913651321667655,
    "jirachibadge": 1380913643591565323,
    "stonebadge": 1380913169874292756,
    "Lugiabadge": 1380913130263154709,
    "mewtwobadge": 1380913117940416583,
    "registeelbadge": 1380913106833768468,
    "waterbadge": 1380912251074253000,
    "snorlaxbadge": 1380912204169220297,
    "clefabadge": 1380912174460964924,
    "eeveebadge": 1380912132589097060
}

test_badges = {
    "stonebadge": 1381352055209463939,
    "waterbadge": 1381352045889589410,
    "staryubadge": 1381352034527215687,
    "leafbadge": 1381352020123844648,
    "eeveebadge": 1381352009403334806,
    "flamebadge": 1381351997915140137,
    "clefabadge": 1381351983813890219,
    "snorlaxbadge": 1381351952020930652,
    "lugiabadge": 1381351938721054800,
    "mewtwobadge": 1381351923277369354,
    "registeelbadge": 1381351906001031268,
    "regicebadge": 1381351880478818406,
    "enteibadge": 1381351867807694928,
    "jirachibadge": 1381351857389310174,
    "waterbadge_locked": 1381351842658914424,
    "stonebadge_locked": 1381351825994944688,
    "staryubadge_locked": 1381351814678581439,
    "snorlaxbadge_locked": 1381351806273191976,
    "registeelbadge_locked": 1381351796328497153,
    "regicebadge_locked": 1381351781153378314,
    "mewtwobadge_locked": 1381351748119171072,
    "lugiabadge_locked": 1381351739088699543,
    "leafbadge_locked": 1381351730452631786,
    "jirachibadge_locked": 1381351721435136092,
    "flamebadge_locked": 1381351712249348096
}

def get_badge_id(badge_name: str) -> int:
    """
    Returns the badge ID for a given badge name.
    
    Args:
        badge_name (str): The name of the badge.
        
    Returns:
        int: The badge ID if found, otherwise -1.
    """
    env = os.getenv("ENVIRONMENT")  # Ensure environment is loaded
    if env == "testing":
        return test_badges.get(badge_name, -1)
    return badges.get(badge_name, -1)