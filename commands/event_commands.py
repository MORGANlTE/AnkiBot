import discord
from discord import app_commands
import json
import datetime
from typing import Optional, List
import io
from data.events import (
    get_event, get_events, get_active_events,
    add_participant, submit_entry, validate_catch_event_entry,
    generate_pokemon_image, event_name_autocomplete, get_pokemon_names
)
from data.badges import get_badge_id


# Event type choices
EVENT_TYPE_CHOICES = [
    app_commands.Choice(name="Catch Event", value="catch")
]


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="list", description="List all events in this server")
async def event_list(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # Get all events for this guild
    events = get_events(interaction.guild_id)
    
    if not events:
        await interaction.followup.send("There are no events available in this server.", ephemeral=True)
        return
    
    # Create embed with event info
    embed = discord.Embed(
        title="Available Events",
        description=f"There are {len(events)} events in this server.",
        color=discord.Color.blue()
    )
    
    # Current time for checking active status
    now = datetime.datetime.now()
    
    for event in events:
        start = datetime.datetime.fromisoformat(event.start_date)
        end = datetime.datetime.fromisoformat(event.end_date)
        
        status = "Upcoming"
        if now > end:
            status = "Ended"
        elif now >= start:
            status = "Active"
        
        value = f"Type: {event.event_type.capitalize()}\n"
        value += f"Status: {status}\n"
        value += f"Start: {start.strftime('%Y-%m-%d %H:%M')}\n"
        value += f"End: {end.strftime('%Y-%m-%d %H:%M')}\n"
        
        if event.event_type == "catch":
            value += f"Pokémon to catch: {len(event.pokemon_list)}"
        
        embed.add_field(
            name=event.name,
            value=value,
            inline=True
        )
    
    await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="info", description="View information about a specific event")
@app_commands.describe(
    event_name="The event to view"
)
@app_commands.autocomplete(event_name=event_name_autocomplete)
async def event_info(interaction: discord.Interaction, event_name: str):
    await interaction.response.defer()
    
    # Get the event
    event = get_event(interaction.guild_id, event_name)
    if not event:
        await interaction.followup.send(f"Event '{event_name}' not found.", ephemeral=True)
        return
    
    # Create embed with event info
    embed = discord.Embed(
        title=f"Event: {event.name}",
        description=f"Type: {event.event_type.capitalize()}",
        color=discord.Color.blue()
    )
    
    # Add event dates
    start = datetime.datetime.fromisoformat(event.start_date)
    end = datetime.datetime.fromisoformat(event.end_date)
    embed.add_field(
        name="Event Period",
        value=f"Start: {start.strftime('%Y-%m-%d %H:%M')}\nEnd: {end.strftime('%Y-%m-%d %H:%M')}",
        inline=False
    )
    
    # Add event creator
    embed.add_field(
        name="Created by",
        value=f"<@{event.creator_id}>",
        inline=False
    )
    
    # Add participant count
    embed.add_field(
        name="Participants",
        value=f"{len(event.participants)}",
        inline=True
    )
    
    # Add participants who have submitted
    submitted_count = sum(1 for p in event.participants.values() if p["submitted"])
    embed.add_field(
        name="Submitted",
        value=f"{submitted_count}",
        inline=True
    )
    
    # For catch events, generate and attach image of Pokémon
    if event.event_type == "catch" and event.pokemon_list:
        embed.add_field(
            name="Pokémon to Catch",
            value=f"Total: {len(event.pokemon_list)}\n(See image below)",
            inline=False
        )
        
        # Generate image of Pokémon to catch
        pokemon_image = await generate_pokemon_image(event.pokemon_list)
        if pokemon_image:
            file = discord.File(fp=pokemon_image, filename="pokemon_to_catch.png")
            embed.set_image(url="attachment://pokemon_to_catch.png")
            await interaction.followup.send(embed=embed, file=file)
            return
    
    # If no image was generated or attached
    await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="enter", description="Enter an event by submitting your Pokémon data")
@app_commands.describe(
    event_name="The event to enter",
    file="JSON file with your caught Pokémon data"
)
@app_commands.autocomplete(event_name=event_name_autocomplete)
async def event_enter(interaction: discord.Interaction, event_name: str, file: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    
    # Get the event
    event = get_event(interaction.guild_id, event_name)
    if not event:
        await interaction.followup.send(f"Event '{event_name}' not found.", ephemeral=True)
        return
    
    # Check if event is active
    now = datetime.datetime.now()
    start = datetime.datetime.fromisoformat(event.start_date)
    end = datetime.datetime.fromisoformat(event.end_date)
    
    if now < start:
        await interaction.followup.send("This event hasn't started yet.", ephemeral=True)
        return
    
    if now > end:
        await interaction.followup.send("This event has already ended.", ephemeral=True)
        return
    
    # Add participant to the event even before validating submission
    # This ensures they appear in the participants list even if validation fails
    add_participant(interaction.guild_id, event_name, interaction.user.id)
    
    # Check file type
    if not file.filename.endswith('.json'):
        await interaction.followup.send("Please submit a JSON file.", ephemeral=True)
        return
    
    # Get file content
    try:
        file_content = await file.read()
        entry_data = json.loads(file_content.decode('utf-8'))
    except Exception as e:
        await interaction.followup.send(f"Error reading file: {str(e)}", ephemeral=True)
        return
    
    # Validate submission based on event type
    if event.event_type == "catch":
        valid, message, results = await validate_catch_event_entry(entry_data, event.pokemon_list)
        
        # Get names for missing Pokemon
        missing_pokemon_names = {}
        if results['missing']:
            missing_pokemon_names = await get_pokemon_names(results['missing'])
        
        # Create a detailed response embed
        embed = discord.Embed(
            title=f"Event Submission: {event_name}",
            description=message,
            color=discord.Color.green() if valid else discord.Color.gold()
        )
        
        # Add caught Pokemon details
        if results['caught']:
            caught_list = []
            for p_id, pokemon_info in results['caught'].items():
                name = pokemon_info['name']
                nickname = f" ({pokemon_info['nickname']})" if pokemon_info['nickname'] else ""
                
                # Parse date more flexibly to handle different formats
                try:
                    # Try ISO format with T separator
                    capture_date = datetime.datetime.fromisoformat(pokemon_info['capture_date'])
                except (ValueError, TypeError):
                    try:
                        # Try standard format with space separator
                        capture_date = datetime.datetime.strptime(pokemon_info['capture_date'], '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        # Fallback to just showing the raw date
                        capture_date_str = str(pokemon_info['capture_date'])
                        caught_list.append(f"• #{p_id}: {name}{nickname} - Lvl {pokemon_info['level']} - {capture_date_str}")
                        continue
                
                # Format the date nicely
                caught_list.append(f"• #{p_id}: {name}{nickname} - Lvl {pokemon_info['level']} - {capture_date.strftime('%d %B')}")
            
            embed.add_field(
                name=f"Caught Pokémon ({len(results['caught'])})",
                value="\n".join(caught_list) or "None",
                inline=False
            )
        
        # Add missing Pokemon details
        if results['missing']:
            missing_list = []
            for p_id in results['missing']:
                name = missing_pokemon_names.get(p_id, f"Pokémon #{p_id}")
                missing_list.append(f"• #{p_id}: {name}")
            
            embed.add_field(
                name=f"Missing Pokémon ({len(results['missing'])})",
                value="\n".join(missing_list) or "None",
                inline=False
            )
        
        # Show progress with emoji bars instead of percentage
        total_required = results['total_required']
        total_caught = results['total_caught']
        progress_blocks = 10  # Total number of blocks in progress bar
        
        # Calculate filled blocks (rounded down)
        filled_blocks = int((total_caught / total_required) * progress_blocks) if total_required > 0 else 0
        empty_blocks = progress_blocks - filled_blocks
        
        # Create progress bar with emojis
        progress_bar = "🟩" * filled_blocks + "⬛" * empty_blocks
        
        embed.add_field(
            name="Progress",
            value=f"{progress_bar}\n{total_caught}/{total_required} Pokémon caught",
            inline=False
        )
        
        # Calculate completion percentage
        completion_percentage = (total_caught / total_required * 100) if total_required > 0 else 0
        
        # Store only the necessary stats instead of the entire entry data
        submission_data = {
            'total_caught': total_caught,
            'total_required': total_required,
            'completion_percentage': completion_percentage,
            'date_submitted': datetime.datetime.now().isoformat()
        }
        
        # Submit the entry if valid
        if submit_entry(interaction.guild_id, event_name, interaction.user.id, submission_data):
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("Failed to submit your entry. Please try again.", ephemeral=True)
    else:
        await interaction.followup.send("This event type doesn't support submissions yet.", ephemeral=True)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="leaderboard", description="View the leaderboard for an event")
@app_commands.describe(
    event_name="The event to view the leaderboard for"
)
@app_commands.autocomplete(event_name=event_name_autocomplete)
async def event_leaderboard(interaction: discord.Interaction, event_name: str):
    await interaction.response.defer()
    
    # Get the event
    event = get_event(interaction.guild_id, event_name)
    if not event:
        await interaction.followup.send(f"Event '{event_name}' not found.", ephemeral=True)
        return
    
    # Check if event has participants
    if not event.participants:
        await interaction.followup.send(f"No one has participated in '{event_name}' yet.", ephemeral=True)
        return
    
    # Get participant data with progress information
    leaderboard_data = []
    
    # Add all participants to the leaderboard
    for user_id_str, participant_data in event.participants.items():
        user_id = user_id_str  # Keep as string for the mention
        
        if participant_data.get("submitted", False):
            # Get stored submission data
            submission_data = participant_data.get("data", {})
            
            # Add to leaderboard data
            leaderboard_data.append({
                "user_id": user_id,
                "total_caught": submission_data.get('total_caught', 0),
                "total_required": submission_data.get('total_required', len(event.pokemon_list)),
                "completion_percentage": submission_data.get('completion_percentage', 0),
                "has_submitted": True,
                "submission_date": submission_data.get('date_submitted', '')
            })
        else:
            # Add participants who haven't submitted with 0 progress
            leaderboard_data.append({
                "user_id": user_id,
                "total_caught": 0,
                "total_required": len(event.pokemon_list),
                "completion_percentage": 0,
                "has_submitted": False
            })
    
    # Sort by completion percentage (descending) and then by total caught (descending)
    leaderboard_data.sort(key=lambda x: (x["completion_percentage"], x["total_caught"]), reverse=True)
    
    # Create leaderboard embed
    embed = discord.Embed(
        title=f"Leaderboard: {event_name}",
        description=f"Participants: {len(event.participants)}",
        color=discord.Color.gold()
    )
    
    # Add leaderboard entries
    if leaderboard_data:
        for i, entry in enumerate(leaderboard_data, 1):
            # Skip showing non-submitters after a certain rank to keep the embed clean
            if not entry["has_submitted"] and i > 10:
                continue
                
            # Create progress bar
            progress_blocks = 10
            
            # Medal emoji for top 3
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            # Format the entry
            name_field = f"** **"
            
            if entry["has_submitted"]:
                value_field = f"{medal}{i}. <@{entry['user_id']}> ({entry['total_caught']}/{entry['total_required']})"
            else:
                value_field = "No submission yet"
            
            embed.add_field(
                name=name_field,
                value=value_field,
                inline=False
            )
    else:
        embed.add_field(
            name="No participants yet",
            value="Be the first to join this event!",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)


def setup(tree: app_commands.CommandTree):
    # Group for regular event commands: /event list, /event info, etc.
    regular_event_group = app_commands.Group(name="event", description="Commands for managing events.")
    regular_event_group.add_command(event_list)
    regular_event_group.add_command(event_info)
    regular_event_group.add_command(event_enter)
    regular_event_group.add_command(event_leaderboard)
    tree.add_command(regular_event_group)