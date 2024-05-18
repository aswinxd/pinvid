import os
import asyncio
import aiohttp
import logging
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the bot
API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6055798094:AAEAGxwAP55aB-jO5sq0FDCFzOSQdNnYMqQ'

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=100)  # Adjust based on your server's capacity

async def fetch_video(session, url):
    async with session.get(url) as response:
        return await response.read()

def get_pinterest_video_url(pin_url):
    response = requests.get(pin_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Example: Finding video URL in meta tags (actual implementation may vary)
    video_tag = soup.find('meta', property='og:video')
    if video_tag:
        return video_tag.get('content')
    return None

async def download_and_send_video(client, message, url):
    try:
        video_url = await asyncio.get_event_loop().run_in_executor(executor, get_pinterest_video_url, url)
        if not video_url:
            await message.reply_text("Could not find a video at the provided link.")
            return
        
        async with aiohttp.ClientSession() as session:
            video_data = await fetch_video(session, video_url)
        
        video_path = f"{message.message_id}.mp4"
        with open(video_path, 'wb') as file:
            file.write(video_data)
        
        await client.send_video(message.chat.id, video=video_path, caption="Here is your video!")
        
        os.remove(video_path)
    except Exception as e:
        logger.error(f"Error in download_and_send_video: {e}")
        await message.reply_text("An error occurred while processing your request.")
    finally:
        await asyncio.sleep(0.1)  # Short delay to prevent flooding

@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    url = message.text
    if "pinterest.com" in url:
        try:
            asyncio.create_task(download_and_send_video(client, message, url))
        except FloodWait as e:
            logger.warning(f"FloodWait error: Waiting for {e.x} seconds")
            await asyncio.sleep(e.x)
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            await message.reply_text("An error occurred while processing your request.")
    else:
        await message.reply_text("Please provide a valid Pinterest video link.")
@app.on_errors()
async def error_handler(client, message, error):
    if isinstance(error, FloodWait):
        await asyncio.sleep(error.x)
        await client.send_message(message.chat.id, "I'm experiencing high load. Please try again later.")
    else:
        logger.error(f"Unhandled error: {error}")
if __name__ == "__main__":
    app.run()
