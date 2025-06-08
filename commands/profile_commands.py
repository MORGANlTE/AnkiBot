import discord
from discord import app_commands
import datetime
from data.profiles import get_user_profile, get_user_badges, has_badge, check_special_badges, get_user_badge_names
from data.badges import get_badge_id
from typing import Optional

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def profile_command(interaction: discord.Interaction, user: Optional[discord.User] = None):
    """View your profile or someone else's profile."""
    # Determine which user's profile to show
    target_user = user or interaction.user
    
    # For the user's own profile, check for special badges first
    if target_user.id == interaction.user.id:
        check_special_badges(target_user.id)
    
    # Get the user's badges
    badges = get_user_badges(target_user.id)
    badge_names = get_user_badge_names(target_user.id)
    
    # Create the embed
    embed = discord.Embed(
        title=f"{target_user.display_name}'s Profile",
        color=discord.Color.blurple()
    )
    
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # List of available badge names (without _locked suffix)
    available_badges = [
        "clefabadge", "eeveebadge", "enteibadge", "flamebadge", 
        "jirachibadge", "leafbadge", "lugiabadge", "mewtwobadge",
        "regicebadge", "registeelbadge", "snorlaxbadge", "staryubadge",
        "stonebadge", "waterbadge"
    ]
    
    # Add badges section
    badge_display = []
    
    for badge_name in available_badges:
        # Determine if user has the badge
        if badge_name in badge_names:
            # User has badge - get the unlocked emoji ID
            badge_id = get_badge_id(badge_name)
            if badge_id != -1:
                # Make sure the emoji name is lowercase and follows Discord's format
                emoji_str = f"<:{badge_name}:{badge_id}>"
                badge_display.append((badge_name, emoji_str, True))
        # else:
        #     # User doesn't have badge - get the locked emoji ID
        #     locked_badge_name = f"{badge_name}_locked"
        #     locked_badge_id = get_badge_id(locked_badge_name)
        #     if locked_badge_id != -1:
        #         # Make sure the emoji name is lowercase and follows Discord's format
        #         emoji_str = f"<:{locked_badge_name}:{locked_badge_id}>"
        #         badge_display.append((badge_name, emoji_str, False))
    
    # Format badges into rows of 8
    badge_rows = []
    for i in range(0, len(badge_display), 8):
        badge_row = badge_display[i:i+8]
        badge_icons = " ".join([badge[1] for badge in badge_row])
        badge_rows.append(badge_icons)
    
    if badge_rows:
        embed.add_field(
            name="Badges",
            value="\n".join(badge_rows),
            inline=False
        )
    else:
        embed.add_field(
            name="Badges",
            value="No badges to display.",
            inline=False
        )
    
    # Add badge details section for unlocked badges
    unlocked_badges = [b for b in badge_display if b[2]]
    if unlocked_badges:
        badge_details = []
        for badge_name, _, _ in unlocked_badges:
            # Find the badge details
            for badge in badges:
                if badge["name"] == badge_name:
                    badge_id = get_badge_id(badge_name)
                    badge_details.append(f"<:{badge_name}:{badge_id}> • {badge.get('acquired_from', 'Unknown')}")
                    break
        
        if badge_details:
            embed.add_field(
                name="Badge Details",
                value="\n".join(badge_details),
                inline=False
            )
    
    # Send the profile
    await interaction.response.send_message(embed=embed)

def setup(tree: app_commands.CommandTree):
    tree.command(
        name="profile",
        description="View your profile or someone else's profile"
    )(profile_command)
