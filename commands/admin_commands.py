import discord
from discord import app_commands
from discord.app_commands import default_permissions
from typing import Optional, List
from data.profiles import award_badge, award_badges_to_users, get_badge_details, get_all_badges
from data.badges import get_badge_id
from data.database import db

# Guild ID where badge admin commands will be available
ADMIN_GUILD_ID = discord.Object(id=945414516391424040)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.command(name="award_badge", description="Award a badge to a user (Admin only)")
@app_commands.describe(
    user="The user to award the badge to",
    badge_name="The badge to award",
    reason="The reason for awarding the badge (will be shown on their profile)"
)
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

def setup(tree: app_commands.CommandTree):
    admin_perms = discord.Permissions(administrator=True)
    
    # For global commands
    config_main_group = app_commands.Group(
        name="config",
        description="Configuration commands.",
        default_permissions=admin_perms,
    )
    
    # Create badges subgroup for global commands
    config_badges_subgroup = app_commands.Group(
        name="badges",
        description="Admin commands for badge management.",
        default_permissions=admin_perms,
        parent=config_main_group
    )
    
    # Add the award_badge command to the global group
    config_badges_subgroup.add_command(award_badge_command)
    
    # Add guild-specific commands (only in ADMIN_GUILD_ID)
    tree.add_command(badge_add_command, guild=ADMIN_GUILD_ID)
    tree.add_command(badge_list_command, guild=ADMIN_GUILD_ID)
    
    # Check if the main config group is already added in event_commands.py
    try:
        # If it throws an error, it doesn't exist yet
        tree.get_command("config")
    except:
        # Add it if it doesn't exist
        tree.add_command(config_main_group)
