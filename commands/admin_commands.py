import discord
from discord import app_commands
from discord.app_commands import default_permissions
from typing import Optional, List
from data.profiles import award_badge, award_badges_to_users
from data.badges import get_badge_id

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

def setup(tree: app_commands.CommandTree):
    admin_perms = discord.Permissions(administrator=True)
    
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
    
    config_badges_subgroup.add_command(award_badge_command)
    
    # Check if the main config group is already added in event_commands.py
    try:
        # If it throws an error, it doesn't exist yet
        tree.get_command("config")
    except:
        # Add it if it doesn't exist
        tree.add_command(config_main_group)
