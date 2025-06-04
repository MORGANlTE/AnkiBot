import discord
from discord import app_commands 
from data.contributers import contributers

async def credits_command(interaction: discord.Interaction): # Added type hint
    await interaction.response.defer()
    embed = discord.Embed(
        title="Credits",
        color=discord.Color.teal()
    )

    embed.add_field(
        name="Contributors",
        value=", ".join(contributers),
        inline=False,
    )

    embed.set_thumbnail(
        url="https://i.ibb.co/GvXCXvcy/logo.png"
    )

    await interaction.followup.send(embed=embed)


def setup(tree: app_commands.CommandTree): # Added type hint
    tree.command(
        name="credits",
        description="Look at the credits of the bot",
    )(credits_command)