import discord
from discord import app_commands
from typing import Optional, List
import io
from discord.ext.commands import has_permissions
from data.tournament import (
    create_tournament, get_tournament, list_tournaments, delete_tournament,
    generate_bracket_image, Tournament, Participant, Match, tournament_name_autocomplete,
    save_tournaments
)

# Create tournament group
tournament_group = app_commands.Group(name="tournament", description="Commands for managing tournaments.")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="create", description="Create a new tournament (Admin only)")
@app_commands.describe(
    name="Name of the tournament",
    size="Maximum number of participants (2-64)"
)
@has_permissions(administrator=True)
async def tournament_create(interaction: discord.Interaction, name: str, size: int):
    await interaction.response.defer()
    
    # Create the tournament
    success, message = create_tournament(
        interaction.guild_id, 
        name, 
        size, 
        interaction.user.id
    )
    
    if not success:
        await interaction.followup.send(f"Failed to create tournament: {message}", ephemeral=True)
        return
    
    await interaction.followup.send(f"Tournament '{name}' created successfully! Use `/tournament add {name} @user` to add participants.")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="add", description="Add a user to a tournament")
@app_commands.describe(
    tournament_name="Name of the tournament",
    user="User to add to the tournament"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
@has_permissions(administrator=True)
async def tournament_add(interaction: discord.Interaction, tournament_name: str, user: discord.User):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has already started
    if tournament.started:
        await interaction.followup.send("Cannot add participants after the tournament has started.", ephemeral=True)
        return
    
    # Add the user to the tournament
    avatar_url = user.display_avatar.url
    success = tournament.add_participant(user.id, user.display_name, avatar_url)
    
    if not success:
        await interaction.followup.send(f"Failed to add {user.mention} to the tournament. They may already be participating or the tournament is full.", ephemeral=True)
        return
    
    # Save tournaments after modification
    save_tournaments()
    
    await interaction.followup.send(f"Added {user.mention} to tournament '{tournament_name}'! ({len(tournament.participants)}/{tournament.size} participants)")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="join", description="Join a tournament")
@app_commands.describe(
    tournament_name="Name of the tournament you want to join"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
async def tournament_join(interaction: discord.Interaction, tournament_name: str):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has already started
    if tournament.started:
        await interaction.followup.send("Cannot join after the tournament has started.", ephemeral=True)
        return
    
    # Add the user to the tournament
    avatar_url = interaction.user.display_avatar.url
    success = tournament.add_participant(interaction.user.id, interaction.user.display_name, avatar_url)
    
    if not success:
        await interaction.followup.send(f"Failed to join the tournament. You may already be participating or the tournament is full.", ephemeral=True)
        return
    
    # Save tournaments after modification
    save_tournaments()
    
    await interaction.followup.send(f"You have joined tournament '{tournament_name}'! ({len(tournament.participants)}/{tournament.size} participants)")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="leave", description="Leave a tournament")
@app_commands.describe(
    tournament_name="Name of the tournament you want to leave"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
async def tournament_leave(interaction: discord.Interaction, tournament_name: str):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has already started
    if tournament.started:
        await interaction.followup.send("Cannot leave after the tournament has started.", ephemeral=True)
        return
    
    # Remove the user from the tournament
    success = tournament.remove_participant(interaction.user.id)
    
    if not success:
        await interaction.followup.send(f"Failed to leave the tournament. You may not be participating.", ephemeral=True)
        return
    
    # Save tournaments after modification
    save_tournaments()
    
    await interaction.followup.send(f"You have left tournament '{tournament_name}'.")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="remove", description="Remove a user from a tournament (Admin only)")
@app_commands.describe(
    tournament_name="Name of the tournament",
    user="User to remove from the tournament"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
@has_permissions(administrator=True)
async def tournament_remove(interaction: discord.Interaction, tournament_name: str, user: discord.User):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has already started
    if tournament.started:
        await interaction.followup.send("Cannot remove participants after the tournament has started.", ephemeral=True)
        return
    
    # Remove the user from the tournament
    success = tournament.remove_participant(user.id)
    
    if not success:
        await interaction.followup.send(f"Failed to remove {user.mention} from the tournament. They may not be participating.", ephemeral=True)
        return
    
    # Save tournaments after modification
    save_tournaments()
    
    await interaction.followup.send(f"Removed {user.mention} from tournament '{tournament_name}'.")

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="start", description="Start a tournament (Admin only)")
@app_commands.describe(
    tournament_name="Name of the tournament to start"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
async def tournament_start(interaction: discord.Interaction, tournament_name: str):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has enough participants
    if len(tournament.participants) < 2:
        await interaction.followup.send("Cannot start tournament with fewer than 2 participants.", ephemeral=True)
        return
    
    # Start the tournament
    success = tournament.start_tournament()
    
    if not success:
        await interaction.followup.send("Failed to start the tournament. It may have already started.", ephemeral=True)
        return
    
    # Generate bracket image
    bracket_image = await generate_bracket_image(tournament)
    
    # Create a message with tournament info
    embed = discord.Embed(
        title=f"Tournament '{tournament_name}' has started!",
        description=f"The tournament has begun with {len(tournament.participants)} participants.",
        color=discord.Color.green()
    )
    
    # List first round matches
    current_matches = tournament.get_current_matches()
    if current_matches:
        match_list = []
        for match in current_matches:
            p1_name = match.participant1.display_name if match.participant1 else "TBD"
            p2_name = match.participant2.display_name if match.participant2 else "TBD"
            match_list.append(f"Match #{match.match_id}: {p1_name} vs {p2_name}")
        
        embed.add_field(
            name="Current Matches",
            value="\n".join(match_list),
            inline=False
        )
    
    # Send the message with the bracket image
    file = discord.File(fp=bracket_image, filename="tournament_bracket.png")
    embed.set_image(url="attachment://tournament_bracket.png")
    
    await interaction.followup.send(embed=embed, file=file)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="bracket", description="View the tournament bracket")
@app_commands.describe(
    tournament_name="Name of the tournament"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
async def tournament_bracket(interaction: discord.Interaction, tournament_name: str):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has started
    if not tournament.started:
        # Show list of participants instead
        embed = discord.Embed(
            title=f"Tournament '{tournament_name}' - Participants",
            description=f"The tournament has not started yet. {len(tournament.participants)}/{tournament.size} participants registered.",
            color=discord.Color.blue()
        )
        
        if tournament.participants:
            participant_list = []
            for i, participant in enumerate(tournament.participants, 1):
                participant_list.append(f"{i}. <@{participant.user_id}> ({participant.display_name})")
            
            embed.add_field(
                name="Registered Participants",
                value="\n".join(participant_list) if participant_list else "None yet",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        return
    
    # Generate bracket image
    bracket_image = await generate_bracket_image(tournament)
    
    # Create a message with tournament info
    embed = discord.Embed(
        title=f"Tournament '{tournament_name}' Bracket",
        description=f"Tournament status: {'Completed' if tournament.completed else 'In Progress'}",
        color=discord.Color.blue()
    )
    
    # List current matches
    current_matches = tournament.get_current_matches()
    if current_matches:
        match_list = []
        for match in current_matches:
            p1_name = match.participant1.display_name if match.participant1 else "TBD"
            p2_name = match.participant2.display_name if match.participant2 else "TBD"
            match_list.append(f"Match #{match.match_id}: {p1_name} vs {p2_name}")
        
        embed.add_field(
            name="Current Matches",
            value="\n".join(match_list),
            inline=False
        )
    
    # Show winner if tournament is completed
    if tournament.completed:
        final_match = max(tournament.matches.values(), key=lambda m: m.round_num)
        if final_match.winner:
            embed.add_field(
                name="Tournament Winner",
                value=f"🏆 <@{final_match.winner.user_id}> ({final_match.winner.display_name})",
                inline=False
            )
    
    # Send the message with the bracket image
    file = discord.File(fp=bracket_image, filename="tournament_bracket.png")
    embed.set_image(url="attachment://tournament_bracket.png")
    
    await interaction.followup.send(embed=embed, file=file)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="list", description="List all active tournaments")
async def tournament_list(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # Get all tournaments for this guild
    tournaments = list_tournaments(interaction.guild_id)
    
    if not tournaments:
        await interaction.followup.send("There are no active tournaments in this server.", ephemeral=True)
        return
    
    # Create embed with tournament info
    embed = discord.Embed(
        title="Active Tournaments",
        description=f"There are {len(tournaments)} active tournaments in this server.",
        color=discord.Color.blue()
    )
    
    for tournament in tournaments:
        status = "Not Started"
        if tournament.completed:
            status = "Completed"
        elif tournament.started:
            status = "In Progress"
        
        value = f"Status: {status}\n"
        value += f"Participants: {len(tournament.participants)}/{tournament.size}\n"
        value += f"Created by: <@{tournament.creator_id}>"
        
        embed.add_field(
            name=tournament.name,
            value=value,
            inline=True
        )
    
    await interaction.followup.send(embed=embed)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="match", description="Report a match result")
@app_commands.describe(
    tournament_name="Name of the tournament",
    match_id="ID of the match (visible on the bracket)",
    winner="The user who won the match"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
@has_permissions(administrator=True)
async def tournament_match(interaction: discord.Interaction, tournament_name: str, match_id: int, winner: discord.User):
    await interaction.response.defer()
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Check if tournament has started
    if not tournament.started:
        await interaction.followup.send("The tournament has not started yet.", ephemeral=True)
        return
    
    # Check if tournament is completed
    if tournament.completed:
        await interaction.followup.send("The tournament is already completed.", ephemeral=True)
        return
    
    # Check if match exists
    match = tournament.matches.get(match_id)
    if not match:
        await interaction.followup.send(f"Match #{match_id} not found in this tournament.", ephemeral=True)
        return
    
    # Check if match is already completed
    if match.completed:
        await interaction.followup.send(f"Match #{match_id} is already completed.", ephemeral=True)
        return
    
    # Check if match has both participants
    if not match.participant1 or not match.participant2:
        await interaction.followup.send(f"Match #{match_id} doesn't have both participants assigned yet.", ephemeral=True)
        return
    
    # Check if winner is one of the participants
    if winner.id != match.participant1.user_id and winner.id != match.participant2.user_id:
        await interaction.followup.send(f"{winner.mention} is not a participant in this match.", ephemeral=True)
        return
    
    # Check if user is the tournament creator, admin, or one of the participants
    is_admin = interaction.user.guild_permissions.administrator
    is_creator = interaction.user.id == tournament.creator_id
    is_participant = (interaction.user.id == match.participant1.user_id or 
                      interaction.user.id == match.participant2.user_id)
    
    # Record the result
    success = tournament.record_match_result(match_id, winner.id)
    
    if not success:
        await interaction.followup.send("Failed to record match result.", ephemeral=True)
        return
    
    # Get the loser
    loser = match.participant1 if match.winner.user_id == match.participant2.user_id else match.participant2
    
    # Generate bracket image
    bracket_image = await generate_bracket_image(tournament)
    
    # Create a message with match result
    embed = discord.Embed(
        title=f"Match #{match_id} Result - Tournament '{tournament_name}'",
        description=f"**{match.winner.display_name}** defeated **{loser.display_name}**",
        color=discord.Color.gold()
    )
    
    # Check if this was the final match
    if tournament.completed:
        embed.add_field(
            name="Tournament Completed",
            value=f"🏆 <@{match.winner.user_id}> is the tournament champion!",
            inline=False
        )
    else:
        # List next matches
        next_matches = tournament.get_current_matches()
        if next_matches:
            match_list = []
            for next_match in next_matches:
                p1_name = next_match.participant1.display_name if next_match.participant1 else "TBD"
                p2_name = next_match.participant2.display_name if next_match.participant2 else "TBD"
                match_list.append(f"Match #{next_match.match_id}: {p1_name} vs {p2_name}")
            
            embed.add_field(
                name="Next Matches",
                value="\n".join(match_list),
                inline=False
            )
    
    # Send the message with the bracket image
    file = discord.File(fp=bracket_image, filename="tournament_bracket.png")
    embed.set_image(url="attachment://tournament_bracket.png")
    
    await interaction.followup.send(embed=embed, file=file)

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@tournament_group.command(name="delete", description="Delete a tournament (Admin only)")
@app_commands.describe(
    tournament_name="Name of the tournament to delete"
)
@app_commands.autocomplete(tournament_name=tournament_name_autocomplete)
@has_permissions(administrator=True)
async def tournament_delete(interaction: discord.Interaction, tournament_name: str):
    await interaction.response.defer(ephemeral=True)
    
    # Get the tournament
    tournament = get_tournament(interaction.guild_id, tournament_name)
    if not tournament:
        await interaction.followup.send(f"Tournament '{tournament_name}' not found.", ephemeral=True)
        return
    
    # Delete the tournament
    success = delete_tournament(interaction.guild_id, tournament_name)
    
    if not success:
        await interaction.followup.send(f"Failed to delete tournament '{tournament_name}'.", ephemeral=True)
        return
    
    await interaction.followup.send(f"Tournament '{tournament_name}' has been deleted.")

def setup(tree: app_commands.CommandTree):
    # tree.add_command(tournament_group)
    print("Tournament is still TODO!")
    return