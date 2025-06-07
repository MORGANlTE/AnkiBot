import discord
from typing import List, Dict, Optional, Tuple
import random
import math
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import os
import json
from discord import app_commands

# Path for tournament data file
TOURNAMENT_DATA_FILE = os.path.join(os.path.dirname(__file__), 'tournament_data.json')

# Dictionary to store active tournaments by guild ID
# Structure: {guild_id: {tournament_name: Tournament}}
active_tournaments = {}

# Load tournaments from file if it exists
def load_tournaments():
    """Load tournaments from the JSON file."""
    global active_tournaments
    if not os.path.exists(TOURNAMENT_DATA_FILE):
        # make sure the file exists
        os.makedirs(os.path.dirname(TOURNAMENT_DATA_FILE), exist_ok=True)
        
        print("No tournament data file found, starting with empty tournaments.")
        active_tournaments = {}
        # Initialize with empty tournaments
        # This ensures that the file is created if it doesn't exist

        with open(TOURNAMENT_DATA_FILE, 'w') as f:
            json.dump({}, f, indent=2)
        print("Created empty tournament data file.")
        
    try:
        with open(TOURNAMENT_DATA_FILE, 'r') as f:
            data = json.load(f)
            
        # Convert guild_ids from string back to int
        for guild_id_str, guild_tournaments in data.items():
            guild_id = int(guild_id_str)
            active_tournaments[guild_id] = {}
            
            for tournament_name, tournament_data in guild_tournaments.items():
                # Recreate tournament object
                tournament = Tournament(
                    tournament_data['name'],
                    tournament_data['size'],
                    tournament_data['creator_id']
                )
                tournament.current_round = tournament_data['current_round']
                tournament.started = tournament_data['started']
                tournament.completed = tournament_data['completed']
                
                # Recreate participants
                for p_data in tournament_data['participants']:
                    participant = Participant(
                        p_data['user_id'],
                        p_data['display_name'],
                        p_data['avatar_url']
                    )
                    participant.wins = p_data['wins']
                    participant.losses = p_data['losses']
                    tournament.participants.append(participant)
                
                # Recreate matches (first pass without linking participants)
                for match_id_str, match_data in tournament_data['matches'].items():
                    match_id = int(match_id_str)
                    match = Match(
                        match_id,
                        match_data['round_num'],
                        match_data['position']
                    )
                    match.next_match_id = match_data['next_match_id']
                    match.completed = match_data['completed']
                    tournament.matches[match_id] = match
                
                # Second pass to link participants to matches
                for match_id_str, match_data in tournament_data['matches'].items():
                    match_id = int(match_id_str)
                    match = tournament.matches[match_id]
                    
                    # Link participant1
                    if match_data['participant1_id'] is not None:
                        p1 = next((p for p in tournament.participants 
                                  if p.user_id == match_data['participant1_id']), None)
                        match.participant1 = p1
                    
                    # Link participant2
                    if match_data['participant2_id'] is not None:
                        p2 = next((p for p in tournament.participants 
                                  if p.user_id == match_data['participant2_id']), None)
                        match.participant2 = p2
                    
                    # Link winner
                    if match_data['winner_id'] is not None:
                        winner = next((p for p in tournament.participants 
                                     if p.user_id == match_data['winner_id']), None)
                        match.winner = winner
                    
                    # Link loser
                    if match_data['loser_id'] is not None:
                        loser = next((p for p in tournament.participants 
                                    if p.user_id == match_data['loser_id']), None)
                        match.loser = loser
                
                # Add tournament to active tournaments
                active_tournaments[guild_id][tournament_name] = tournament
        
        print(f"Loaded {len(active_tournaments)} guilds with tournaments")
    except Exception as e:
        print(f"Error loading tournaments: {e}")
        # Start with empty tournaments if there's an error
        active_tournaments = {}

def save_tournaments():
    """Save tournaments to a JSON file."""
    try:
        # Convert tournaments to a serializable format
        data = {}
        
        for guild_id, guild_tournaments in active_tournaments.items():
            guild_data = {}
            
            for tournament_name, tournament in guild_tournaments.items():
                tournament_data = {
                    'name': tournament.name,
                    'size': tournament.size,
                    'creator_id': tournament.creator_id,
                    'current_round': tournament.current_round,
                    'started': tournament.started,
                    'completed': tournament.completed,
                    'participants': [],
                    'matches': {}
                }
                
                # Serialize participants
                for participant in tournament.participants:
                    participant_data = {
                        'user_id': participant.user_id,
                        'display_name': participant.display_name,
                        'avatar_url': participant.avatar_url,
                        'wins': participant.wins,
                        'losses': participant.losses
                    }
                    tournament_data['participants'].append(participant_data)
                
                # Serialize matches
                for match_id, match in tournament.matches.items():
                    match_data = {
                        'match_id': match.match_id,
                        'round_num': match.round_num,
                        'position': match.position,
                        'participant1_id': match.participant1.user_id if match.participant1 else None,
                        'participant2_id': match.participant2.user_id if match.participant2 else None,
                        'winner_id': match.winner.user_id if match.winner else None,
                        'loser_id': match.loser.user_id if match.loser else None,
                        'next_match_id': match.next_match_id,
                        'completed': match.completed
                    }
                    tournament_data['matches'][str(match_id)] = match_data
                
                guild_data[tournament_name] = tournament_data
            
            data[str(guild_id)] = guild_data
        
        # Save to file
        os.makedirs(os.path.dirname(TOURNAMENT_DATA_FILE), exist_ok=True)
        with open(TOURNAMENT_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
    except Exception as e:
        print(f"Error saving tournaments: {e}")

class Participant:
    def __init__(self, user_id: int, display_name: str, avatar_url: str):
        self.user_id = user_id
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.wins = 0
        self.losses = 0

class Match:
    def __init__(self, match_id: int, round_num: int, position: int):
        self.match_id = match_id
        self.round_num = round_num
        self.position = position
        self.participant1: Optional[Participant] = None
        self.participant2: Optional[Participant] = None
        self.winner: Optional[Participant] = None
        self.loser: Optional[Participant] = None
        self.next_match_id: Optional[int] = None
        self.completed = False

class Tournament:
    def __init__(self, name: str, size: int, creator_id: int):
        self.name = name
        self.size = size  # Number of participants
        self.creator_id = creator_id
        self.participants: List[Participant] = []
        self.matches: Dict[int, Match] = {}
        self.current_round = 1
        self.started = False
        self.completed = False
        
        # Initialize bracket structure
        self._initialize_bracket()
    
    def _initialize_bracket(self):
        """Initialize the tournament bracket structure."""
        # Calculate total number of rounds needed
        num_rounds = math.ceil(math.log2(self.size))
        total_matches = (2 ** num_rounds) - 1
        
        # Create matches for each round, starting from the final
        match_id = 1  # Start with 1 for the final match
        
        # Create the final match
        final_match = Match(match_id, num_rounds, 1)
        self.matches[match_id] = final_match
        
        # Create matches for earlier rounds
        for round_num in range(num_rounds - 1, 0, -1):
            matches_in_round = 2 ** (num_rounds - round_num)
            for position in range(1, matches_in_round + 1):
                parent_match_id = match_id
                match_id += 1
                
                # Create match
                match = Match(match_id, round_num, position)
                self.matches[match_id] = match
                
                # Link to next match
                parent_position = (position + 1) // 2
                parent_match = next((m for m in self.matches.values() 
                                     if m.round_num == round_num + 1 and m.position == parent_position), None)
                if parent_match:
                    match.next_match_id = parent_match.match_id
    
    def add_participant(self, user_id: int, display_name: str, avatar_url: str) -> bool:
        """Add a participant to the tournament."""
        # Check if tournament is already full
        if len(self.participants) >= self.size:
            return False
            
        # Check if user is already in tournament
        if any(p.user_id == user_id for p in self.participants):
            return False
            
        participant = Participant(user_id, display_name, avatar_url)
        self.participants.append(participant)
        return True
    
    def remove_participant(self, user_id: int) -> bool:
        """Remove a participant from the tournament."""
        if self.started:
            return False  # Can't remove after tournament has started
            
        for i, participant in enumerate(self.participants):
            if participant.user_id == user_id:
                self.participants.pop(i)
                return True
        return False
    
    def start_tournament(self) -> bool:
        """Start the tournament by seeding participants into the bracket."""
        if self.started or len(self.participants) < 2:
            return False
            
        # Shuffle participants for random seeding
        random.shuffle(self.participants)
        
        # Get all first-round matches
        first_round_matches = [m for m in self.matches.values() if m.round_num == 1]
        first_round_matches.sort(key=lambda m: m.position)
        
        # Seed participants into first-round matches
        for i, participant in enumerate(self.participants):
            match_index = i // 2
            if match_index < len(first_round_matches):
                match = first_round_matches[match_index]
                if i % 2 == 0:
                    match.participant1 = participant
                else:
                    match.participant2 = participant
        
        # Handle byes for matches with only one participant
        for match in first_round_matches:
            if match.participant1 and not match.participant2:
                # Automatically advance single participant
                match.winner = match.participant1
                match.completed = True
                self._advance_winner(match)
            elif match.participant2 and not match.participant1:
                # Automatically advance single participant
                match.winner = match.participant2
                match.completed = True
                self._advance_winner(match)
        
        self.started = True
        return True
    
    def record_match_result(self, match_id: int, winner_id: int) -> bool:
        """Record the result of a match."""
        if not self.started or self.completed:
            return False
            
        match = self.matches.get(match_id)
        if not match or match.completed:
            return False
            
        # Determine winner and loser
        winner = None
        loser = None
        
        if match.participant1 and match.participant1.user_id == winner_id:
            winner = match.participant1
            loser = match.participant2
        elif match.participant2 and match.participant2.user_id == winner_id:
            winner = match.participant2
            loser = match.participant1
        else:
            return False  # Winner ID doesn't match either participant
            
        # Update match
        match.winner = winner
        match.loser = loser
        match.completed = True
        
        # Update participant stats
        winner.wins += 1
        if loser:
            loser.losses += 1
        
        # Advance winner to next match
        self._advance_winner(match)
        
        # Check if tournament is complete
        if match.round_num == max(m.round_num for m in self.matches.values()):
            self.completed = True
            
        return True
    
    def _advance_winner(self, match: Match):
        """Advance the winner to the next match."""
        if not match.next_match_id:
            return  # No next match (this was the final)
            
        next_match = self.matches[match.next_match_id]
        
        # Determine which slot to place the winner in
        if match.position % 2 == 1:
            next_match.participant1 = match.winner
        else:
            next_match.participant2 = match.winner
        
        # Check if next match is ready to be played
        if (next_match.participant1 and next_match.participant2) or \
           (next_match.participant1 and not next_match.participant2 and 
            all(m.completed for m in self.matches.values() 
                if m.next_match_id == next_match.match_id and m.position % 2 == 0)) or \
           (next_match.participant2 and not next_match.participant1 and 
            all(m.completed for m in self.matches.values() 
                if m.next_match_id == next_match.match_id and m.position % 2 == 1)):
            # If only one participant is present because the other side had no matches,
            # automatically advance them
            if next_match.participant1 and not next_match.participant2:
                next_match.winner = next_match.participant1
                next_match.completed = True
                self._advance_winner(next_match)
            elif next_match.participant2 and not next_match.participant1:
                next_match.winner = next_match.participant2
                next_match.completed = True
                self._advance_winner(next_match)
    
    def get_current_matches(self) -> List[Match]:
        """Get matches that are currently playable."""
        if not self.started or self.completed:
            return []
            
        # A match is playable if:
        # 1. It's not completed
        # 2. It has both participants assigned
        playable_matches = [
            m for m in self.matches.values()
            if not m.completed and m.participant1 and m.participant2
        ]
        
        return playable_matches
    
    def get_participant_matches(self, user_id: int) -> List[Match]:
        """Get all matches involving a specific participant."""
        return [
            m for m in self.matches.values()
            if (m.participant1 and m.participant1.user_id == user_id) or
               (m.participant2 and m.participant2.user_id == user_id)
        ]
    
    def get_next_round_matches(self) -> List[Match]:
        """Get matches for the next round."""
        if not self.started or self.completed:
            return []
            
        # Find the earliest round with incomplete matches
        min_incomplete_round = float('inf')
        for match in self.matches.values():
            if not match.completed and match.participant1 and match.participant2:
                min_incomplete_round = min(min_incomplete_round, match.round_num)
        
        if min_incomplete_round == float('inf'):
            return []
            
        # Get matches in that round
        return [
            m for m in self.matches.values()
            if m.round_num == min_incomplete_round and 
               not m.completed and 
               m.participant1 and m.participant2
        ]

async def generate_bracket_image(tournament: Tournament) -> io.BytesIO:
    """Generate an image visualization of the tournament bracket."""
    # Constants for image generation
    PADDING = 20
    MATCH_WIDTH = 180
    MATCH_HEIGHT = 80
    ROUND_SPACING = 200
    MATCH_SPACING = 100
    AVATAR_SIZE = 40
    CONNECTOR_WIDTH = 3
    
    # Calculate image dimensions
    num_rounds = max(m.round_num for m in tournament.matches.values())
    max_matches_in_round = max(
        sum(1 for m in tournament.matches.values() if m.round_num == r)
        for r in range(1, num_rounds + 1)
    )
    
    image_width = (num_rounds * (MATCH_WIDTH + ROUND_SPACING)) + PADDING * 2
    image_height = (max_matches_in_round * (MATCH_HEIGHT + MATCH_SPACING)) + PADDING * 2
    
    # Create base image
    image = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        name_font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        # Fallback to default font
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
    
    # Draw title
    title = f"{tournament.name} Tournament"
    draw.text((PADDING, PADDING), title, fill=(0, 0, 0), font=title_font)
    
    # Draw brackets round by round
    async with aiohttp.ClientSession() as session:
        # Organize matches by round
        matches_by_round = {}
        for match in tournament.matches.values():
            if match.round_num not in matches_by_round:
                matches_by_round[match.round_num] = []
            matches_by_round[match.round_num].append(match)
        
        # Sort matches within each round
        for round_num in matches_by_round:
            matches_by_round[round_num].sort(key=lambda m: m.position)
        
        # Draw each round
        for round_num in range(1, num_rounds + 1):
            matches = matches_by_round.get(round_num, [])
            matches_in_round = len(matches)
            
            x = PADDING + (round_num - 1) * (MATCH_WIDTH + ROUND_SPACING)
            
            # Calculate spacing for this round
            total_height_needed = matches_in_round * MATCH_HEIGHT + (matches_in_round - 1) * MATCH_SPACING
            first_match_y = (image_height - total_height_needed) / 2
            
            for i, match in enumerate(matches):
                y = first_match_y + i * (MATCH_HEIGHT + MATCH_SPACING)
                
                # Draw match box
                box_color = (220, 220, 220)
                if match.completed:
                    box_color = (200, 240, 200)  # Green tint for completed matches
                draw.rectangle([(int(x), int(y)), (int(x + MATCH_WIDTH), int(y + MATCH_HEIGHT))], fill=box_color, outline=(0, 0, 0))
                
                # Draw participant 1
                if match.participant1:
                    # Try to download avatar
                    avatar_img = None
                    try:
                        async with session.get(match.participant1.avatar_url) as resp:
                            if resp.status == 200:
                                avatar_data = await resp.read()
                                avatar_img = Image.open(io.BytesIO(avatar_data)).convert('RGBA')
                                avatar_img = avatar_img.resize((AVATAR_SIZE, AVATAR_SIZE))
                    except Exception:
                        pass
                    
                    # Draw avatar if available
                    if avatar_img:
                        image.paste(avatar_img, (int(x + 10), int(y + 10)), avatar_img)
                        
                    # Draw name
                    name = match.participant1.display_name
                    if len(name) > 15:
                        name = name[:12] + "..."
                    draw.text((int(x + AVATAR_SIZE + 15), int(y + 15)), name, fill=(0, 0, 0), font=name_font)
                    
                    # Indicate winner
                    if match.winner and match.winner.user_id == match.participant1.user_id:
                        draw.polygon([(int(x + 5), int(y + 5)), (int(x + 15), int(y + 5)), 
                                     (int(x + 10), int(y + 15))], fill=(0, 200, 0))
                
                # Draw participant 2
                if match.participant2:
                    # Try to download avatar
                    avatar_img = None
                    try:
                        async with session.get(match.participant2.avatar_url) as resp:
                            if resp.status == 200:
                                avatar_data = await resp.read()
                                avatar_img = Image.open(io.BytesIO(avatar_data)).convert('RGBA')
                                avatar_img = avatar_img.resize((AVATAR_SIZE, AVATAR_SIZE))
                    except Exception:
                        pass
                    
                    # Draw avatar if available
                    if avatar_img:
                        image.paste(avatar_img, (int(x + 10), int(y + MATCH_HEIGHT - AVATAR_SIZE - 10)), avatar_img)
                        
                    # Draw name
                    name = match.participant2.display_name
                    if len(name) > 15:
                        name = name[:12] + "..."
                    draw.text((int(x + AVATAR_SIZE + 15), int(y + MATCH_HEIGHT - 25)), name, fill=(0, 0, 0), font=name_font)
                    
                    # Indicate winner
                    if match.winner and match.winner.user_id == match.participant2.user_id:
                        draw.polygon([(int(x + 5), int(y + MATCH_HEIGHT - 15)), (int(x + 15), int(y + MATCH_HEIGHT - 15)), 
                                    (int(x + 10), int(y + MATCH_HEIGHT - 5))], fill=(0, 200, 0))
                
                # Draw match ID
                draw.text((int(x + MATCH_WIDTH - 20), int(y + MATCH_HEIGHT - 15)), f"#{match.match_id}", 
                          fill=(150, 150, 150), font=name_font)
                
                # Draw connector to next match if not in final round
                if match.next_match_id and round_num < num_rounds:
                    next_match = tournament.matches[match.next_match_id]
                    next_matches = matches_by_round.get(round_num + 1, [])
                    next_match_index = next(i for i, m in enumerate(next_matches) if m.match_id == next_match.match_id)
                    
                    next_x = x + MATCH_WIDTH + ROUND_SPACING
                    next_total_height = len(next_matches) * MATCH_HEIGHT + (len(next_matches) - 1) * MATCH_SPACING
                    next_first_y = (image_height - next_total_height) / 2
                    next_y = next_first_y + next_match_index * (MATCH_HEIGHT + MATCH_SPACING)
                    
                    # Draw horizontal line from match to middle
                    mid_x = x + MATCH_WIDTH + ROUND_SPACING/2
                    connector_color = (100, 100, 100)
                    
                    # For top matches, connect from bottom
                    if match.position % 2 == 1:
                        mid_y = y + MATCH_HEIGHT/2
                        end_y = next_y + MATCH_HEIGHT/4
                        draw.line([(int(x + MATCH_WIDTH), int(mid_y)), (int(mid_x), int(mid_y)), 
                                  (int(mid_x), int(end_y)), (int(next_x), int(end_y))], 
                                 fill=connector_color, width=CONNECTOR_WIDTH)
                    # For bottom matches, connect from top
                    else:
                        mid_y = y + MATCH_HEIGHT/2
                        end_y = next_y + 3*MATCH_HEIGHT/4
                        draw.line([(int(x + MATCH_WIDTH), int(mid_y)), (int(mid_x), int(mid_y)), 
                                  (int(mid_x), int(end_y)), (int(next_x), int(end_y))], 
                                 fill=connector_color, width=CONNECTOR_WIDTH)
    
    # Save image to BytesIO
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    
    return output

def get_tournament(guild_id: int, tournament_name: str) -> Optional[Tournament]:
    """Get a tournament by guild ID and name."""
    if guild_id not in active_tournaments:
        return None
    return active_tournaments[guild_id].get(tournament_name)

def create_tournament(guild_id: int, tournament_name: str, size: int, creator_id: int) -> Tuple[bool, str]:
    """Create a new tournament."""
    # Initialize guild tournaments dictionary if needed
    if guild_id not in active_tournaments:
        active_tournaments[guild_id] = {}
    
    # Check if tournament with this name already exists
    if tournament_name in active_tournaments[guild_id]:
        return False, "A tournament with this name already exists."
    
    # Validate tournament size
    if size < 2:
        return False, "Tournament size must be at least 2."
    if size > 64:
        return False, "Tournament size cannot exceed 64."
    
    # Create tournament
    tournament = Tournament(tournament_name, size, creator_id)
    active_tournaments[guild_id][tournament_name] = tournament
    
    # Save tournaments to file
    save_tournaments()
    
    return True, "Tournament created successfully."

def list_tournaments(guild_id: int) -> List[Tournament]:
    """List all active tournaments in a guild."""
    if guild_id not in active_tournaments:
        return []
    return list(active_tournaments[guild_id].values())

def delete_tournament(guild_id: int, tournament_name: str) -> bool:
    """Delete a tournament."""
    if guild_id not in active_tournaments:
        return False
    
    if tournament_name not in active_tournaments[guild_id]:
        return False
    
    del active_tournaments[guild_id][tournament_name]
    
    # Save tournaments to file
    save_tournaments()
    
    return True

async def tournament_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function that returns available tournaments in the guild"""
    guild_id = interaction.guild_id
    
    if guild_id not in active_tournaments:
        return []
    
    tournaments = list(active_tournaments[guild_id].keys())
    return [
        app_commands.Choice(name=name, value=name)
        for name in tournaments if current.lower() in name.lower()
    ][:25]  # Discord limits to 25 choices

# Load tournaments when module is imported
load_tournaments()
