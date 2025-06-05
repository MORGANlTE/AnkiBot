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
@pokemon_group.command(name="info", description="Get comprehensive information about a Pokémon.")
@app_commands.describe(pokemon="The name or National Pokédex ID of the Pokémon.")
async def pokemon_info(interaction: discord.Interaction, pokemon: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        # Fetch basic Pokémon data
        pokemon_data = await fetch_data(session, f"{POKEAPI_BASE_URL}pokemon/{pokemon.lower()}")
        if pokemon_data is None:
            await interaction.followup.send(f"I could not find a Pokémon named '{pokemon}'.")
            return
        if pokemon_data == "error":
            await interaction.followup.send("An error occurred while fetching Pokémon data.")
            return

        # Fetch species data for description and evolution chain
        species_url = pokemon_data['species']['url']
        species_data = await fetch_data(session, species_url)
        if species_data is None or species_data == "error":
            await interaction.followup.send("Error fetching species data.")
            return

        # Get English description
        description = "No description available."
        for entry in species_data['flavor_text_entries']:
            if entry['language']['name'] == 'en':
                description = entry['flavor_text'].replace('\n', ' ').replace('\f', ' ')
                break

        # Basic info
        name = pokemon_data['name'].capitalize()
        pokedex_id = pokemon_data['id']
        types = [t['type']['name'].capitalize() for t in pokemon_data['types']]
        abilities = [a['ability']['name'].replace('-', ' ').capitalize() for a in pokemon_data['abilities']]
        height_m = pokemon_data['height'] / 10.0
        weight_kg = pokemon_data['weight'] / 10.0
        sprite_url = pokemon_data['sprites']['other']['official-artwork']['front_default'] or pokemon_data['sprites']['front_default']
        
        # Type effectiveness
        primary_type = pokemon_data['types'][0]['type']['name']
        embed_color = TYPE_COLORS.get(primary_type, discord.Color.default())

        # Calculate type effectiveness
        damage_multipliers = {t: 1.0 for t in ALL_POKEMON_TYPES}
        for type_slot in pokemon_data['types']:
            type_name = type_slot['type']['name']
            type_data = await fetch_data(session, f"{POKEAPI_BASE_URL}type/{type_name}")
            
            if not type_data or type_data == "error":
                continue

            relations = type_data['damage_relations']
            for relation_type, multiplier_effect in [
                ('double_damage_from', 2.0),
                ('half_damage_from', 0.5),
                ('no_damage_from', 0.0)
            ]:
                for attacking_type_info in relations[relation_type]:
                    attacking_type_name = attacking_type_info['name']
                    if multiplier_effect == 0.0:
                        damage_multipliers[attacking_type_name] = 0.0
                    elif damage_multipliers[attacking_type_name] != 0.0:
                        damage_multipliers[attacking_type_name] *= multiplier_effect
        
        weak_to = []
        if any(m >= 2.0 for m in damage_multipliers.values()):
            weak_to = [f"{t.capitalize()} ({m}x)" for t, m in damage_multipliers.items() if m >= 2.0]
        
        resist_immune = []
        if any(m <= 0.5 for m in damage_multipliers.values()):
            resist_immune = [f"{t.capitalize()} ({m}x)" for t, m in damage_multipliers.items() if m <= 0.5]

        # Evolution chain
        evolution_text = "No evolution data available."
        if 'evolution_chain' in species_data:
            evo_url = species_data['evolution_chain']['url']
            evo_data = await fetch_data(session, evo_url)
            
            if evo_data and evo_data != "error":
                evolution_chain = []
                
                def parse_evolution(chain_link, evo_details=""):
                    species_name = chain_link['species']['name'].capitalize()
                    evolution_chain.append(f"{species_name}{evo_details}")
                    
                    for evolution in chain_link.get('evolves_to', []):
                        evo_details = ""
                        if evolution.get('evolution_details'):
                            detail = evolution['evolution_details'][0]
                            if 'min_level' in detail and detail['min_level']:
                                evo_details = f" (Level {detail['min_level']})"
                            elif 'item' in detail and detail['item']:
                                evo_details = f" ({detail['item']['name'].replace('-', ' ').capitalize()})"
                            elif 'trigger' in detail and detail['trigger']['name'] == 'trade':
                                evo_details = " (Trade)"
                        parse_evolution(evolution, evo_details)
                
                parse_evolution(evo_data['chain'])
                evolution_text = " → ".join(evolution_chain)

        # Create embed
        embed = discord.Embed(
            title=f"{name} (#{pokedex_id})",
            description=description,
            color=embed_color
        )
        
        if sprite_url:
            embed.set_thumbnail(url=sprite_url)
        
        # Basic Info Section
        basic_info = f"**Type**: {', '.join(types)}\n"
        basic_info += f"**Height**: {height_m} m\n"
        basic_info += f"**Weight**: {weight_kg} kg\n"
        basic_info += f"**Abilities**: {', '.join(abilities)}"
        embed.add_field(name="📋 Basic Info", value=basic_info, inline=False)
        
        # Evolution Chain
        embed.add_field(name="⬆️ Evolution Chain", value=evolution_text, inline=False)
        
        # Type Effectiveness
        if weak_to:
            embed.add_field(name="⚠️ Weak To", value=", ".join(weak_to), inline=False)
        
        if resist_immune:
            embed.add_field(name="🛡️ Resists/Immune To", value=", ".join(resist_immune), inline=False)

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
            "hp": "❤️ HP",
            "attack": "⚔️ Attack",
            "defense": "🛡️ Defense",
            "special-attack": "💧 Sp. Atk",
            "special-defense": "☂️ Sp. Def",
            "speed": "⚡ Speed"
        }

        for stat_info in data['stats']:
            stat_name = stat_map.get(stat_info['stat']['name'], stat_info['stat']['name'].capitalize())
            base_stat = str(stat_info['base_stat'])
            embed.add_field(name=stat_name + " - " + base_stat, value="** **", inline=False)
        
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
        pokemon_types_info = pokemon_data['types']
        pokemon_types = [t['type']['name'].capitalize() for t in pokemon_types_info]
        
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
                    if multiplier_effect == 0.0:
                        damage_multipliers[attacking_type_name] = 0.0
                    elif damage_multipliers[attacking_type_name] != 0.0:
                        damage_multipliers[attacking_type_name] *= multiplier_effect
        
        # Create a sorted list of multipliers and types
        type_effectiveness = []
        for t, m in damage_multipliers.items():
            if m != 1.0:  # Only include non-neutral effectiveness
                type_effectiveness.append((t.capitalize(), m))
        
        # Group by effectiveness category
        weaknesses = []
        resistances = []
        immunities = []
        
        for t, m in type_effectiveness:
            if m >= 2.0:
                weaknesses.append((t, m))
            elif m == 0.0:
                immunities.append(t)
            elif m < 1.0:
                resistances.append((t, m))
        
        # Sort within each category
        weaknesses.sort(key=lambda x: (-x[1], x[0]))  # Sort by multiplier (desc) then name
        resistances.sort(key=lambda x: (x[1], x[0]))  # Sort by multiplier (asc) then name
        immunities.sort()
        
        # Build response message
        response = f"**{name}** ({'/'.join(pokemon_types)}) type effectiveness:\n\n"
        
        # Weaknesses section
        if weaknesses:
            response += "⚠️ **Weak to**:\n"
            # Group by same multiplier
            multiplier_groups = {}
            for type_name, mult in weaknesses:
                if mult not in multiplier_groups:
                    multiplier_groups[mult] = []
                multiplier_groups[mult].append(type_name)
            
            for mult, types in sorted(multiplier_groups.items(), reverse=True):
                response += f"{', '.join(types)} ({mult}x)\n"
            response += "\n"
        
        # Resistances section
        if resistances:
            response += "🛡️ **Resists**:\n"
            # Group by same multiplier
            multiplier_groups = {}
            for type_name, mult in resistances:
                if mult not in multiplier_groups:
                    multiplier_groups[mult] = []
                multiplier_groups[mult].append(type_name)
            
            for mult, types in sorted(multiplier_groups.items()):
                response += f"{', '.join(types)} ({mult}x)\n"
            response += "\n"
        
        # Immunities section
        if immunities:
            response += "❌ **Immune to**:\n"
            response += f"{', '.join(immunities)} (0x)\n"
        
        if not weaknesses and not resistances and not immunities:
            response += "No special type effectiveness (all types are neutral)."
        
        await interaction.followup.send(response)

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
