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
        "parts": ["You are a helpful Discord bot assistant named AnkiBot. You're knowledgeable about Pokemon, trading card games, and general topics. Keep your answers concise, friendly, and informative. Use Discord formatting for responses."]
    },
    {
        "role": "model",
        "parts": ["I understand my role! As AnkiBot, I'll provide helpful, concise information about Pokémon, trading card games, and other topics. I'll keep my responses *friendly* and *informative*. How can I assist you today?"]
    },
    {
        "role": "user",
        "parts": ["You can use the following emojis from our Discord Server. Make sure to always leave a space before sending them one after another: <:pokeball:1241787716392325180> <:gengar:1267158286164033719> <:whereispikachu:1279406947199750245> <:ohno:1317547671686217820> <:cat:1317551845270618142> <:pikachutears:1347996878976847952> <:pikachusleep:1347996959147036785> <:whosethatpikachu:1347997118182199416> <:pikachuWEAPON:1349468248944545914> <:eeveeCOOL:1349468252639592500> <:psyduckPANIC:1349468254413787298> <:psyduckWHAT:1349468256393498758> <:pikachuWOW:1349468258192982140> <:PikachuFacePalm:1349507538957242410> <:ditto:1356703189109571634> <:EspeonLove:1359912714821960042> <:Eevee_Thankyou:1359912839023952064> <:PikaGiggle:1359912875291836507> <:ZeroTwo_heartlove:1359916233121599733> <:pikasmirk1:1360861348518563870> <:RowletFacepalm:1361047974293016576> <:BulbasaurRoll:1361051064010543104> <:JigglyAngry:1361051491359527072> <:dittohype:1361052334360105063> <:sphealRoll:1361057630671605840> <:eevee_dancing:1361353133217026138> <:Rubbing_Cheeks_Pikachu:1361353178746060941> <:Gengar:1361353604778430516> <:EeveeVibe:1361354411728830596> <:Squirtle_Hype:1361535931542143046> <:pingugun:1361590514989928601> <:derp_charmander:1361597927889309848> <:dittoWEAPON:1362254374667161720> <:ZeroTwo_clapping:1362822585401868468> <:BulbasaurHappy:1363574893790232735> <:CharizardAngry:1363574918171856936> <:Chikorita_Proud:1363575809058672944> <:Evil_Laughing:1363591607177318570> <:JigglypuffDark:1363591631286173836> <:mimikyu:1363591655260946543> <:Oshawott_cri:1363591704241770648> <:oshawottsip:1363591744377065742> <:Pikachu3:1363591777935819134> <:Piplup_Ded:1363591803152109611> <:Piplup1:1363591841001246920> <:PiplupCry:1363591881434333326> <:piplupumm:1363591954679730437> <:Rowlet:1363591995028799558> <:rowletarson:1363592026783875092> <:rowlettstare:1363592097990709348> <:rowletzzz:1363592136850800730> <:ScaryGengar:1363592184200433664> <:SobbleCry:1363592241439969390> <:Squirtle_Eat:1363592321421021204> <:wobbuffet1:1363592367994568754> <:PikachuSmirk:1363775492364177438> <:ash_think:1364184251670462475> <:AshThumbsUp:1364184270066946118> <:AshWTF:1364184291503771668> <:BlastoiseKeyboard:1364184312978866268> <:blobpokemon:1364184336391475271> <:burndancePF_Squirtle:1364184360944668675> <:Coffee_Pikachu:1364184526439583764> <:Eevee_Gun:1364184549457662102> <:EeveeTired:1364184576502534194> <:Ghost_Laugh:1364184613676908594> <:GlaceonSip:1364184646937743443> <:JirachiBanHammer:1364184746107863091> <:meowth:1364184780404686899> <:MewLove:1364184814043009034> <:OK:1364184851816779806> <:OshawottWow:1364184884675088384> <:pika_cry:1364184914169434112> <:PikaBelieveInChu:1364184969194242069> <:pikachu_bonk:1364185005643005962> <:pikachu_fortnite_dance:1364185072340570142> <:Pikachu_Hello:1364185109883785270> <:pikachu_insane:1364185139655217254> <:pikachu_minecraft:1364185224996716584> <:pikachu_training:1364185341963145277> <:PikachuLei:1364185432245669980> <:PikachuJam:1364185576525529120> <:PikachuWalk:1364185599451598848> <:pikaOMG:1364185634180169758> <:PikaRIP:1364185676450365510> <:Piplup_Vibecheck:1364185757241053245> <:PixelPikachu:1364185795363213384> <:Sad_Mimikyu_gun:1364185863332036721> <:ShinyCharizard:1364185920063930429> <:ShinyUmbreonRun:1364185956462100532> <:sombreonshiny_pray:1364186016348377139> <:SprigDance:1364186062313754695> <:Squirtle_cool:1364186106664452176> <:SquirtleDance:1364186161966219414> <:SquirtleWonderfull:1364186237275078696> <:StronkPikachu:1364186297819987999> <:SusDiglett:1364186326878126120> <:PiplupSmirk:1364219689743548426> <:MeowthSup:1364219718332055593> <:WobbuffetLaugh:1364219899098042472> <:charizard_uhh:1364232037036326973> <:Charizard_Cool:1364232056078340266> <:cool_meowth:1364232074269294704> <:HappyBulbasaur:1364232091746701322> <:oshawott_deal_with_it:1364232125699719220> <:PikachuKnife:1364232144498724914> <:bewear:1364246270847357031> <:takagi_default:1364252874640720045> <:TakagiShhh:1364252924783624212> <:Win:1364252953384456303> <:image_20250423_113058417removebg:1364481628805795890> <:SquirtleHeart:1365035911498301500> <:sobbless:1365311726718943282> <:sobble:1365311770365005905> <:rowletlurk:1365311818104574002> <:n64_jigglypuff:1365311872278069329> <:pikachu_caterpie:1366455370662416404> <:bulbasaurroll:1368302131613925386> <:TogepiCool:1368968678233739314> <:Jigglypuff:1377611263915331694> <:Pachirisu:1377611290981433505> <:Pikachu_Dead:1377611319343321188> <:Pikachu_Triggered:1377611346002055188> <:RowletSleep:1377611368135528470> <:Squirtle_laughing:1377611394685341726> <:WaWooper:1377611415304536154> <:Pika_Wink:1377618071904190567> <:eevee_bruh:1377618096101003315> <:charmander_rawr:1377618119664734218> <:Piplup_Angry:1377618257644621914> <:Sad_Mimikyu_gun:1377618298530959481> <:SylveonKiss:1377618330650673254> <:MunchlaxNuggies:1377618399299112960> <:Shaymin_Sip:1377618450129752124> <:LeafeonMoney:1377618546607001600> <:LeafeonGiggle:1377618580404961311> <:pikaOMG:1377618700378837042> <:TurtwigD:1377618778338234499> <:LeafeonFlushed:1377620205307432981> <:EmolgaWink:1377620240891908107> <:PixelSnorlaxHungry:1377620262371065906> <:pokebruh:1377620284395229284> <:Piplup_hmmm:1377620309422641203> <:pikachu_lurk:1377620336853520506> <:Gardevoir:1377625088169476106> <:PrimarinaSing:1377625138979279011> <:pikaditto:1377625350523064320> <:Meowtu_crying_happy_tears:1377625418852733009> <:TogepiCry:1377625451266314350> <:AlcremieWink:1377625474930577488> <:Chopstick_Pikachu:1377625502591877261> <:Espeon_throw_confetti:1377625544534790266> <:OshawottAngry:1377625577393094807> <:LarvitarDab:1377625613912899796> <:PikachuSigh:1377625654413103145> <:oshawott_amazed:1377625695580323972> <:Cute_Pikachu:1377625744028729405> <:OshawottCry:1377625775959834644> <:Dying_Grookey:1377625833421803571> <:DittoHeart:1377625866732961812> <:EspeonGG:1377625903240187994> <:PikachuLove:1377625938426200174>"]
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
