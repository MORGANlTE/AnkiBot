import discord

# Dictionary to store active Pokemon guessing games, keyed by channel ID
active_pokemon_guesses = {}

async def evaluate_guess(msg_content: str, pkmn_name: str, channel: discord.channel.TextChannel, author: discord.User):
  """
  Evaluates a guess made by a user in the Pokémon guessing game."""
  # we check if the first character is the same as the first character of the pokemon name
  if not msg_content.lower().startswith(pkmn_name[0].lower()):
      return
  # Check if the message content matches the Pokemon name (case insensitive)
  if msg_content.lower() == pkmn_name.lower():
      # replace the msg_content.lower() with only the a-z characters
      import re
      message_content_cleaned = re.sub(r'[^a-z]', '', msg_content.lower())
      pokemon_name_cleaned = re.sub(r'[^a-z]', '', pkmn_name.lower())
      if message_content_cleaned != pokemon_name_cleaned:
          # If the cleaned content doesn't match, ignore the guess
          return

      pokemon_name = pkmn_name.capitalize()
      await channel.send(f"Congratulations {author.mention}! You correctly guessed the Pokémon: **{pokemon_name}**!")
      
      # Deactivate the guessing game
      active_pokemon_guesses[channel.id]['active'] = False