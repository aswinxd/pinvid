import io
import os
import asyncio
import aiohttp
import json
import logging
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6055798094:AAEAGxwAP55aB-jO5sq0FDCFzOSQdNnYMqQ'

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=100)  

def expand_shortened_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        final_url = response.url
        logger.info(f"Expanded URL: {final_url}")
        return final_url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url

def get_pinterest_video_url(pin_url):
    try:
        response = requests.get(pin_url, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info(f"Response content: {soup.prettify()[:2000]}") 
        for script in soup.find_all('script', type='application/ld+json'):
            json_data = json.loads(script.string)
            logger.info(f"Found JSON-LD script: {json.dumps(json_data, indent=2)[:1000]}")
            if '@type' in json_data and json_data['@type'] == 'VideoObject':
                video_url = json_data['contentUrl']
                logger.info(f"Found video URL: {video_url}")
                return video_url
        
    except Exception as e:
        logger.error(f"Error getting Pinterest video URL: {e}")
    
    logger.warning("No video URL found.")
    return None

async def fetch_video(session, url):
    async with session.get(url) as response:
        return await response.read()
        

async def download_and_send_video(client, message, url):
    try:
        video_url = await asyncio.get_event_loop().run_in_executor(executor, get_pinterest_video_url, url)
        if not video_url:
            await message.reply_text("Could not find a video at the provided link.")
            return
        
        async with aiohttp.ClientSession() as session:
            video_data = await fetch_video(session, video_url)
        
        video_io = io.BytesIO(video_data)
        
        await client.send_video(
            chat_id=message.chat.id,
            video=video_io,
            file_name="video.mp4",  
            caption="Here is your video!"
        )
        
    except Exception as e:
        logger.error(f"Error in download_and_send_video: {e}")
        await message.reply_text("An error occurred while processing your request.")
    finally:
        await asyncio.sleep(0.1)

@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    url = message.text
    if "pinterest.com" in url or "pin.it" in url:
        try:
            if "pin.it" in url:
                url = await asyncio.get_event_loop().run_in_executor(executor, expand_shortened_url, url)
            
            asyncio.create_task(download_and_send_video(client, message, url))
        except FloodWait as e:
            logger.warning(f"FloodWait error: Waiting for {e.x} seconds")
            await asyncio.sleep(e.x)
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            await message.reply_text("An error occurred while processing your request.")
    else:
        await message.reply_text("Please provide a valid Pinterest video link.")
        async def handle_start_command(event):
    instructions = (
        "Welcome! This is AntiBioLink. Here are some commands you can use:\n"
        "/add <user_id> - Add a user ID to the whitelist\n"
        "/removeuser <user_id> - Remove a user ID from the whitelist\n"
        "/start - Show this help message\n"
        "\n"
        "Features:\n"
        "1. Automatically checks new users' bios for links and kicks them if a link is found.\n"
        "2. Caches user bio checks to avoid repetitive checks within an hour.\n"
        "3. Handles messages in batches to optimize performance and reduce load.\n"
        "4. Sends notifications to users when they are kicked due to having links in their bio.\n"
        "~**ADD TO YOUR GROUP AND PROMOTE AS ADMIN WITH BAN PERMISSION.**\n"
    )
    buttons = [
        [types.KeyboardButtonUrl("Support", "https://xenonsupportchat.t.me"), types.KeyboardButtonUrl("Updates", "https://xenonbots.t.me")]
    ]
    await event.respond(instructions, buttons=buttons)

if __name__ == "__main__":
    app.run()
