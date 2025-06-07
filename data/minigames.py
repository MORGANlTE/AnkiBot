import discord
import aiohttp
from data.help_functions import fetch_data, POKEAPI_BASE_URL
from PIL import Image
import io
import random
from data.game_state import active_pokemon_guesses
import json
import os
from typing import Dict, List, Any, Optional

# Store loaded minigames
minigames = []

async def who_is_that_pokemon_visible(interaction: discord.Interaction, pokemon_id: int):
  """
  Guesses the Pokémon by showing the full sprite instead of a pokémon.
  """
  async with aiohttp.ClientSession() as session:
          # Fetch the Pokemon data
          data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}")
          
          if data is None or data == "error":
              await interaction.followup.send("Sorry, an error occurred while fetching Pokémon data.")
              return
          
          name = data['name'].capitalize()
          sprite_url = data['sprites']['front_default']
          
          if not sprite_url:
              await interaction.followup.send("This Pokémon doesn't have a sprite available.")
              return
          
          # Download the sprite image
          async with session.get(sprite_url) as response:
              if response.status != 200:
                  await interaction.followup.send("I couldn't download the Pokémon sprite.")
                  return
              
              image_data = await response.read()
              
          # Process the image - create a silhouette
          file = discord.File(io.BytesIO(image_data), filename="who_is_that_pokemon.png")

          embed = discord.Embed(
              title="Who's that Pokémon?",
              description="Guess the Pokémon in the chat!",
              color=discord.Color.blue()
          )
          embed.set_image(url="attachment://who_is_that_pokemon.png")
          
          # Store the current Pokemon being guessed
          active_pokemon_guesses[interaction.channel_id] = {
              'pokemon_name': name.lower(),
              'active': True,
              'guesses': 0  # Initialize guess counter
          }
          
          await interaction.followup.send(file=file, embed=embed)

async def who_is_that_pokemon(interaction: discord.Interaction, pokemon_id: int):
  """Starts the 'Who's that Pokémon?' minigame by showing a silhouette of a Pokémon. With hints!"""
  async with aiohttp.ClientSession() as session:
          # Fetch the Pokemon data
          data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}")
          
          if data is None or data == "error":
              await interaction.followup.send("Sorry, an error occurred while fetching Pokémon data.")
              return
          
          name = data['name'].capitalize()
          sprite_url = data['sprites']['front_default']
          
          if not sprite_url:
              await interaction.followup.send("This Pokémon doesn't have a sprite available.")
              return
          
          # Download the sprite image
          async with session.get(sprite_url) as response:
              if response.status != 200:
                  await interaction.followup.send("I couldn't download the Pokémon sprite.")
                  return
              
              image_data = await response.read()
              
          # Process the image - create a silhouette
          img = Image.open(io.BytesIO(image_data))
          
          # Convert to RGB mode first to ensure compatibility
          if img.mode != 'RGBA':
              img = img.convert('RGBA')
              
          # Create a silhouette by converting to black
          # Instead of using brightness which causes errors, we'll create a silhouette directly
          width, height = img.size
          silhouette = Image.new('RGBA', (width, height), color='black')
          
          # Create a mask from the original image's alpha channel if it exists
          if 'A' in img.getbands():
              mask = img.getchannel('A')
              silhouette.putalpha(mask)
          else:
              # If no alpha channel, create a mask based on non-white pixels
              # Convert to grayscale first
              gray = img.convert('L')
              # Create a binary mask where non-background pixels are white
              threshold = 3  # Adjust if needed
              mask = gray.point(lambda p: 255 if p > threshold else 0)
              silhouette.putalpha(mask)
          
          # Save the processed image to a BytesIO object
          img_byte_arr = io.BytesIO()
          silhouette.save(img_byte_arr, format='PNG')
          img_byte_arr.seek(0)  # Move to the beginning of BytesIO
          
          # Send the silhouette image and start the guessing game
          file = discord.File(img_byte_arr, filename="who_is_that_pokemon.png")
          embed = discord.Embed(
              title="Who's that Pokémon?",
              description="Guess the Pokémon in the chat!",
              color=discord.Color.blue()
          )
          embed.set_image(url="attachment://who_is_that_pokemon.png")

          embed.add_field(
              name="Hint",
              value="||"+"||, ||".join([t['type']['name'].capitalize() for t in data['types']]) + "||",
              inline=False)
          
          # Store the current Pokemon being guessed
          active_pokemon_guesses[interaction.channel_id] = {
              'pokemon_name': name.lower(),
              'active': True,
              'guesses': 0  # Initialize guess counter
          }
          
          await interaction.followup.send(file=file, embed=embed)

async def unscramble_pokemon(interaction: discord.Interaction, pokemon_id: int):
    """Play the Pokémon name unscrambling minigame."""
    async with aiohttp.ClientSession() as session:
        # Fetch the Pokemon data
        data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}")
        
        if data is None or data == "error":
            await interaction.followup.send("Sorry, an error occurred while fetching Pokémon data.")
            return
        
        name = data['name'].capitalize()
        
        # Scramble the Pokémon name
        name_list = list(name.lower())
        random.shuffle(name_list)
        scrambled_name = "".join(name_list)
        
        # Ensure scrambled name is different from original, reshuffle if not (for short names)
        if len(name) > 1:  # Avoid infinite loop for single-letter names (though unlikely for Pokemon)
            while scrambled_name == name.lower():
                random.shuffle(name_list)
                scrambled_name = "".join(name_list)
        
        embed = discord.Embed(
            title="Unscramble This Pokémon!",
            description=f"The scrambled name is: \n**{scrambled_name}**\n\nType your guess in the chat!",
            color=discord.Color.blue()
        )
        
        # Take the image from the original Pokémon
        sprite_url = data['sprites']['front_default']
        file = None
        
        # Transform the sprite image into very pixelated image
        if sprite_url:
            async with session.get(sprite_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    img = Image.open(io.BytesIO(image_data))
                    # Resize to create a pixelated effect
                    img_byte_arr = io.BytesIO()
                    image_tiny = img.resize((6, 6))    # resize it to a relatively tiny size
                    # pixelization is resizing a smaller image into a larger one with some resampling
                    pixelated = image_tiny.resize(img.size, Image.NEAREST)   # resizing the smaller image to the original size
                    pixelated.save(img_byte_arr, format='PNG')  # Save with low quality to pixelate
                    img_byte_arr.seek(0)
                    file = discord.File(img_byte_arr, filename="unscrambled_pokemon.png")
        
        # Store the current Pokemon being guessed
        active_pokemon_guesses[interaction.channel_id] = {
            'pokemon_name': name.lower(),  # Store original lowercase name for checking
            'active': True,
            'guesses': 0  # Initialize guess counter
        }
        
        if file:
            embed.set_image(url="attachment://unscrambled_pokemon.png")
            await interaction.followup.send(file=file, embed=embed)
        else:
            await interaction.followup.send(embed=embed)

# Play a random minigame
async def play_random_minigame(interaction: discord.Interaction, pokemon_id: int):
    """Play a random minigame."""
    # Select a random minigame from the loaded minigames list
    if minigames:
        chosen_game = random.choice(minigames)
        await chosen_game['function'](interaction, pokemon_id)
    else:
        await interaction.followup.send("No minigames are currently available.")

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

def load_minigames():
    """Load available minigames into the global minigames list."""
    global minigames
    
    minigames = [
        {
            "type": "guess_pokemon",
            "name": "Who's that Pokémon?",
            "description": "Guess the Pokémon based on a silhouette.",
            "function": who_is_that_pokemon
        },
        {
            "type": "unscramble_pokemon",
            "name": "Unscramble the Pokémon",
            "description": "Unscramble the letters to guess the Pokémon name.",
            "function": unscramble_pokemon
        },
        {
            "type": "guess_pokemon_visible",
            "name": "Who's that Pokémon? (Visible)",
            "description": "Guess the Pokémon by seeing its full sprite.",
            "function": who_is_that_pokemon_visible
        }
    ]
    
    print(f"Loaded {len(minigames)} minigames")

# Load minigames when module is imported
load_minigames()
