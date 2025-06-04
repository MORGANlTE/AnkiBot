from discord import app_commands
import os
import discord

async def help_command(interaction):
    embed = discord.Embed(
        title="Commands",
        description="Available commands:",
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="Informational",
        value="** **",
        inline=False,
    )
    embed.add_field(
        name=":thinking: /quote",
        value="Random quote",
        inline=True,
    )
    embed.add_field(
        name="** **",
        value=f"*v{os.getenv("VERSION")}*",
        inline=False,
    )
    embed.set_footer(
        text="Made by _morganite",
        icon_url="https://iili.io/JlxAR7R.png",
    )

    await interaction.response.send_message(embed=embed)

def setup(tree):
    tree.command(
        name="help",
        description="Help with the commands",
    )(help_command)