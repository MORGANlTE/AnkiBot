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
        name=":thinking: This is still a work in progress",
        value=":)",
        inline=True,
    )
    embed.add_field(
        name="** **",
        value=f"*v{os.getenv("VERSION")}*",
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