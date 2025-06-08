from discord import app_commands
import os
import discord

async def help_command(interaction):
    embed = discord.Embed(
        title="Commands",
        description="Available commands:",
        color=discord.Color.teal(),
    )
    embed.set_thumbnail(
        url="https://i.ibb.co/GvXCXvcy/logo.png",
    )
    embed.add_field(
        name="Informational",
        value="** **",
        inline=False,
    )
    embed.add_field(
        name="/profile",
        value="View your profile with earned badges",
        inline=True,
    )
    embed.add_field(
        name="/event list",
        value="List active events with badge rewards",
        inline=True,
    )
    embed.add_field(
        name="/event info [event]",
        value="View event details and requirements",
        inline=True,
    )
    embed.add_field(
        name="/event enter [event]",
        value="Submit your entry for an event to earn badges",
        inline=True,
    )
    embed.add_field(
        name="/pokemon info [name]",
        value="Get detailed info about a Pokémon",
        inline=True,
    )
    embed.add_field(
        name="** **",
        value=f"*v{os.getenv('VERSION')}*",
        inline=False,
    )
    embed.set_footer(
        text="Made by the volunteers of the AnkiMon project",
    )

    await interaction.response.send_message(embed=embed)

def setup(tree):
    tree.command(
        name="help",
        description="Help with the commands",
    )(help_command)