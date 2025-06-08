import discord
import json
import os
import datetime
from typing import List, Dict, Any, Optional, Tuple
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import asyncio

# Path for event data file
EVENT_DATA_FILE = os.path.join(os.path.dirname(__file__), 'event_data.json')

# Dictionary to store active events by guild ID
# Structure: {guild_id: {event_name: EventData}}
active_events = {}

class EventData:
    def __init__(self, name: str, event_type: str, start_date: str, end_date: str, creator_id: int):
        self.name = name
        self.event_type = event_type
        self.start_date = start_date
        self.end_date = end_date
        self.creator_id = creator_id
        self.pokemon_list = []  # List of Pokémon IDs to catch
        self.participants = {}  # Dictionary of user_id -> {submitted: bool, data: Any}
        self.badge_reward = None  # Badge name to award
        self.required_completion = 100  # Percentage required to earn badge (default 100%)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'event_type': self.event_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'creator_id': self.creator_id,
            'pokemon_list': self.pokemon_list,
            'participants': self.participants,
            'badge_reward': self.badge_reward,
            'required_completion': self.required_completion
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventData':
        event = cls(
            data['name'],
            data['event_type'],
            data['start_date'],
            data['end_date'],
            data['creator_id']
        )
        event.pokemon_list = data['pokemon_list']
        event.participants = data['participants']
        event.badge_reward = data.get('badge_reward')
        event.required_completion = data.get('required_completion', 100)
        return event

def load_events():
    """Load events from the JSON file."""
    global active_events
    if not os.path.exists(EVENT_DATA_FILE):
        # make sure the file exists
        os.makedirs(os.path.dirname(EVENT_DATA_FILE), exist_ok=True)
        with open(EVENT_DATA_FILE, 'w') as f:
            json.dump({}, f)
        
    try:
        with open(EVENT_DATA_FILE, 'r') as f:
            data = json.load(f)
            
        # Convert guild_ids from string back to int
        for guild_id_str, guild_events in data.items():
            guild_id = int(guild_id_str)
            active_events[guild_id] = {}
            
            for event_name, event_data in guild_events.items():
                active_events[guild_id][event_name] = EventData.from_dict(event_data)
        
        print(f"Loaded events for {len(active_events)} guilds")
    except Exception as e:
        print(f"Error loading events: {e}")
        # Start with empty events if there's an error
        active_events = {}

def save_events():
    """Save events to a JSON file."""
    try:
        # Convert events to a serializable format
        data = {}
        
        for guild_id, guild_events in active_events.items():
            guild_data = {}
            
            for event_name, event in guild_events.items():
                guild_data[event_name] = event.to_dict()
            
            data[str(guild_id)] = guild_data
        
        # Save to file
        os.makedirs(os.path.dirname(EVENT_DATA_FILE), exist_ok=True)
        with open(EVENT_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
    except Exception as e:
        print(f"Error saving events: {e}")

def create_event(guild_id: int, name: str, event_type: str, start_date: str, end_date: str, creator_id: int) -> Tuple[bool, str]:
    """Create a new event.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    # Validate dates
    try:
        start = datetime.datetime.fromisoformat(start_date)
        end = datetime.datetime.fromisoformat(end_date)
        
        if start >= end:
            return False, "End date must be after start date."
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS."
    
    # Validate event type
    if event_type not in ["catch"]:
        return False, "Invalid event type. Currently only 'catch' is supported."
    
    # Initialize guild events dictionary if needed
    if guild_id not in active_events:
        active_events[guild_id] = {}
    
    # Check if event with this name already exists in this guild
    if name in active_events[guild_id]:
        return False, "An event with this name already exists."
    
    # Create the event
    event = EventData(name, event_type, start_date, end_date, creator_id)
    active_events[guild_id][name] = event
    
    # Save events
    save_events()
    
    return True, "Event created successfully."

def delete_event(guild_id: int, event_name: str) -> bool:
    """Delete an event."""
    if guild_id not in active_events:
        return False
    
    if event_name not in active_events[guild_id]:
        return False
    
    del active_events[guild_id][event_name]
    
    # Clean up if guild has no events
    if not active_events[guild_id]:
        del active_events[guild_id]
    
    save_events()
    return True

def get_event(guild_id: int, event_name: str) -> Optional[EventData]:
    """Get an event by guild ID and name."""
    if guild_id not in active_events:
        return None
    return active_events[guild_id].get(event_name)

def get_events(guild_id: int) -> List[EventData]:
    """Get all events for a guild."""
    if guild_id not in active_events:
        return []
    return list(active_events[guild_id].values())

def get_active_events(guild_id: int) -> List[EventData]:
    """Get all currently active events (between start and end date) for a guild."""
    if guild_id not in active_events:
        return []
        
    now = datetime.datetime.now()
    return [
        event for event in active_events[guild_id].values()
        if datetime.datetime.fromisoformat(event.start_date) <= now <= datetime.datetime.fromisoformat(event.end_date)
    ]

def set_pokemon_list(guild_id: int, event_name: str, pokemon_list: List[int]) -> bool:
    """Set the list of Pokémon for a catch event."""
    event = get_event(guild_id, event_name)
    if not event:
        return False
    
    if event.event_type != "catch":
        return False
    
    event.pokemon_list = pokemon_list
    save_events()
    return True

def add_participant(guild_id: int, event_name: str, user_id: int) -> bool:
    """Add a participant to an event."""
    event = get_event(guild_id, event_name)
    if not event:
        return False
    
    # Convert user_id to string for consistent storage
    user_id_str = str(user_id)
    
    if user_id_str not in event.participants:
        event.participants[user_id_str] = {"submitted": False, "data": None}
        save_events()
    
    return True

def submit_entry(guild_id: int, event_name: str, user_id: int, entry_data: Any) -> bool:
    """Submit an entry for an event."""
    event = get_event(guild_id, event_name)
    if not event:
        return False
    
    # Convert user_id to string for consistent storage
    user_id_str = str(user_id)
    
    # Add participant if not already in the event
    add_participant(guild_id, event_name, user_id)
    
    # Update their entry
    event.participants[user_id_str] = {"submitted": True, "data": entry_data}
    save_events()
    return True

async def validate_catch_event_entry(entry_data: Any, pokemon_list: List[int]) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate a submission for a catch event.
    
    Returns:
        Tuple[bool, str, Dict[str, Any]]: (success, message, validation_results)
    """
    # Check if entry is a list of Pokemon objects
    if not isinstance(entry_data, list):
        return False, "Submission must be a list of Pokémon objects.", {}
    
    # Track which Pokemon from the required list have been caught
    caught_pokemon = {}
    missing_pokemon = set(pokemon_list)
    
    # Process each Pokemon in the submission
    for pokemon in entry_data:
        # Validate it has the required fields
        if not isinstance(pokemon, dict) or 'id' not in pokemon:
            continue  # Skip invalid entries
        
        pokemon_id = pokemon.get('id')
        
        # Check if this is one of the required Pokemon
        if pokemon_id in pokemon_list:
            # Add to caught list
            caught_pokemon[pokemon_id] = {
                'name': pokemon.get('name', f"Pokémon #{pokemon_id}"),
                'capture_date': pokemon.get('captured_date', 'Unknown date'),
                'level': pokemon.get('level', '?'),
                'nickname': pokemon.get('nickname', '')
            }
            
            # Remove from missing list
            if pokemon_id in missing_pokemon:
                missing_pokemon.remove(pokemon_id)
    
    # Build results dictionary
    validation_results = {
        'caught': caught_pokemon,
        'missing': list(missing_pokemon),
        'total_required': len(pokemon_list),
        'total_caught': len(caught_pokemon)
    }
    
    # Determine success based on whether all required Pokemon are caught
    success = len(missing_pokemon) == 0
    
    # Build message
    if success:
        message = f"You have caught all {len(pokemon_list)} required Pokémon!"
    else:
        message = f"You have caught {len(caught_pokemon)} out of {len(pokemon_list)} required Pokémon."
    
    return success, message, validation_results

async def generate_pokemon_image(pokemon_ids: List[int]) -> Optional[io.BytesIO]:
    """Generate an image showing all Pokémon required for the event."""
    if not pokemon_ids:
        return None
    
    # Constants for image generation
    POKEMON_PER_ROW = 5
    CELL_SIZE = 150
    PADDING = 20
    TITLE_HEIGHT = 60
    
    # Calculate image dimensions
    rows = (len(pokemon_ids) - 1) // POKEMON_PER_ROW + 1
    img_width = POKEMON_PER_ROW * CELL_SIZE + PADDING * 2
    img_height = rows * CELL_SIZE + PADDING * 2 + TITLE_HEIGHT
    
    # Create base image
    image = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        number_font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        # Fallback to default font
        title_font = ImageFont.load_default()
        number_font = ImageFont.load_default()
    
    # Draw title
    title = f"Pokémon to Catch: {len(pokemon_ids)}"
    draw.text((PADDING, PADDING), title, fill=(0, 0, 0), font=title_font)
    
    # Fetch and draw Pokémon sprites
    async with aiohttp.ClientSession() as session:
        for i, pokemon_id in enumerate(pokemon_ids):
            row = i // POKEMON_PER_ROW
            col = i % POKEMON_PER_ROW
            
            x = PADDING + col * CELL_SIZE
            y = PADDING + TITLE_HEIGHT + row * CELL_SIZE
            
            # Draw Pokémon number
            draw.text((x + 5, y + 5), f"#{pokemon_id}", fill=(100, 100, 100), font=number_font)
            
            # Fetch Pokémon sprite
            try:
                async with session.get(f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png") as resp:
                    if resp.status == 200:
                        sprite_data = await resp.read()
                        sprite = Image.open(io.BytesIO(sprite_data)).convert('RGBA')
                        
                        # Center the sprite in the cell
                        sprite_x = x + (CELL_SIZE - sprite.width) // 2
                        sprite_y = y + (CELL_SIZE - sprite.height) // 2
                        
                        image.paste(sprite, (sprite_x, sprite_y), sprite)
            except Exception as e:
                print(f"Error fetching sprite for Pokémon #{pokemon_id}: {e}")
                # Draw placeholder
                draw.rectangle([(x + 20, y + 20), (x + CELL_SIZE - 20, y + CELL_SIZE - 20)], outline=(200, 200, 200))
                draw.text((x + 35, y + 50), f"#{pokemon_id}", fill=(150, 150, 150), font=title_font)
    
    # Save image to BytesIO
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    
    return output

# Event autocomplete
async def event_name_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete function for event names in the guild."""
    guild_id = interaction.guild_id
    
    if guild_id not in active_events:
        return []
    
    events = list(active_events[guild_id].keys())
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in events if current.lower() in name.lower()
    ][:25]  # Discord limits to 25 choices

# Helper function to get Pokemon names from API
async def get_pokemon_names(pokemon_ids: List[int]) -> Dict[int, str]:
    """Get Pokemon names from the PokeAPI."""
    names = {}
    async with aiohttp.ClientSession() as session:
        for pokemon_id in pokemon_ids:
            try:
                async with session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        names[pokemon_id] = data['name'].capitalize()
                    else:
                        names[pokemon_id] = f"Pokémon #{pokemon_id}"
            except Exception:
                names[pokemon_id] = f"Pokémon #{pokemon_id}"
    return names

def set_badge_reward(guild_id: int, event_name: str, badge_name: str, required_completion: int) -> bool:
    """Set the badge reward for an event."""
    event = get_event(guild_id, event_name)
    if not event:
        return False
    
    # Validate completion percentage
    if required_completion < 1 or required_completion > 100:
        return False
    
    event.badge_reward = badge_name
    event.required_completion = required_completion
    save_events()
    return True

def end_event(guild_id: int, event_name: str) -> Tuple[bool, Dict[str, Any]]:
    """End an event and calculate rewards.
    
    Returns:
        Tuple[bool, Dict[str, Any]]: (success, results)
    """
    event = get_event(guild_id, event_name)
    if not event:
        return False, {"error": "Event not found"}
    
    # Process results
    results = {
        "name": event.name,
        "qualified_users": [],
        "badge_awarded": event.badge_reward,
        "required_completion": event.required_completion
    }
    
    if event.badge_reward:
        qualified_users = []
        
        for user_id, participant_data in event.participants.items():
            if participant_data.get("submitted", False):
                # Get completion percentage
                submission_data = participant_data.get("data", {})
                completion = submission_data.get("completion_percentage", 0)
                
                # Check if user qualifies for the badge
                if completion >= event.required_completion:
                    qualified_users.append(int(user_id))
        
        results["qualified_users"] = qualified_users
    
    # Delete the event
    if delete_event(guild_id, event_name):
        return True, results
    else:
        return False, {"error": "Failed to delete event"}

# Load events when module is imported
load_events()
