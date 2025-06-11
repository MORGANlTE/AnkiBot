import discord
from discord import app_commands
import os
from dotenv import load_dotenv
from setup.setup import *
from commands import help_commands, ping_commands, quote_commands, pokemon_commands, credit_commands, trade_commands, tournament_commands, event_commands, profile_commands, admin_commands, ai_commands
from data.minigames import active_pokemon_guesses, evaluate_guess

# Load the .env file
load_dotenv()

# Variables:
sync_commands = True # Set to False to disable command syncing
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Need this to read message content

# Check the value of the ENVIRONMENT variable
guilds = setup_guilds()

# Functions:
has_synced = False
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Register command groups
help_commands.setup(tree)
ping_commands.setup(tree)
# experimenting with api requests from outside:
# quote_commands.setup(tree)
pokemon_commands.setup(tree)
credit_commands.setup(tree)
trade_commands.setup(tree)
event_commands.setup(tree) 
tournament_commands.setup(tree)
profile_commands.setup(tree)
admin_commands.setup(tree)  # Add the admin commands
ai_commands.setup(tree)  # Add the AI commands

@client.event
async def on_ready():
    global has_synced
    print("Finished setting up commands")
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    
    # Only sync commands once
    if not has_synced and sync_commands:
        await tree.sync()
        has_synced = True
        print("Currently supporting {} guilds".format(len(client.guilds)))

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user or message.author.bot:
        return
    
    # Check if there's an active Pokemon guessing game in this channel
    channel_id = message.channel.id
    if channel_id in active_pokemon_guesses and active_pokemon_guesses[channel_id]['active']:
        await evaluate_guess(message.content, active_pokemon_guesses[channel_id]['pokemon_name'], message.channel, message.author)

    # Get AI channels from environment variable
    ai_channels = os.getenv("AI_CHANNELS", "").split(",")
    if ai_channels and ai_channels[0]:  # Make sure it's not an empty string
        # Convert channel IDs to integers for comparison
        ai_channel_ids = [int(channel_id.strip()) for channel_id in ai_channels if channel_id.strip()]
        
        # If the message is in a designated AI channel, process it with the AI
        if channel_id in ai_channel_ids:
            author = message.author
            nickname = author.display_name

            await ai_commands.handle_ai_message(str(nickname + " user full name: " + str(author)), message)

client.run(os.getenv("TOKEN"))