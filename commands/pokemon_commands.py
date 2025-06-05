import discord
from discord import app_commands
import aiohttp
import asyncio
import random
from data.pokemon import TYPE_COLORS, ALL_POKEMON_TYPES
from data.help_functions import fetch_data, POKEAPI_BASE_URL
from data.minigames import play_random_minigame

# Command Group
pokemon_group = app_commands.Group(name="pokemon", description="Commands related to Pokémon.")

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@pokemon_group.command(name="info", description="Get general information about a Pokémon.")
@app_commands.describe(pokemon="The name or National Pokédex ID of the Pokémon.")
async def pokemon_info(interaction: discord.Interaction, pokemon: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon.lower()}")

        if data is None:
            await interaction.followup.send(f"I could not find a Pokémon named '{pokemon}'.")
            return
        if data == "error":
            await interaction.followup.send("An error occurred while fetching Pokémon data.")
            return

        name = data['name'].capitalize()
        pokedex_id = data['id']
        types = [t['type']['name'].capitalize() for t in data['types']]
        abilities = [a['ability']['name'].replace('-', ' ').capitalize() for a in data['abilities']]
        height_m = data['height'] / 10.0  # decimetres to metres
        weight_kg = data['weight'] / 10.0  # hectograms to kilograms
        sprite_url = data['sprites']['front_default']
        
        primary_type = data['types'][0]['type']['name']
        embed_color = TYPE_COLORS.get(primary_type, discord.Color.default())

        embed = discord.Embed(
            title=f"{name} (#{pokedex_id})",
            color=embed_color
        )
        if sprite_url:
            embed.set_thumbnail(url=sprite_url)
        
        embed.add_field(name="Type", value=", ".join(types), inline=True)
        embed.add_field(name="Abilities", value=", ".join(abilities), inline=True)
        embed.add_field(name="Height", value=f"{height_m} m", inline=True)
        embed.add_field(name="Weight", value=f"{weight_kg} kg", inline=True)

        await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@pokemon_group.command(name="stats", description="Get the base stats of a Pokémon.")
@app_commands.describe(pokemon="The name or National Pokédex ID of the Pokémon.")
async def pokemon_stats(interaction: discord.Interaction, pokemon: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon.lower()}")

        if data is None:
            await interaction.followup.send(f"Sorry, I couldn't find a Pokémon named '{pokemon}'.")
            return
        if data == "error":
            await interaction.followup.send("Sorry, an error occurred while fetching Pokémon data.")
            return

        name = data['name'].capitalize()
        pokedex_id = data['id']
        sprite_url = data['sprites']['front_default']
        primary_type = data['types'][0]['type']['name']
        embed_color = TYPE_COLORS.get(primary_type, discord.Color.default())

        embed = discord.Embed(
            title=f"{name} (#{pokedex_id}) - Base Stats",
            color=embed_color
        )
        if sprite_url:
            embed.set_thumbnail(url=sprite_url)

        stat_map = {
            "hp": "HP",
            "attack": "Attack",
            "defense": "Defense",
            "special-attack": "Sp. Atk",
            "special-defense": "Sp. Def",
            "speed": "Speed"
        }

        for stat_info in data['stats']:
            stat_name = stat_map.get(stat_info['stat']['name'], stat_info['stat']['name'].capitalize())
            base_stat = stat_info['base_stat']
            embed.add_field(name=stat_name, value=str(base_stat), inline=True)
        
        await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@pokemon_group.command(name="weak", description="Get the type weaknesses, resistances, and immunities of a Pokémon.")
@app_commands.describe(pokemon="The name or National Pokédex ID of the Pokémon.")
async def pokemon_weaknesses(interaction: discord.Interaction, pokemon: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        pokemon_data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon.lower()}")

        if pokemon_data is None:
            await interaction.followup.send(f"Sorry, I couldn't find a Pokémon named '{pokemon}'.")
            return
        if pokemon_data == "error":
            await interaction.followup.send("Sorry, an error occurred while fetching Pokémon data.")
            return

        name = pokemon_data['name'].capitalize()
        pokedex_id = pokemon_data['id']
        sprite_url = pokemon_data['sprites']['front_default']
        
        pokemon_types_info = pokemon_data['types']
        primary_type_name = pokemon_types_info[0]['type']['name']
        embed_color = TYPE_COLORS.get(primary_type_name, discord.Color.default())

        damage_multipliers = {t: 1.0 for t in ALL_POKEMON_TYPES}

        for type_slot in pokemon_types_info:
            type_name = type_slot['type']['name']
            type_data = await fetch_data(session, f"{POKEAPI_BASE_URL}type/{type_name}")
            
            if not type_data or type_data == "error":
                await interaction.followup.send(f"Sorry, an error occurred while fetching type data for {type_name}.")
                return

            relations = type_data['damage_relations']
            for relation_type, multiplier_effect in [
                ('double_damage_from', 2.0),
                ('half_damage_from', 0.5),
                ('no_damage_from', 0.0)
            ]:
                for attacking_type_info in relations[relation_type]:
                    attacking_type_name = attacking_type_info['name']
                    if multiplier_effect == 0.0: # Immunity takes precedence
                        damage_multipliers[attacking_type_name] = 0.0
                    elif damage_multipliers[attacking_type_name] != 0.0: # Don't override immunity
                        damage_multipliers[attacking_type_name] *= multiplier_effect
        
        weak_to_x4 = [t.capitalize() for t, m in damage_multipliers.items() if m == 4.0]
        weak_to_x2 = [t.capitalize() for t, m in damage_multipliers.items() if m == 2.0]
        resists_x0_5 = [t.capitalize() for t, m in damage_multipliers.items() if m == 0.5]
        resists_x0_25 = [t.capitalize() for t, m in damage_multipliers.items() if m == 0.25]
        immune_to = [t.capitalize() for t, m in damage_multipliers.items() if m == 0.0]

        embed = discord.Embed(
            title=f"{name} (#{pokedex_id}) - Type Effectiveness",
            color=embed_color
        )
        if sprite_url:
            embed.set_thumbnail(url=sprite_url)

        if immune_to:
            embed.add_field(name="Immune To (x0)", value=", ".join(immune_to) or "None", inline=False)
        if resists_x0_25:
            embed.add_field(name="Resists (x0.25)", value=", ".join(resists_x0_25) or "None", inline=False)
        if resists_x0_5:
            embed.add_field(name="Resists (x0.5)", value=", ".join(resists_x0_5) or "None", inline=False)
        if weak_to_x2:
            embed.add_field(name="Weak To (x2)", value=", ".join(weak_to_x2) or "None", inline=False)
        if weak_to_x4:
            embed.add_field(name="Weak To (x4)", value=", ".join(weak_to_x4) or "None", inline=False)
        
        if not any([immune_to, resists_x0_25, resists_x0_5, weak_to_x2, weak_to_x4]):
             embed.description = "This Pokémon has neutral effectiveness against all types (or data is incomplete)."

        await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@pokemon_group.command(name="minigame", description="Play a minigame! From guess the pokemon, to a lot more!")
async def pokemon_guess(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # Get a random Pokemon ID (there are around 1010 Pokemon in the National Pokedex)
    pokemon_id = random.randint(1, 1010)
    await play_random_minigame(interaction, pokemon_id)

def setup(tree: app_commands.CommandTree):
    tree.add_command(pokemon_group)
