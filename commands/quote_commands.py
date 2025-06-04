import discord
from discord import app_commands
import aiohttp # handle HTTP requests asynchronously

async def random_quote_command(interaction: discord.Interaction): # Added type hint
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        # get the quote
        quote_url = "https://zenquotes.io/api/random"
        async with session.get(quote_url) as response:
            if response.status != 200:
                await interaction.followup.send("Sorry, I couldn't fetch a quote right now.")
                return
            data = await response.json()
            quote = data[0]['q']
            author = data[0]['a']

        # get a random image for the thumbnail
        image_url = "https://picsum.photos/300/200"
        # We don't need to fetch the image data, just its final URL after redirects
        # aiohttp handles redirects by default.
        # For picsum, the direct URL is what we need.
        
        embed = quote_embed(quote, author, image_url) # Pass the direct URL

    await interaction.followup.send(embed=embed)

def quote_embed(quote, author, thumbnail_url): # Renamed thumbnail to thumbnail_url for clarity
    embed = discord.Embed(
        color=discord.Color.teal(),
    )
    embed.add_field(name=author, value=quote, inline=False)
    embed.set_thumbnail(url=thumbnail_url) # Use thumbnail_url
    return embed

def setup(tree: app_commands.CommandTree): # Added type hint
    tree.command(
        name="quote",
        description="Get a quote",
    )(random_quote_command)