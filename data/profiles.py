import json
import os
import datetime
from typing import Dict, List, Any, Optional, Set

# Path for profile data file
PROFILE_DATA_FILE = os.path.join(os.path.dirname(__file__), 'profile_data.json')

# Dictionary to store user profiles by user ID
# Structure: {user_id: {"badges": [{"name": badge_name, "acquired_from": source, "date": date}]}}
user_profiles = {}

def load_profiles():
    """Load profiles from the JSON file."""
    global user_profiles
    if not os.path.exists(PROFILE_DATA_FILE):
        # Make sure the file exists
        os.makedirs(os.path.dirname(PROFILE_DATA_FILE), exist_ok=True)
        with open(PROFILE_DATA_FILE, 'w') as f:
            json.dump({}, f)
        
    try:
        with open(PROFILE_DATA_FILE, 'r') as f:
            user_profiles = json.load(f)
        
        # Migrate old profile format if needed
        for user_id, profile in user_profiles.items():
            if "badges" in profile and isinstance(profile["badges"], list):
                # Check if any badge is a string (old format) and convert to new format
                updated_badges = []
                for badge in profile["badges"]:
                    if isinstance(badge, str):
                        # Convert to new format
                        updated_badges.append({
                            "name": badge,
                            "acquired_from": "Unknown",
                            "date": datetime.datetime.now().isoformat()
                        })
                    else:
                        updated_badges.append(badge)
                profile["badges"] = updated_badges
        
        # Save migrated profiles
        save_profiles()
        print(f"Loaded profiles for {len(user_profiles)} users")
    except Exception as e:
        print(f"Error loading profiles: {e}")
        # Start with empty profiles if there's an error
        user_profiles = {}

def save_profiles():
    """Save profiles to a JSON file."""
    try:
        # Save to file
        os.makedirs(os.path.dirname(PROFILE_DATA_FILE), exist_ok=True)
        with open(PROFILE_DATA_FILE, 'w') as f:
            json.dump(user_profiles, f, indent=2)
        
    except Exception as e:
        print(f"Error saving profiles: {e}")

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Get a user's profile, creating it if it doesn't exist."""
    user_id_str = str(user_id)
    
    if user_id_str not in user_profiles:
        user_profiles[user_id_str] = {
            "badges": [],
            "first_seen": datetime.datetime.now().isoformat()
        }
        save_profiles()
    
    return user_profiles[user_id_str]

def get_user_badges(user_id: int) -> List[Dict[str, Any]]:
    """Get a list of badge objects that the user has earned."""
    profile = get_user_profile(user_id)
    return profile.get("badges", [])

def get_user_badge_names(user_id: int) -> List[str]:
    """Get a list of badge names that the user has earned."""
    badges = get_user_badges(user_id)
    return [badge["name"] for badge in badges]

def has_badge(user_id: int, badge_name: str) -> bool:
    """Check if a user has a specific badge."""
    badge_names = get_user_badge_names(user_id)
    return badge_name in badge_names

def award_badge(user_id: int, badge_name: str, acquired_from: str = "Unknown") -> bool:
    """Award a badge to a user. Returns True if the badge was newly awarded."""
    profile = get_user_profile(user_id)
    
    # Check if user already has this badge
    if has_badge(user_id, badge_name):
        return False
    
    # Create badge entry with acquisition details
    badge_entry = {
        "name": badge_name,
        "acquired_from": acquired_from,
        "date": datetime.datetime.now().isoformat()
    }
    
    if "badges" not in profile:
        profile["badges"] = []
    
    profile["badges"].append(badge_entry)
    save_profiles()
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
    profile = get_user_profile(user_id)
    
    # Check for early adopter badge (first profile access before 2025-09-01)
    if not has_badge(user_id, "snorlaxbadge"):
        today = datetime.datetime.now()
        cutoff_date = datetime.datetime(2025, 9, 1)
        
        if today < cutoff_date:
            award_badge(user_id, "snorlaxbadge", "Early adopter")

# Load profiles when module is imported
load_profiles()
