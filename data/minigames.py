import discord
import aiohttp
from data.help_functions import fetch_data, POKEAPI_BASE_URL
from PIL import Image
import io
import random  # Added import
from data.game_state import active_pokemon_guesses
import json
import os
from typing import Dict, List, Any, Optional

# Path for minigame data file
MINIGAME_DATA_FILE = os.path.join(os.path.dirname(__file__), 'minigame_data.json')

# Default minigames if no file exists
DEFAULT_MINIGAMES = [
    {
        "name": "Guess the Pokémon",
        "description": "Try to guess the Pokémon from its silhouette!",
        "type": "guess_pokemon"
    },
    {
        "name": "Pokémon Trivia",
        "description": "Answer trivia questions about Pokémon!",
        "type": "pokemon_trivia"
    }
]

# Store loaded minigames
minigames = []

def load_minigames():
    """Load minigames from the JSON file."""
    global minigames
    
    if not os.path.exists(MINIGAME_DATA_FILE):
        # Create default file if it doesn't exist
        minigames = DEFAULT_MINIGAMES
        save_minigames()
        return
    
    try:
        with open(MINIGAME_DATA_FILE, 'r') as f:
            minigames = json.load(f)
        print(f"Loaded {len(minigames)} minigames")
    except Exception as e:
        print(f"Error loading minigames: {e}")
        # Use defaults if there's an error
        minigames = DEFAULT_MINIGAMES
        save_minigames()

def save_minigames():
    """Save minigames to a JSON file."""
    try:
        os.makedirs(os.path.dirname(MINIGAME_DATA_FILE), exist_ok=True)
        with open(MINIGAME_DATA_FILE, 'w') as f:
            json.dump(minigames, f, indent=2)
    except Exception as e:
        print(f"Error saving minigames: {e}")

def get_minigame(minigame_type: str) -> Optional[Dict[str, Any]]:
    """Get a minigame by type."""
    return next((m for m in minigames if m["type"] == minigame_type), None)

def add_minigame(name: str, description: str, minigame_type: str) -> bool:
    """Add a new minigame."""
    if any(m["type"] == minigame_type for m in minigames):
        return False  # Minigame type already exists
    
    minigames.append({
        "name": name,
        "description": description,
        "type": minigame_type
    })
    
    save_minigames()
    return True

def remove_minigame(minigame_type: str) -> bool:
    """Remove a minigame by type."""
    global minigames
    original_length = len(minigames)
    minigames = [m for m in minigames if m["type"] != minigame_type]
    
    if len(minigames) < original_length:
        save_minigames()
        return True
    return False

# Active minigame sessions
active_pokemon_guesses = {}

# Guess the Pokémon game
async def play_pokemon_guess(interaction: discord.Interaction, pokemon_id: int):
    """Play the Guess the Pokémon minigame."""
    channel = interaction.channel
    user = interaction.user
    
    # Setup game data
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}") as response:
            if response.status != 200:
                await interaction.followup.send("Sorry, I couldn't fetch Pokémon data right now.")
                return
            data = await response.json()
        
        pokemon_name = data['name'].lower()
        sprite_url = data['sprites']['other']['official-artwork']['front_default']
        
        if not sprite_url:
            sprite_url = data['sprites']['front_default']
            
        if not sprite_url:
            await interaction.followup.send("Sorry, I couldn't find a sprite for this Pokémon.")
            return
        
        # Store the game state
        active_pokemon_guesses[channel.id] = {
            'active': True,
            'pokemon_name': pokemon_name,
            'starter': user.id,
            'guesses': 0
        }
        
        # Create silhouette image
        embed = discord.Embed(
            title="Guess the Pokémon!",
            description="Type your guess in the chat!",
            color=discord.Color.blue()
        )
        
        # Use the silhouette URL (you would need to process the image to make a silhouette)
        embed.set_image(url=sprite_url)
        
        await interaction.followup.send(embed=embed)

# Pokémon Trivia game
async def play_pokemon_trivia(interaction: discord.Interaction, pokemon_id: int):
    """Play the Pokémon Trivia minigame."""
    # Implementation for trivia game
    await interaction.followup.send("Pokémon Trivia game will be implemented soon!")

# Play a random minigame
async def play_random_minigame(interaction: discord.Interaction, pokemon_id: int):
    """Play a random minigame."""
    # Ensure minigames are loaded
    if not minigames:
        load_minigames()
    
    # Select a random minigame
    selected_minigame = random.choice(minigames)
    
    # Play the selected minigame
    if selected_minigame["type"] == "guess_pokemon":
        await play_pokemon_guess(interaction, pokemon_id)
    elif selected_minigame["type"] == "pokemon_trivia":
        await play_pokemon_trivia(interaction, pokemon_id)
    else:
        await interaction.followup.send(f"Unknown minigame type: {selected_minigame['type']}")

async def evaluate_guess(guess: str, pokemon_name: str, channel, user):
    """Evaluate a user's guess in the Pokémon guessing game."""
    if guess.lower() == pokemon_name:
        # Correct guess
        embed = discord.Embed(
            title="Correct!",
            description=f"{user.mention} guessed it right! The Pokémon was **{pokemon_name.capitalize()}**!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)
        
        # End the game
        if channel.id in active_pokemon_guesses:
            active_pokemon_guesses[channel.id]['active'] = False
    else:
        # Increment guess counter
        if channel.id in active_pokemon_guesses:
            active_pokemon_guesses[channel.id]['guesses'] += 1
            
            # After a certain number of guesses, provide a hint
            if active_pokemon_guesses[channel.id]['guesses'] % 5 == 0:
                # Simple hint: first letter
                hint = f"Hint: The Pokémon's name starts with '{pokemon_name[0].upper()}'."
                await channel.send(hint)

# Load minigames when module is imported
load_minigames()
