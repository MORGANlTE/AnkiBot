import datetime
from typing import Dict, List, Any, Optional
from data.database import db
print("test")

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Get a user's profile, creating it if it doesn't exist."""
    # Check if user exists
    user = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    
    if not user:
        # Create new user
        now = datetime.datetime.now().isoformat()
        db.execute(
            "INSERT INTO users (id, first_seen, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, now, now, now)
        )
        return {"id": user_id, "first_seen": now, "badges": []}
    
    # Get user badges
    badges = get_user_badges(user_id)
    
    return {
        "id": user_id,
        "first_seen": user["first_seen"],
        "badges": badges
    }

def get_user_badges(user_id: int) -> List[Dict[str, Any]]:
    """Get a list of badge objects that the user has earned."""
    rows = db.fetch_all(
        """SELECT ub.badge_name, ub.acquired_from, ub.date, b.emoji_id 
           FROM user_badges ub
           JOIN badges b ON ub.badge_name = b.name
           WHERE ub.user_id = ?""",
        (user_id,)
    )
    
    return [
        {
            "name": row["badge_name"],
            "acquired_from": row["acquired_from"],
            "date": row["date"],
            "emoji_id": row["emoji_id"]
        }
        for row in rows
    ]

def get_user_badge_names(user_id: int) -> List[str]:
    """Get a list of badge names that the user has earned."""
    rows = db.fetch_all(
        "SELECT badge_name FROM user_badges WHERE user_id = ?",
        (user_id,)
    )
    
    return [row["badge_name"] for row in rows]

def has_badge(user_id: int, badge_name: str) -> bool:
    """Check if a user has a specific badge."""
    row = db.fetch_one(
        "SELECT 1 FROM user_badges WHERE user_id = ? AND badge_name = ?",
        (user_id, badge_name)
    )
    
    return row is not None

def award_badge(user_id: int, badge_name: str, acquired_from: str = "Unknown") -> bool:
    """Award a badge to a user. Returns True if the badge was newly awarded."""
    # Check if badge exists
    badge = db.fetch_one("SELECT name FROM badges WHERE name = ?", (badge_name,))
    if not badge:
        print(f"Warning: Attempted to award non-existent badge '{badge_name}'")
        return False
    
    # Check if user already has this badge
    if has_badge(user_id, badge_name):
        return False
    
    # Make sure user exists
    get_user_profile(user_id)
    
    # Award badge
    now = datetime.datetime.now().isoformat()
    db.execute(
        "INSERT INTO user_badges (user_id, badge_name, acquired_from, date) VALUES (?, ?, ?, ?)",
        (user_id, badge_name, acquired_from, now)
    )
    
    return True

def award_badges_to_users(user_ids: List[int], badge_name: str, acquired_from: str = "Unknown") -> Dict[int, bool]:
    """Award a badge to multiple users at once.
    Returns a dictionary of user_id -> success pairs."""
    results = {}
    for user_id in user_ids:
        results[user_id] = award_badge(user_id, badge_name, acquired_from)
    return results

def check_special_badges(user_id: int):
    """Check and award special badges based on criteria."""
    # Check for early adopter badge (first profile access before 2025-09-01)
    if not has_badge(user_id, "snorlaxbadge"):
        today = datetime.datetime.now()
        cutoff_date = datetime.datetime(2025, 9, 1)
        
        if today < cutoff_date:
            award_badge(user_id, "snorlaxbadge", "Early adopter")

def get_all_badges() -> List[Dict[str, Any]]:
    """Get all available badges."""
    rows = db.fetch_all("SELECT * FROM badges")
    
    return [dict(row) for row in rows]

def get_badge_details(badge_name: str) -> Optional[Dict[str, Any]]:
    """Get details for a specific badge."""
    row = db.fetch_one("SELECT * FROM badges WHERE name = ?", (badge_name,))
    
    return dict(row) if row else None
