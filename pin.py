import os
import asyncio
import aiohttp
import logging
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the bot
API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6055798094:AAEAGxwAP55aB-jO5sq0FDCFzOSQdNnYMqQ'

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=100)  # Adjust based on your server's capacity

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
        
        # Log the response content for debugging
        logger.info(f"Response content: {soup.prettify()[:2000]}")  # Log the first 2000 characters
        
        # Try to find video tag in other places if the above didn't work
        for script in soup.find_all('script'):
            if 'video_url' in script.text:
                logger.info(f"Found potential video script: {script.text[:500]}")
                # Extract the JSON data from the script content
                script_content = script.text
                start_index = script_content.find('{')
                end_index = script_content.rfind('}') + 1
                json_content = script_content[start_index:end_index]
                video_data = json.loads(json_content)
                video_url = video_data.get('video_url', None)
                if video_url:
                    return video_url
                
    except Exception as e:
        logger.error(f"Error getting Pinterest video URL: {e}")
    
    logger.warning("No video URL found.")
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

if __name__ == "__main__":
    app.run()
