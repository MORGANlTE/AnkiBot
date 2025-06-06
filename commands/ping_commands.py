from discord import app_commands
from discord.app_commands import default_permissions
from discord import app_commands
import discord


@app_commands.command(name="ping", description="Check the bot's latency")
@app_commands.default_permissions(administrator=True)
async def ping_command(interaction):
    await interaction.response.send_message(f"Pong! {round(interaction.client.latency * 1000)}ms", ephemeral=True)

# Register the command
def setup(tree):
    tree.add_command(ping_command)