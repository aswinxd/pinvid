import io
import os
import asyncio
import aiohttp
import json
import logging
import shutil
import requests
from pymongo import MongoClient
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from git import Repo, GitCommandError, InvalidGitRepositoryError
from datetime import datetime


SUDOERS = [1137799257]  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6525647702:AAEcBZ4z-nkG161VkOPOQOFsNidoao-jwHw'
MONGO_URI = 'mongodb+srv://bot:bot@cluster0.8vepzds.mongodb.net/?retryWrites=true&w=majority'
DATABASE_NAME = 'Pinterest_bot'
COLLECTION_NAME = 'users'

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=150)  
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
users_collection = db[COLLECTION_NAME]

@app.on_message(filters.command("start") & filters.private)
async def handle_start_command(client, message):
    logger.info(f"Received /start command from {message.from_user.id}")
    
    # Check if the user is already in the database
    user_id = message.from_user.id
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
    
    # Get the user count
    user_count = users_collection.count_documents({})
    
    instructions = (
        "Welcome! This is **Pinterest Downloader Bot**. This bot can download videos from Pinterest.\n"
        "• Send Pinterest video link, and the bot will download it and send it to you.\n"
        "• If you face any issues, please contact the support chat so developers can fix your issue.\n"
        "• We don't recommend adding this bot to groups even though you can add it and use it in groups.\n"
        "• Queue request on bot: {user_count}\n"
    )
    buttons = [
        [
            InlineKeyboardButton("Support Group", url="https://codecarchive.t.me"),
            InlineKeyboardButton("Updates", url="https://codecbots.t.me"),
        ],
        [
            InlineKeyboardButton("Contact Developer", url="https://drxew.t.me")
        ]
    ]
    await message.reply_text(instructions, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command(["update", "gitpull"]) & filters.user(SUDOERS))
async def update_(client, message):
    response = await message.reply_text("Updating the bot...")
    try:
        repo = Repo()
    except GitCommandError:
        return await response.edit("Git command error.")
    except InvalidGitRepositoryError:
        return await response.edit("Invalid Git repository.")
    
    to_exc = "git fetch origin master &> /dev/null"
    os.system(to_exc)
    await asyncio.sleep(7)
    
    verification = ""
    REPO_ = repo.remotes.origin.url.split(".git")[0]
    for checks in repo.iter_commits("HEAD..origin/master"):
        verification = str(checks.count())
    
    if verification == "":
        return await response.edit("No updates available.")
    
    updates = ""
    ordinal = lambda format: "%d%s" % (
        format,
        "tsnrhtdd"[(format // 10 % 10 != 1) * (format % 10 < 4) * format % 10 :: 4],
    )
    
    for info in repo.iter_commits("HEAD..origin/master"):
        updates += f"<b>➣ #{info.count()}: <a href={REPO_}/commit/{info}>{info.summary}</a> by -> {info.author}</b>\n\t\t\t\t<b>➥ Committed on :</b> {ordinal(int(datetime.fromtimestamp(info.committed_date).strftime('%d')))} {datetime.fromtimestamp(info.committed_date).strftime('%b')}, {datetime.fromtimestamp(info.committed_date).strftime('%Y')}\n\n"
    
    update_response = "<b>A new update is available for the bot!</b>\n\n➣ Pushing updates now\n\n<b><u>Updates:</u></b>\n\n"
    final_updates = update_response + updates
    if len(final_updates) > 4096:
        url = "https://anonybin.org"  # Use AnonyBin or any other paste service
        nrs = await response.edit(
            f"<b>A new update is available for the bot!</b>\n\n➣ Pushing updates now\n\n<u><b>Updates :</b></u>\n\n<a href={url}>Check updates</a>"
        )
    else:
        nrs = await response.edit(final_updates, disable_web_page_preview=True)
    
    os.system("git stash &> /dev/null && git pull")
    
    try:
        # Add your logic to restart the bot or notify users about the update
        await response.edit(f"{nrs.text}\n\nBot updated successfully.")
    except Exception as err:
        await response.edit(f"{nrs.text}\n\nUpdate failed: {err}")

@app.on_message(filters.command(["restart"]) & filters.user(SUDOERS))
async def restart_(client, message):
    response = await message.reply_text("Restarting...")
    try:
        shutil.rmtree("downloads")
        shutil.rmtree("raw_files")
        shutil.rmtree("cache")
    except:
        pass
    await response.edit_text(
        "Restart process started, please wait for a few seconds until the bot starts..."
    )
    os.system(f"kill -9 {os.getpid()} && python3 pin.py")

@app.on_message(filters.command("broadcast") & filters.user(SUDOERS))
async def broadcast_message(client, message):
    if message.reply_to_message:
        broadcast_message = message.reply_to_message.text
    else:
        if len(message.command) < 2:
            await message.reply_text("Usage: /broadcast <message>")
            return
        broadcast_message = message.text.split(None, 1)[1]

    all_users = users_collection.find()
    broadcast_count = 0

    for user in all_users:
        try:
            await client.send_message(user['user_id'], broadcast_message)
            broadcast_count += 1
            await asyncio.sleep(0.1)  # To prevent hitting the flood limit
        except FloodWait as e:
            logger.warning(f"Hit FloodWait for {e.x} seconds.")
            await asyncio.sleep(e.x)
        except Exception as e:
            logger.error(f"Error broadcasting to {user['user_id']}: {e}")
    
    await message.reply_text(f"Broadcast completed. Message sent to {broadcast_count} users.")

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


if __name__ == "__main__":
    app.run()
