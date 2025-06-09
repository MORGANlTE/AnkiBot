import discord
from discord import app_commands
from discord.app_commands import default_permissions
import json
import datetime
from typing import Optional, List
from data.profiles import award_badge, award_badges_to_users, get_badge_details, get_all_badges
from data.badges import get_badge_id
from data.database import db
from data.events import (
    create_event, delete_event, get_event, event_name_autocomplete, 
    set_pokemon_list, set_badge_reward, end_event
)
import os

# Event type choices
EVENT_TYPE_CHOICES = [
    app_commands.Choice(name="Catch Event", value="catch")
]

# Badge autocomplete function
async def badge_name_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete function for badge names."""
    badges = get_all_badges()
    
    return [
        discord.app_commands.Choice(name=badge["name"], value=badge["name"])
        for badge in badges 
        if current.lower() in badge["name"].lower()
    ][:25]  # Discord limits to 25 choices

# --- BADGE COMMANDS ---
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.command(name="award_badge", description="Award a badge to a user (Admin only)")
@app_commands.describe(
    user="The user to award the badge to",
    badge_name="The badge to award",
    reason="The reason for awarding the badge (will be shown on their profile)"
)
@app_commands.autocomplete(badge_name=badge_name_autocomplete)
async def award_badge_command(
    interaction: discord.Interaction, 
    user: discord.User,
    badge_name: str,
    reason: Optional[str] = None
):
    await interaction.response.defer(ephemeral=True)
    
    # Validate the badge
    badge_id = get_badge_id(badge_name)
    if badge_id == -1:
        await interaction.followup.send(f"Invalid badge name: {badge_name}", ephemeral=True)
        return
    
    # Set acquisition reason
    if not reason:
        reason = f"Awarded by {interaction.user.display_name}"
    
    # Award the badge
    success = award_badge(user.id, badge_name, reason)
    
    if success:
        # Format the emoji correctly
        emoji_str = f"<:{badge_name}:{badge_id}>"
        
        embed = discord.Embed(
            title="Badge Awarded",
            description=f"Successfully awarded {badge_name} to {user.mention}",
            color=discord.Color.green()
        )
        
        # Add badge details
        embed.add_field(
            name="Badge",
            value=f"{emoji_str} ({badge_name})",
            inline=True
        )
        
        embed.add_field(
            name="Reason",
            value=reason,
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"User already has the {badge_name} badge.", ephemeral=True)

# New command to add a badge to the database
@app_commands.command(name="badge_add", description="Add or update a badge in the database (Admin only)")
@app_commands.describe(
    badge_name="The name of the badge (e.g., 'leafbadge')",
    emoji_id="The Discord emoji ID for the unlocked badge",
    locked_emoji_id="The Discord emoji ID for the locked version (optional)",
    description="Description of the badge (optional)"
)
async def badge_add_command(
    interaction: discord.Interaction,
    badge_name: str,
    emoji_id: str,
    locked_emoji_id: Optional[str] = None,
    description: Optional[str] = None
):
    await interaction.response.defer(ephemeral=True)
    
    # Validate emoji IDs are numbers
    try:
        emoji_id_int = int(emoji_id)
        locked_emoji_id_int = int(locked_emoji_id) if locked_emoji_id else -1
    except ValueError:
        await interaction.followup.send("Emoji IDs must be numeric values.", ephemeral=True)
        return
    
    # Set default description if not provided
    if not description:
        description = f"The {badge_name} badge"
    
    # Check if badge already exists
    existing_badge = get_badge_details(badge_name)
    
    if existing_badge:
        # Update existing badge
        db.execute(
            """UPDATE badges 
               SET emoji_id = ?, locked_emoji_id = ?, description = ? 
               WHERE name = ?""",
            (emoji_id_int, locked_emoji_id_int, description, badge_name)
        )
        action = "updated"
    else:
        # Insert new badge
        db.execute(
            """INSERT INTO badges (name, emoji_id, locked_emoji_id, description) 
               VALUES (?, ?, ?, ?)""",
            (badge_name, emoji_id_int, locked_emoji_id_int, description)
        )
        action = "added"
    
    # Create response embed
    embed = discord.Embed(
        title=f"Badge {action.capitalize()}",
        description=f"Badge '{badge_name}' has been {action} to the database.",
        color=discord.Color.green()
    )
    
    # Format badge display
    badge_display = f"<:{badge_name}:{emoji_id_int}>"
    locked_badge_display = f"<:{badge_name}_locked:{locked_emoji_id_int}>" if locked_emoji_id_int != -1 else "None"
    
    embed.add_field(name="Badge Name", value=badge_name, inline=True)
    embed.add_field(name="Unlocked", value=badge_display, inline=True)
    embed.add_field(name="Locked", value=locked_badge_display, inline=True)
    embed.add_field(name="Description", value=description, inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@app_commands.command(name="badge_list", description="List all badges in the database (Admin only)")
async def badge_list_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Get all badges from the database
    badges = get_all_badges()
    
    if not badges:
        await interaction.followup.send("No badges found in the database.", ephemeral=True)
        return
    
    # Create an embed to display badges
    embed = discord.Embed(
        title="Available Badges",
        description=f"Total badges: {len(badges)}",
        color=discord.Color.blue()
    )
    
    # Add each badge to the embed
    for badge in badges:
        badge_name = badge["name"]
        emoji_id = badge["emoji_id"]
        locked_emoji_id = badge["locked_emoji_id"]
        
        badge_display = f"<:{badge_name}:{emoji_id}>"
        locked_display = f"<:{badge_name}_locked:{locked_emoji_id}>" if locked_emoji_id != -1 else "None"
        
        embed.add_field(
            name=badge_name,
            value=f"Unlocked: {badge_display}\nLocked: {locked_display}\nDescription: {badge['description']}",
            inline=True
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# --- EVENT COMMANDS ---
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.command(name="create", description="Create a new event (Admin only)")
@app_commands.describe(
    name="Name of the event",
    event_type="Type of event",
    start_date="Start date in YYYY-MM-DD format",
    end_date="End date in YYYY-MM-DD format",
    pokemon_list="Comma-separated list of Pokémon IDs to catch (for catch events)",
    badge_reward="Badge to award as a reward (leave empty for no badge)",
    required_completion="Percentage of completion required to earn the badge (1-100)"
)
@app_commands.choices(event_type=EVENT_TYPE_CHOICES)
@app_commands.autocomplete(badge_reward=badge_name_autocomplete)
async def event_create(
    interaction: discord.Interaction, 
    name: str, 
    event_type: str,
    start_date: str,
    end_date: str,
    pokemon_list: str,
    badge_reward: Optional[str] = None,
    required_completion: Optional[int] = 100
):
    await interaction.response.defer(ephemeral=True)
    
    # Create the event
    success, message = create_event(
        interaction.guild_id,
        name,
        event_type,
        start_date,
        end_date,
        interaction.user.id
    )
    
    if not success:
        await interaction.followup.send(f"Failed to create event: {message}", ephemeral=True)
        return
    
    # For catch events, process the Pokémon list
    if event_type == "catch":
        try:
            # Parse the Pokémon list from comma-separated string
            pokemon_ids = [int(p.strip()) for p in pokemon_list.split(',')]
            
            # Set the Pokémon list for the event
            if not set_pokemon_list(interaction.guild_id, name, pokemon_ids):
                await interaction.followup.send("Failed to set Pokémon list for the event.", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("Invalid Pokémon list format. Use comma-separated numbers.", ephemeral=True)
            delete_event(interaction.guild_id, name)  # Clean up the partially created event
            return
    
    # Set badge reward if provided
    if badge_reward:
        # Validate the badge name
        badge_id = get_badge_id(badge_reward)
        if badge_id == -1:
            await interaction.followup.send(f"Invalid badge name: {badge_reward}. The event was created but no badge reward was set.", ephemeral=True)
        else:
            # Validate completion percentage
            if required_completion < 1 or required_completion > 100:
                await interaction.followup.send("Required completion must be between 1 and 100. Using default value of 100%.", ephemeral=True)
                required_completion = 100
            
            # Set the badge reward
            if not set_badge_reward(interaction.guild_id, name, badge_reward, required_completion):
                await interaction.followup.send("Failed to set badge reward for the event.", ephemeral=True)
    
    await interaction.followup.send(f"Event '{name}' created successfully!", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.command(name="delete", description="Delete an existing event (Admin only)")
@app_commands.describe(
    event_name="The event to delete"
)
@app_commands.autocomplete(event_name=event_name_autocomplete)
async def event_delete(interaction: discord.Interaction, event_name: str):
    await interaction.response.defer(ephemeral=True)
    
    # Delete the event
    success = delete_event(interaction.guild_id, event_name)
    
    if not success:
        await interaction.followup.send(f"This event doesn't exist", ephemeral=True)
        return
    
    await interaction.followup.send(f"Event '{event_name}' deleted successfully!", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.command(name="end", description="End an event and distribute rewards (Admin only)")
@app_commands.describe(
    event_name="The event to end"
)
@app_commands.autocomplete(event_name=event_name_autocomplete)
async def event_end(interaction: discord.Interaction, event_name: str):
    await interaction.response.defer()
    
    # End the event and get results
    success, results = end_event(interaction.guild_id, event_name)
    
    if not success:
        error_message = results.get("error", "Unknown error")
        await interaction.followup.send(f"Failed to end event: {error_message}", ephemeral=True)
        return
    
    # Create results embed
    embed = discord.Embed(
        title=f"Event Ended: {results['name']}",
        description="The event has been completed and rewards have been distributed.",
        color=discord.Color.green()
    )
    
    # Add badge reward info if applicable
    if results.get("badge_awarded"):
        badge_name = results["badge_awarded"]
        badge_id = get_badge_id(badge_name)
        
        badge_display = f"<:{badge_name}:{badge_id}>" if badge_id != -1 else badge_name
        
        embed.add_field(
            name="Badge Reward",
            value=f"{badge_display} ({badge_name})",
            inline=False
        )
        
        embed.add_field(
            name="Required Completion",
            value=f"{results['required_completion']}%",
            inline=True
        )
        
        # Award badges to qualified users
        qualified_users = results.get("qualified_users", [])
        
        if qualified_users:
            # Include event name in the acquisition source
            acquisition_source = f"Completed {results['name']} event"
            award_results = award_badges_to_users(qualified_users, badge_name, acquisition_source)
            
            # Create a list of users who earned the badge
            badge_recipients = []
            for user_id in qualified_users:
                try:
                    user = await interaction.client.fetch_user(user_id)
                    badge_recipients.append(f"• {user.mention}")
                except discord.NotFound:
                    badge_recipients.append(f"• Unknown User ({user_id})")
            
            embed.add_field(
                name=f"Badge Recipients ({len(qualified_users)})",
                value="\n".join(badge_recipients) if badge_recipients and len(badge_recipients) < 20 else "Too many recipients to display.",
                inline=False
            )
        else:
            embed.add_field(
                name="Badge Recipients",
                value="No users qualified for the badge reward.",
                inline=False
            )
    
    await interaction.followup.send(embed=embed)

def setup(tree: app_commands.CommandTree):
    admin_perms = discord.Permissions(administrator=True)
    
    # Create main config group
    config_main_group = app_commands.Group(
        name="config",
        description="Configuration commands.",
        default_permissions=admin_perms,
    )
    
    # Create badges subgroup
    config_badges_subgroup = app_commands.Group(
        name="badges",
        description="Admin commands for badge management.",
        default_permissions=admin_perms,
        parent=config_main_group
    )
    
    # Create event subgroup
    config_event_subgroup = app_commands.Group(
        name="event",
        description="Admin commands for event configuration.",
        default_permissions=admin_perms,
        parent=config_main_group
    )
    
    # Add badge commands to badges subgroup
    config_badges_subgroup.add_command(award_badge_command)
    
    # Add event commands to event subgroup
    config_event_subgroup.add_command(event_create)
    config_event_subgroup.add_command(event_delete)
    config_event_subgroup.add_command(event_end)
    
    # Add guild-specific commands (only in ADMIN_GUILD_ID)
    ADMIN_GUILD_IDS = [discord.Object(id=guild_id) for guild_id in os.getenv("ADMIN_GUILD_IDS", "").split(", ")]
    print(f"Admin guild IDs: {ADMIN_GUILD_IDS}")
    tree.add_command(badge_add_command, guilds=ADMIN_GUILD_IDS)
    tree.add_command(badge_list_command, guilds=ADMIN_GUILD_IDS)
    
    # Add the config main group to the tree
    tree.add_command(config_main_group, guilds=ADMIN_GUILD_IDS)