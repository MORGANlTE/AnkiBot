import discord
from discord import app_commands
from data.ai_manager import ask_question, clear_history
import re

# Command Group
ai_group = app_commands.Group(name="ai", description="Commands related to AI interactions.")

# Discord message character limit
DISCORD_MESSAGE_LIMIT = 2000

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@ai_group.command(name="ask", description="Ask a question to the AI assistant.")
@app_commands.describe(question="The question you want to ask.")
async def ai_ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    
    # Get the response from the AI
    response = await ask_question(question)
    
    # Send the question
    await interaction.followup.send(embed=discord.Embed(
        title="Question", 
        description=question, 
        color=discord.Color.blue()
    ))
    
    # Split response if it exceeds Discord's message limit
    if len(response) <= DISCORD_MESSAGE_LIMIT:
        await interaction.followup.send(content=response)
    else:
        # Split by paragraphs or sentences to make more natural breaks
        # First try to split by paragraphs (double newlines)
        parts = re.split(r'\n\s*\n', response)
        
        current_part = ""
        for part in parts:
            # If adding this part would exceed the limit, send the current part and start a new one
            if len(current_part) + len(part) + 2 > DISCORD_MESSAGE_LIMIT:
                if current_part:
                    await interaction.followup.send(content=current_part)
                    current_part = part
                else:
                    # This single part is too long, need to split it further
                    sentences = re.split(r'(?<=[.!?])\s+', part)
                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 1 > DISCORD_MESSAGE_LIMIT:
                            if current_part:
                                await interaction.followup.send(content=current_part)
                                current_part = sentence
                            else:
                                # Even a single sentence is too long, just split by character limit
                                for i in range(0, len(sentence), DISCORD_MESSAGE_LIMIT):
                                    chunk = sentence[i:i + DISCORD_MESSAGE_LIMIT]
                                    await interaction.followup.send(content=chunk)
                        else:
                            current_part += " " + sentence if current_part else sentence
            else:
                current_part += "\n\n" + part if current_part else part
        
        # Send any remaining content
        if current_part:
            await interaction.followup.send(content=current_part)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@ai_group.command(name="reset", description="Reset the AI conversation history.")
async def ai_reset(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Clear the AI conversation history
    success = await clear_history()
    
    if success:
        await interaction.followup.send("AI conversation history has been reset.", ephemeral=True)
    else:
        await interaction.followup.send("Failed to reset AI conversation history.", ephemeral=True)

async def handle_ai_message(message):
    """Handle AI interactions in designated chat channels"""
    # Ignore messages from bots
    if message.author.bot:
        return
    
    # Get response from AI
    try:
        # Send typing indicator while waiting for response
        async with message.channel.typing():
            response = await ask_question(message.content)
            
            # Split response if it exceeds Discord's message limit
            if len(response) <= DISCORD_MESSAGE_LIMIT:
                await message.channel.send(content=response)
            else:
                # Split by paragraphs or sentences to make more natural breaks
                parts = re.split(r'\n\s*\n', response)
                
                current_part = ""
                for part in parts:
                    # If adding this part would exceed the limit, send the current part and start a new one
                    if len(current_part) + len(part) + 2 > DISCORD_MESSAGE_LIMIT:
                        if current_part:
                            await message.channel.send(content=current_part)
                            current_part = part
                        else:
                            # This single part is too long, need to split it further
                            sentences = re.split(r'(?<=[.!?])\s+', part)
                            for sentence in sentences:
                                if len(current_part) + len(sentence) + 1 > DISCORD_MESSAGE_LIMIT:
                                    if current_part:
                                        await message.channel.send(content=current_part)
                                        current_part = sentence
                                    else:
                                        # Even a single sentence is too long, just split by character limit
                                        for i in range(0, len(sentence), DISCORD_MESSAGE_LIMIT):
                                            chunk = sentence[i:i + DISCORD_MESSAGE_LIMIT]
                                            await message.channel.send(content=chunk)
                                else:
                                    current_part += " " + sentence if current_part else sentence
                    else:
                        current_part += "\n\n" + part if current_part else part
                
                # Send any remaining content
                if current_part:
                    await message.channel.send(content=current_part)
    except Exception as e:
        print(f"Error in AI response: {str(e)}")
        await message.channel.send("I encountered an error while processing your message.")

def setup(tree: app_commands.CommandTree):
    tree.add_command(ai_group)
