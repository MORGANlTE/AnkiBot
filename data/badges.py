import os
from data.database import db

def get_badge_id(badge_name: str) -> int:
    """
    Returns the badge ID for a given badge name from the database.
    
    Args:
        badge_name (str): The name of the badge.
        
    Returns:
        int: The badge ID if found, otherwise -1.
    """
    # For locked badges
    if badge_name.endswith('_locked'):
        # Remove '_locked' suffix and get the locked emoji ID
        base_name = badge_name[:-7]
        row = db.fetch_one("SELECT locked_emoji_id FROM badges WHERE name = ?", (base_name,))
        if row and row["locked_emoji_id"] != -1:
            return row["locked_emoji_id"]
    else:
        # For regular badges
        row = db.fetch_one("SELECT emoji_id FROM badges WHERE name = ?", (badge_name,))
        if row and row["emoji_id"] != -1:
            return row["emoji_id"]
    
    # If not found
    return -1