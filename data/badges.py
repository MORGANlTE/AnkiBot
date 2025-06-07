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

def get_badge_id(badge_name: str) -> int:
    """
    Returns the badge ID for a given badge name.
    
    Args:
        badge_name (str): The name of the badge.
        
    Returns:
        int: The badge ID if found, otherwise -1.
    """
    return badges.get(badge_name, -1)