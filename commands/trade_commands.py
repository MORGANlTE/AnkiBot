import discord
from discord import app_commands
import aiohttp
import asyncio
from typing import Dict, List, Optional

# Dictionary to store active trades
# Structure:
# {
#   "trade_id": {
#     "initiator": {"user_id": user_id, "pokemon_code": code, "confirmed": bool},
#     "recipient": {"user_id": user_id, "pokemon_code": code, "confirmed": bool},
#     "message_id": message_id,
#     "channel_id": channel_id
#   }
# }
active_trades = {}

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/"

async def fetch_pokemon_data(session: aiohttp.ClientSession, pokemon_id: int):
    """Fetch Pokemon data from PokeAPI."""
    try:
        async with session.get(f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}") as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except Exception as e:
        print(f"Error fetching Pokemon data: {e}")
        return None

def generate_trade_id(user1_id: int, user2_id: int) -> str:
    """Generate a unique trade ID based on the users involved."""
    return f"{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"

@app_commands.describe(
    pokemon_code="Your Pokemon code (comma-separated numbers)",
    user="The user you want to trade with"
)
async def trade_command(interaction: discord.Interaction, pokemon_code: str, user: discord.User):
    # Check if trading with self
    if user.id == interaction.user.id:
        await interaction.response.send_message("You can't trade with yourself!", ephemeral=True)
        return
    
    # Check if the user is a bot
    if user.bot:
        await interaction.response.send_message("You can't trade with a bot!", ephemeral=True)
        return
    
    # Validate the Pokemon code format
    try:
        code_parts = [int(part.strip()) for part in pokemon_code.split(',')]
        if len(code_parts) < 1:
            await interaction.response.send_message("Invalid Pokemon code format. Please provide a comma-separated list of numbers.", ephemeral=True)
            return
        
        pokemon_id = code_parts[0]
    except ValueError:
        await interaction.response.send_message("Invalid Pokemon code format. Please provide comma-separated numbers only.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Generate a trade ID
    trade_id = generate_trade_id(interaction.user.id, user.id)
    
    # Check if there's already an active trade between these users
    if trade_id in active_trades:
        # If the recipient is initiating a trade, handle it as a trade response
        existing_trade = active_trades[trade_id]
        
        if existing_trade["initiator"]["user_id"] == user.id and existing_trade["recipient"]["user_id"] == interaction.user.id:
            # The recipient is responding to an existing trade
            existing_trade["recipient"]["pokemon_code"] = pokemon_code
            
            # Update the trade message with both Pokemon
            await update_trade_message(interaction, trade_id)
            
            await interaction.followup.send("You've added your Pokemon to the trade. Please check the channel to confirm.", ephemeral=True)
            return
        else:
            # There's already a trade between these users but in a different direction
            await interaction.followup.send(f"There's already an active trade with {user.display_name}. Please complete that trade first.", ephemeral=True)
            return
    
    # Create a new trade
    active_trades[trade_id] = {
        "initiator": {
            "user_id": interaction.user.id,
            "pokemon_code": pokemon_code,
            "confirmed": False
        },
        "recipient": {
            "user_id": user.id,
            "pokemon_code": None,
            "confirmed": False
        },
        "message_id": None,
        "channel_id": interaction.channel_id
    }
    
    # Fetch Pokemon data to display
    async with aiohttp.ClientSession() as session:
        pokemon_data = await fetch_pokemon_data(session, pokemon_id)
        
        if not pokemon_data:
            await interaction.followup.send("Could not fetch Pokemon data. Please try again later.", ephemeral=True)
            del active_trades[trade_id]
            return
        
        pokemon_name = pokemon_data['name'].capitalize()
        pokemon_sprite = pokemon_data['sprites']['front_default']
    
    # Create the initial trade message
    embed = discord.Embed(
        title="Pokemon Trade Request",
        description=f"{interaction.user.mention} wants to trade with {user.mention}!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name=f"{interaction.user.display_name}'s Pokemon",
        value=f"{pokemon_name}",
        inline=True
    )
    
    embed.add_field(
        name=f"{user.display_name}'s Pokemon",
        value="Waiting for response...",
        inline=True
    )
    
    if pokemon_sprite:
        embed.set_thumbnail(url=pokemon_sprite)
    
    # Create action buttons
    view = TradeView(trade_id)
    
    # Send the trade message to the channel
    await interaction.followup.send("Trade request sent!", ephemeral=True)
    trade_message = await interaction.channel.send(
        content=f"{user.mention}, {interaction.user.display_name} wants to trade with you! Use `/trade` to respond.",
        embed=embed,
        view=view
    )
    
    # Store the message ID for later updates
    active_trades[trade_id]["message_id"] = trade_message.id

async def update_trade_message(interaction: discord.Interaction, trade_id: str):
    """Update the trade message with current information."""
    trade_info = active_trades.get(trade_id)
    if not trade_info:
        return
    
    # Get the channel and message
    channel = interaction.client.get_channel(trade_info["channel_id"])
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(trade_info["message_id"])
    except discord.NotFound:
        return
    
    # Get user objects
    initiator = await interaction.client.fetch_user(trade_info["initiator"]["user_id"])
    recipient = await interaction.client.fetch_user(trade_info["recipient"]["user_id"])
    
    # Fetch Pokemon data for both users
    async with aiohttp.ClientSession() as session:
        initiator_pokemon_id = int(trade_info["initiator"]["pokemon_code"].split(',')[0].strip())
        initiator_pokemon_data = await fetch_pokemon_data(session, initiator_pokemon_id)
        
        recipient_pokemon_data = None
        if trade_info["recipient"]["pokemon_code"]:
            recipient_pokemon_id = int(trade_info["recipient"]["pokemon_code"].split(',')[0].strip())
            recipient_pokemon_data = await fetch_pokemon_data(session, recipient_pokemon_id)
    
    # Create the updated embed
    embed = discord.Embed(
        title="Pokemon Trade",
        description=f"Trade between {initiator.mention} and {recipient.mention}",
        color=discord.Color.blue()
    )
    
    # Add initiator's Pokemon
    if initiator_pokemon_data:
        initiator_pokemon_name = initiator_pokemon_data['name'].capitalize()
        initiator_pokemon_sprite = initiator_pokemon_data['sprites']['front_default']
        
        embed.add_field(
            name=f"{initiator.display_name}'s Pokemon",
            value=f"{initiator_pokemon_name}" + (" ✅" if trade_info["initiator"]["confirmed"] else ""),
            inline=True
        )
        
        if not recipient_pokemon_data and initiator_pokemon_sprite:
            embed.set_thumbnail(url=initiator_pokemon_sprite)
    
    # Add recipient's Pokemon if available
    if recipient_pokemon_data:
        recipient_pokemon_name = recipient_pokemon_data['name'].capitalize()
        recipient_pokemon_sprite = recipient_pokemon_data['sprites']['front_default']
        
        embed.add_field(
            name=f"{recipient.display_name}'s Pokemon",
            value=f"{recipient_pokemon_name}" + (" ✅" if trade_info["recipient"]["confirmed"] else ""),
            inline=True
        )
        
        # If both Pokemon are available, show both sprites
        if recipient_pokemon_sprite:
            embed.set_image(url=recipient_pokemon_sprite)
            if initiator_pokemon_sprite:
                embed.set_thumbnail(url=initiator_pokemon_sprite)
    else:
        embed.add_field(
            name=f"{recipient.display_name}'s Pokemon",
            value="Waiting for response...",
            inline=True
        )
    
    # Update the message
    view = TradeView(trade_id)
    await message.edit(embed=embed, view=view)

class TradeView(discord.ui.View):
    def __init__(self, trade_id: str):
        super().__init__(timeout=600)  # 10-minute timeout
        self.trade_id = trade_id
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        trade_info = active_trades.get(self.trade_id)
        if not trade_info:
            await interaction.response.send_message("This trade is no longer active.", ephemeral=True)
            return
        
        # Check if the user is part of this trade
        user_id = interaction.user.id
        user_role = None
        
        if trade_info["initiator"]["user_id"] == user_id:
            user_role = "initiator"
        elif trade_info["recipient"]["user_id"] == user_id:
            user_role = "recipient"
        
        if not user_role:
            await interaction.response.send_message("You are not part of this trade.", ephemeral=True)
            return
        
        # Check if the user has provided their Pokemon code
        if user_role == "recipient" and not trade_info["recipient"]["pokemon_code"]:
            await interaction.response.send_message("Please use `/trade` to add your Pokemon first.", ephemeral=True)
            return
        
        # Mark as confirmed
        trade_info[user_role]["confirmed"] = True
        
        await interaction.response.send_message("You have confirmed the trade.", ephemeral=True)
        
        # Update the trade message
        await update_trade_message(interaction, self.trade_id)
        
        # Check if both users have confirmed
        if trade_info["initiator"]["confirmed"] and trade_info["recipient"]["confirmed"]:
            # Complete the trade
            await complete_trade(interaction, self.trade_id)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        trade_info = active_trades.get(self.trade_id)
        if not trade_info:
            await interaction.response.send_message("This trade is no longer active.", ephemeral=True)
            return
        
        # Check if the user is part of this trade
        user_id = interaction.user.id
        if trade_info["initiator"]["user_id"] != user_id and trade_info["recipient"]["user_id"] != user_id:
            await interaction.response.send_message("You are not part of this trade.", ephemeral=True)
            return
        
        # Cancel the trade
        del active_trades[self.trade_id]
        
        # Update the message
        channel = interaction.client.get_channel(trade_info["channel_id"])
        if channel:
            try:
                message = await channel.fetch_message(trade_info["message_id"])
                await message.edit(content="This trade has been cancelled.", embed=None, view=None)
            except discord.NotFound:
                pass
        
        await interaction.response.send_message("You have cancelled the trade.", ephemeral=True)

async def complete_trade(interaction: discord.Interaction, trade_id: str):
    """Complete a trade after both users have confirmed."""
    trade_info = active_trades.get(trade_id)
    if not trade_info:
        return
    
    # Get user objects
    initiator = await interaction.client.fetch_user(trade_info["initiator"]["user_id"])
    recipient = await interaction.client.fetch_user(trade_info["recipient"]["user_id"])
    
    # Send DMs with the Pokemon codes
    initiator_pokemon_code = trade_info["initiator"]["pokemon_code"]
    recipient_pokemon_code = trade_info["recipient"]["pokemon_code"]
    
    # DM to initiator
    try:
        await initiator.send(f"Trade completed! You received this Pokemon code from {recipient.display_name}:\n```{recipient_pokemon_code}```")
    except discord.Forbidden:
        pass  # Can't send DM to initiator
    
    # DM to recipient
    try:
        await recipient.send(f"Trade completed! You received this Pokemon code from {initiator.display_name}:\n```{initiator_pokemon_code}```")
    except discord.Forbidden:
        pass  # Can't send DM to recipient
    
    # Update the trade message
    channel = interaction.client.get_channel(trade_info["channel_id"])
    if channel:
        try:
            message = await channel.fetch_message(trade_info["message_id"])
            await message.edit(
                content=f"Trade completed between {initiator.mention} and {recipient.mention}!",
                view=None
            )
        except discord.NotFound:
            pass
    
    # Remove the trade from active trades
    del active_trades[trade_id]

def setup(tree: app_commands.CommandTree):
    tree.command(name="trade", description="Trade Pokemon with another user")(trade_command)
