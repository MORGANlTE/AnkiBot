import discord
from discord import app_commands
import aiohttp
import asyncio
from typing import Optional

# Dictionary to store active trades
# Structure:
# {
#   "trade_id": {
#     "initiator": {"user_id": user_id, "pokemon_code": code, "pokemon_level": level, "confirmed": bool, "message": message},
#     "recipient": {"user_id": user_id, "pokemon_code": code, "pokemon_level": level, "confirmed": bool, "message": message}
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

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    pokemon_code="Your Pokemon code (comma-separated numbers)",
    user="The user you want to trade with",
    user_id="The user ID you want to trade with (alternative to mentioning a user)"
)
async def trade_command(interaction: discord.Interaction, pokemon_code: str, 
                        user: Optional[discord.User] = None, 
                        user_id: Optional[str] = None):
    # Figure out which user to trade with based on provided parameters
    target_user = user
    
    # If user wasn't provided but user_id was, try to fetch the user
    if target_user is None and user_id is not None:
        try:
            # Try to convert the string to an integer (user ID)
            user_id_int = int(user_id.strip())
            try:
                # Try to fetch the user
                target_user = await interaction.client.fetch_user(user_id_int)
            except (discord.NotFound, discord.HTTPException):
                await interaction.response.send_message(f"I couldn't find a user with ID: {user_id}. Please check the ID and try again.", ephemeral=True)
                return
        except ValueError:
            # If the string isn't a valid integer
            await interaction.response.send_message("Please provide a valid user ID (numbers only).", ephemeral=True)
            return
    
    # Handle case where neither user nor user_id was provided
    if target_user is None:
        await interaction.response.send_message("Please specify a user to trade with, either by mentioning them or providing their user ID.", ephemeral=True)
        return
    
    # Check if trading with self
    if target_user.id == interaction.user.id:
        await interaction.response.send_message("You can't trade with yourself!", ephemeral=True)
        return
    
    # Check if the user is a bot
    if target_user.bot:
        await interaction.response.send_message("You can't trade with a bot!", ephemeral=True)
        return
    
    # Validate the Pokemon code format
    try:
        code_parts = [int(part.strip()) for part in pokemon_code.split(',')]
        if len(code_parts) < 1:
            await interaction.response.send_message("Invalid Pokemon code format. Please provide a comma-separated list of numbers.", ephemeral=True)
            return
        
        pokemon_id = code_parts[0]
        pokemon_level = code_parts[1] if len(code_parts) > 1 else 0
    except ValueError:
        await interaction.response.send_message("Invalid Pokemon code format. Please provide comma-separated numbers only.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Generate a trade ID
    trade_id = generate_trade_id(interaction.user.id, target_user.id)
    
    # Check if there's already an active trade between these users
    if trade_id in active_trades:
        # If the recipient is initiating a trade, handle it as a trade response
        existing_trade = active_trades[trade_id]
        
        if existing_trade["initiator"]["user_id"] == target_user.id and existing_trade["recipient"]["user_id"] == interaction.user.id:
            # The recipient is responding to an existing trade
            existing_trade["recipient"]["pokemon_code"] = pokemon_code
            existing_trade["recipient"]["pokemon_level"] = pokemon_level
            
            # Update the trade message with both Pokemon
            await update_trade_messages(interaction, trade_id)
            
            await interaction.followup.send("You've added your Pokemon to the trade. Please check the trade message to confirm.", ephemeral=True)
            return
        else:
            # There's already a trade between these users but in a different direction
            await interaction.followup.send(f"There's already an active trade with {target_user.display_name}. Please complete that trade first.", ephemeral=True)
            return
    
    # Create a new trade
    active_trades[trade_id] = {
        "initiator": {
            "user_id": interaction.user.id,
            "pokemon_code": pokemon_code,
            "pokemon_level": pokemon_level,
            "confirmed": False,
            "message": None
        },
        "recipient": {
            "user_id": target_user.id,
            "pokemon_code": None,
            "pokemon_level": None,
            "confirmed": False,
            "message": None
        }
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
        description=f"{interaction.user.mention} wants to trade with {target_user.mention}!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name=f"{interaction.user.display_name}'s Pokemon",
        value=f"{pokemon_name} (Level {pokemon_level})",
        inline=True
    )
    
    embed.add_field(
        name=f"{target_user.display_name}'s Pokemon",
        value="Waiting for response...",
        inline=True
    )
    
    if pokemon_sprite:
        embed.set_thumbnail(url=pokemon_sprite)

    
    # Create action buttons
    view = TradeView(trade_id)
    
    # Send the trade message to both users
    await interaction.followup.send("Trade request sent!", ephemeral=True)
    
    # Check if we're in a DM channel or guild channel
    is_dm = isinstance(interaction.channel, discord.DMChannel)
    
    # Send message differently based on channel type
    try:
        if is_dm:
            # In DMs, send directly to the user
            initiator_msg = await interaction.user.send(
                content=f"Trade with {target_user.display_name} (ID: {target_user.id})",
                embed=embed,
                view=view
            )
        else:
            # In guild channels, send to the channel
            initiator_msg = await interaction.channel.send(
                content=f"Trade with {target_user.display_name}",
                embed=embed,
                view=view
            )
        
        active_trades[trade_id]["initiator"]["message"] = initiator_msg
    except discord.Forbidden:
        # Handle case where we can't send the message
        await interaction.followup.send("I couldn't send a message with the trade details. Please check your privacy settings.", ephemeral=True)
        del active_trades[trade_id]
        return
    except Exception as e:
        # Handle any other exceptions
        print(f"Error sending trade message: {e}")
        await interaction.followup.send("An error occurred while setting up the trade. Please try again later.", ephemeral=True)
        del active_trades[trade_id]
        return
    
    # Try to send to recipient in DM
    try:
        recipient_msg = await target_user.send(
            content=f"{interaction.user.display_name} (ID: {interaction.user.id}) wants to trade with you! Use `/trade pokemon_code:[your-pokemon-code] user_id:{interaction.user.id}` to respond.",
            embed=embed,
            view=view
        )
        active_trades[trade_id]["recipient"]["message"] = recipient_msg
    except discord.Forbidden:
        # If we can't DM, try to notify in the same channel if it's not a DM
        if not is_dm and hasattr(interaction.channel, 'send'):
            try:
                await interaction.channel.send(
                    content=f"{target_user.mention}, {interaction.user.display_name} wants to trade with you! Use `/trade pokemon_code:[your-pokemon-code] user_id:{interaction.user.id}` to respond.",
                    embed=None
                )
            except Exception:
                pass
    except Exception as e:
        # Handle any other exceptions
        print(f"Error sending trade message to recipient: {e}")

async def update_trade_messages(interaction: discord.Interaction, trade_id: str):
    """Update the trade messages for both users."""
    trade_info = active_trades.get(trade_id)
    if not trade_info:
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
        initiator_pokemon_level = trade_info["initiator"]["pokemon_level"]
        
        embed.add_field(
            name=f"{initiator.display_name}'s Pokemon",
            value=f"{initiator_pokemon_name} (Level {initiator_pokemon_level})" + (" ✅" if trade_info["initiator"]["confirmed"] else ""),
            inline=True
        )
        
        if not recipient_pokemon_data and initiator_pokemon_sprite:
            embed.set_thumbnail(url=initiator_pokemon_sprite)
    
    # Add recipient's Pokemon if available
    if recipient_pokemon_data:
        recipient_pokemon_name = recipient_pokemon_data['name'].capitalize()
        recipient_pokemon_sprite = recipient_pokemon_data['sprites']['front_default']
        recipient_pokemon_level = trade_info["recipient"]["pokemon_level"]
        
        embed.add_field(
            name=f"{recipient.display_name}'s Pokemon",
            value=f"{recipient_pokemon_name} (Level {recipient_pokemon_level})" + (" ✅" if trade_info["recipient"]["confirmed"] else ""),
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
    
    # Update messages for both users
    view = TradeView(trade_id)
    
    # Update initiator's message if exists
    initiator_message = trade_info["initiator"]["message"]
    if initiator_message:
        try:
            await initiator_message.edit(embed=embed, view=view)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass  # Handle various Discord API errors
    
    # Update recipient's message if exists
    recipient_message = trade_info["recipient"]["message"]
    if recipient_message:
        try:
            await recipient_message.edit(embed=embed, view=view)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass  # Handle various Discord API errors

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
        
        # Update the trade messages
        await update_trade_messages(interaction, self.trade_id)
        
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
        
        # Update the messages
        initiator_message = trade_info["initiator"]["message"]
        recipient_message = trade_info["recipient"]["message"]
        
        cancel_message = "This trade has been cancelled."
        
        if initiator_message:
            try:
                await initiator_message.edit(content=cancel_message, embed=None, view=None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # Handle various Discord API errors
                
        if recipient_message:
            try:
                await recipient_message.edit(content=cancel_message, embed=None, view=None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # Handle various Discord API errors
        
        # Remove from active trades
        del active_trades[self.trade_id]
        
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
    
    # Update the trade messages
    complete_message = f"Trade completed between {initiator.mention} and {recipient.mention}!"
    
    initiator_message = trade_info["initiator"]["message"]
    recipient_message = trade_info["recipient"]["message"]
    
    if initiator_message:
        try:
            await initiator_message.edit(content=complete_message, view=None)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass  # Handle various Discord API errors
            
    if recipient_message:
        try:
            await recipient_message.edit(content=complete_message, view=None)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass  # Handle various Discord API errors
    
    # Remove the trade from active trades
    del active_trades[trade_id]

def setup(tree: app_commands.CommandTree):
    tree.command(name="trade", description="Trade Pokémon with another user")(trade_command)
