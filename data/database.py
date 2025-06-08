import sqlite3
import os
import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

# Database file path
DB_FILE = os.path.join(os.path.dirname(__file__), 'ankibot.db')

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        """Initialize the database connection and create tables if they don't exist"""
        self.conn = None
        self.setup_database()
    
    def get_connection(self):
        """Get a connection to the database"""
        if self.conn is None:
            self.conn = sqlite3.connect(DB_FILE)
            self.conn.row_factory = sqlite3.Row  # This allows access to columns by name
        return self.conn
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def setup_database(self):
        """Create tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_seen TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # Badges table (badge definitions)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            name TEXT PRIMARY KEY,
            emoji_id INTEGER,
            locked_emoji_id INTEGER,
            description TEXT
        )
        ''')
        
        # User badges table (which badges each user has)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            badge_name TEXT,
            acquired_from TEXT,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(badge_name) REFERENCES badges(name)
        )
        ''')
        
        # Events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            event_type TEXT,
            start_date TEXT,
            end_date TEXT,
            creator_id INTEGER,
            badge_reward TEXT,
            required_completion INTEGER,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(guild_id, name)
        )
        ''')
        
        # Event Pokémon table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            pokemon_id INTEGER,
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
        )
        ''')
        
        # Event participants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            submitted INTEGER DEFAULT 0,
            total_caught INTEGER DEFAULT 0,
            total_required INTEGER DEFAULT 0,
            completion_percentage REAL DEFAULT 0,
            date_submitted TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Initialize badges
        self._initialize_badges()
        
        conn.commit()
    
    def _initialize_badges(self):
        """Initialize badge data if the table is empty"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if badges table is empty
        cursor.execute("SELECT COUNT(*) FROM badges")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Initialize with predefined badges
            if os.getenv("ENVIRONMENT") == "production":
                badges_dict = {
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
                    "lugiabadge": 1380913130263154709,
                    "mewtwobadge": 1380913117940416583,
                    "registeelbadge": 1380913106833768468,
                    "waterbadge": 1380912251074253000,
                    "snorlaxbadge": 1380912204169220297,
                    "clefabadge": 1380912174460964924,
                    "eeveebadge": 1380912132589097060
                }
            else:
                badges_dict = {
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
            
            # Process the dictionaries to create badge records for insertion
            badges_data = []
            
            # First, collect all the base badge names (without _locked)
            base_badges = set()
            for badge_name in badges_dict.keys():
                if not badge_name.endswith('_locked'):
                    base_badges.add(badge_name)
                else:
                    # Add the base version of locked badges
                    base_badges.add(badge_name[:-7])
            
            # For each base badge, create a database record with its emoji_id and locked_emoji_id
            for badge_name in base_badges:
                emoji_id = badges_dict.get(badge_name, -1)
                locked_emoji_id = badges_dict.get(f"{badge_name}_locked", -1)
                description = f"The {badge_name.capitalize()} badge"
                
                badges_data.append((badge_name, emoji_id, locked_emoji_id, description))
            
            cursor.executemany(
                "INSERT INTO badges (name, emoji_id, locked_emoji_id, description) VALUES (?, ?, ?, ?)",
                badges_data
            )
            
            conn.commit()
            print("Initialized badge definitions")
    
    def execute(self, query, params=None):
        """Execute a query with optional parameters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    
    def fetch_one(self, query, params=None):
        """Execute a query and fetch one result"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query, params=None):
        """Execute a query and fetch all results"""
        cursor = self.execute(query, params)
        return cursor.fetchall()

# Initialize the database manager
db = DatabaseManager()
