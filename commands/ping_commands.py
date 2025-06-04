from discord import app_commands

async def ping_command(interaction):
    await interaction.response.send_message(f"Pong! {round(interaction.client.latency * 1000)}ms", ephemeral=True)

# Register the command
def setup(tree):
    tree.add_command(app_commands.Command(name="ping", description="Ping the bot", callback=ping_command))