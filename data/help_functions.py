import aiohttp
import asyncio

async def fetch_data(session: aiohttp.ClientSession, url: str):
    """Helper function to fetch data from a URL."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None # Not found
            else:
                # Log or handle other HTTP errors if necessary
                print(f"Error fetching {url}: Status {response.status}")
                return "error" # Generic error indicator
    except aiohttp.ClientError as e:
        print(f"AIOHTTP client error fetching {url}: {e}")
        return "error"
    except asyncio.TimeoutError:
        print(f"Timeout error fetching {url}")
        return "error"
    
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/"