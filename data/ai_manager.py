import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional, List
import re

# Load environment variables
load_dotenv()

# Get API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Default models
DEFAULT_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]

# Global variables to store the initialized model and state
_model_initialized = False
_model_instance = None
_selected_model_name = None

# Chat session variables
chat_session = None
files = []

# Default history for chat
default_history = [
    {
        "role": "user",
        "parts": ["You are a helpful Discord bot assistant named AnkiBot. You're knowledgeable about all general topics. Keep your answers concise, friendly, and informative. Use Discord formatting for responses."]
    },
    {
        "role": "model",
        "parts": ["I understand my role! As AnkiBot, I'll provide helpful, concise information about all kinds of topics. I'll keep my responses *friendly* and *informative*. How can I assist you today?"]
    },
    {
        "role": "user",
        "parts": ["You can use the following emojis from our Discord Server. Make sure to always leave a space before sending them one after another: <:eeveeCOOL:1349468252639592500> <:psyduckPANIC:1349468254413787298> <:psyduckWHAT:1349468256393498758> <:EspeonLove:1359912714821960042> <:Eevee_Thankyou:1359912839023952064> <:Chikorita_Proud:1363575809058672944> <:PiplupCry:1363591881434333326> <a:GlaceonSip:1364184646937743443> <:JigglyAngry:1361051491359527072> <:EspeonGG:1377625903240187994>"]
    },
    {
        "role": "model",
        "parts": ["Got it! I can use these emojis in my responses. If you need me to use any of them, just let me know! What would you like to do next?"]
    }
]

def configure_api():
    """Configure the Google Generative AI API"""
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not found in .env file")
        return False
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as e:
        print(f"Error configuring Gemini API: {str(e)}")
        return False

def get_available_models():
    """Fetch available models from Google Generative AI API"""
    try:
        # Configure the API if not already
        configure_api()
        
        # Get available models
        models = []
        for model in genai.list_models():
            # Only include generative models (those that support generateContent)
            if "generateContent" in model.supported_generation_methods:
                models.append(model.name)
        
        print(f"Found {len(models)} available models")
        return models
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        # Return default models if we can't fetch the list
        return DEFAULT_MODELS

def select_best_model(models: List[str]) -> str:
    """Select the best model, preferring ones with 2.5 in the name"""
    # First, look for models with 2.5 in the name
    models_2_5 = [model for model in models if "2.5" in model]
    if models_2_5:
        print(f"Found {len(models_2_5)} models with version 2.5")
        # Prefer flash models for speed if available
        for model in models_2_5:
            if "flash" in model.lower():
                print(f"Selected 2.5 flash model: {model}")
                return model
        # Otherwise return the first 2.5 model
        print(f"Selected 2.5 model: {models_2_5[0]}")
        return models_2_5[0]
    
    # If no 2.5 models, fall back to default preference order
    for model_type in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]:
        for model in models:
            if model_type in model:
                print(f"Selected fallback model: {model}")
                return model
    
    # If nothing matches our preferences, return the first model or a default
    return models[0] if models else "gemini-1.5-flash"

def initialize_model():
    """Initialize the Gemini model (should be called only once)"""
    global _model_initialized, _model_instance, _selected_model_name, chat_session
    
    if _model_initialized:
        return True
    
    if not configure_api():
        return False
    
    try:
        # Get available models
        models = get_available_models()
        
        # Select the best model
        _selected_model_name = select_best_model(models)
        print(f"Initializing AI with model: {_selected_model_name}")
        
        # Initialize Gemini model
        _model_instance = genai.GenerativeModel(_selected_model_name)
        
        # Initialize chat session with default history
        chat_session = _model_instance.start_chat(history=default_history)
        
        _model_initialized = True
        return True
    except Exception as e:
        print(f"Error initializing model: {str(e)}")
        return False

def _generate_description_sync(pokemon_name: str, pokemon_types: list,
                          pokemon_abilities: list, pokemon_id: int) -> Optional[str]:
    """Synchronous function to generate a Pokemon description - runs in a thread"""
    global _model_initialized, _model_instance, _selected_model_name
    
    if not _model_initialized:
        success = initialize_model()
        if not success:
            return None
    
    try:
        # Create the prompt
        prompt = f"""Create an interesting description of the Pokémon {pokemon_name} (Pokédex number {pokemon_id}).
        
        This Pokémon is of type(s): {', '.join(pokemon_types)}.
        It has the following abilities: {', '.join(pokemon_abilities)}.
        
        Write 2-3 sentences describing this Pokémon in a creative and engaging way, but without directly 
        mentioning its name, type, or abilities explicitly, as this will be used in a guessing game.
        
        Don't use obvious clues like "this fire type" or "this water dwelling creature", but instead describe 
        its characteristics, habitat, or behavior indirectly.
        
        Keep your description mysterious but fair, so players can guess without being completely obvious. Make it very short, but write it in a nice poetic way.
        Don't respond with "This Pokémon is a..." or similar phrases, just start describing it directly.
        Avoid using the Pokémon's name in the description.
        You can mention it's type like 'it is in heat for x' to describe it's type. Give a huge hint about how it looks.
        """
        
        # Generate the description using the pre-initialized model
        response = _model_instance.generate_content(prompt)
        description = response.text
        
        # Clean up any potential references to the name
        description = description.replace(pokemon_name, "This Pokémon")
        
        return description
    except Exception as e:
        print(f"Error generating Pokémon description: {str(e)}")
        # If there's an error with the model, reset the initialization flag
        # so we can try to initialize again on the next call
        _model_initialized = False
        return None

async def generate_pokemon_description(pokemon_name: str, pokemon_types: list,
                               pokemon_abilities: list, pokemon_id: int) -> Optional[str]:
    """Generate a creative description for a Pokémon using Google Generative AI
       This runs the API call in a background thread to avoid blocking the main thread"""
    try:
        # Run the synchronous function in a thread pool to avoid blocking
        description = await asyncio.to_thread(
            _generate_description_sync,
            pokemon_name,
            pokemon_types,
            pokemon_abilities,
            pokemon_id
        )
        return description
    except Exception as e:
        print(f"Error in async wrapper for Pokémon description: {str(e)}")
        return None

def _ask_question_sync(author: str, question: str) -> Optional[str]:
    """Synchronous function to ask a question to the AI - runs in a thread"""
    global _model_initialized, chat_session
    
    if not _model_initialized:
        # Assuming initialize_model() sets up the chat_session
        success = initialize_model()
        if not success:
            return "I'm sorry, but I couldn't initialize my AI capabilities at the moment."
    
    try:
        # Construct a clear prompt for the model
        user_prompt = f"User '{author}' asks: {question}"
        
        response = chat_session.send_message(user_prompt)
        
        return response.text
    except Exception as e:
        print(f"Error asking question to AI: {str(e)}")
        # If there's an error with the model, reset the initialization flag
        _model_initialized = False
        return f"I encountered an error while processing your question: {str(e)}"

async def ask_question(author: str, question: str) -> str:
    """Ask a question to the AI and get a response
       This runs the API call in a background thread to avoid blocking the main thread"""
    try:
        # Run the synchronous function in a thread pool to avoid blocking
        response = await asyncio.to_thread(
            _ask_question_sync,
            author,
            question
        )
        return response
    except Exception as e:
        print(f"Error in async wrapper for asking question: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"

async def clear_history():
    """Clear the chat history and reset to default"""
    global chat_session, _model_instance, default_history
    
    if not _model_initialized:
        success = initialize_model()
        if not success:
            return False
    
    try:
        # Reset the chat session with default history
        chat_session = _model_instance.start_chat(history=default_history)
        files.clear()
        return True
    except Exception as e:
        print(f"Error clearing chat history: {str(e)}")
        return False

# Initialize the model when the module is imported
print("Initializing AI manager...")
initialize_model()
