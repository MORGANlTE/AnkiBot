import os
import discord

def setup_guilds():
    """
    Sets up the guilds based on the environment.
    """

    environment = os.getenv("ENVIRONMENT")

    environment = environment.lower()

    if environment not in ["testing", "production"]:
        raise ValueError("Invalid environment specified. Use 'testing' or 'production'.")

    if environment == "testing":
        guilds = [discord.Object(id=os.getenv("TEST_GUILD_ID"))]
    elif environment == "production":
        guilds = []
    print(f"Running in {environment} environment")
    return guilds