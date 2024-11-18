import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, Bot, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import discord
from discord.ext import commands
import logging
import nest_asyncio

# Allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))
DISCORD_SERVER_ID = int(os.getenv("DISCORD_SERVER_ID"))

# Load topics from environment variables
TOPICS = eval(os.getenv("TOPICS", "[]"))  # Example: [["Test 2", "220"], ["Test 1", "219"]]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)

# Initialize Telegram bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix="!", intents=intents)

# Temporary directory to store media
TEMP_DIR = "./temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# Cache for mapping topic IDs to Discord channels
topic_cache = {int(topic[1]): topic[0] for topic in TOPICS}
discord_channel_cache = {}


async def log_discord_channels():
    """
    Log all existing channels and categories in the Discord server.
    """
    guild = discord.utils.get(discord_bot.guilds, id=DISCORD_SERVER_ID)
    if not guild:
        logger.error("[Discord] Guild not found!")
        return

    logger.info("[Discord] Current channels and categories in the server:")
    for category in guild.categories:
        logger.info(f"[Discord] Category: {category.name}, ID: {category.id}")
    for channel in guild.text_channels:
        logger.info(f"[Discord] Channel: {channel.name}, ID: {channel.id}")


async def sync_discord_channels():
    """
    Sync Discord channels with Telegram topics, including creating a General channel.
    """
    guild = discord.utils.get(discord_bot.guilds, id=DISCORD_SERVER_ID)
    if not guild:
        logger.error("[Discord] Guild not found!")
        return

    # Initialize cache with existing Discord channels
    existing_channels = {channel.name: channel.id for channel in guild.text_channels}

    # Create or find General channel
    if "general" not in existing_channels:
        channel = await guild.create_text_channel(name="general")
        discord_channel_cache[0] = channel.id  # Use 0 as key for General channel
        logger.info(f"[Discord] Created General channel: general (ID: {channel.id})")
    else:
        discord_channel_cache[0] = existing_channels["general"]
        logger.info(f"[Discord] Found existing General channel: general (ID: {existing_channels['general']})")

    # Sync other channels with topics
    for topic_id, topic_name in topic_cache.items():
        if topic_name in existing_channels:
            discord_channel_cache[topic_id] = existing_channels[topic_name]
            logger.info(f"[Discord] Found existing channel: {topic_name} (ID: {existing_channels[topic_name]})")
        else:
            channel = await guild.create_text_channel(name=topic_name)
            discord_channel_cache[topic_id] = channel.id
            logger.info(f"[Discord] Created new channel: {topic_name} (ID: {channel.id})")


# Telegram → Discord
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message:
            username = update.message.from_user.full_name
            if update.message.from_user.username:
                username += f" (@{update.message.from_user.username})"

            topic_id = update.message.message_thread_id if update.message.is_topic_message else 0
            discord_channel_id = discord_channel_cache.get(topic_id)

            logger.info(f"[Telegram → Discord] Message from {username} in topic ID {topic_id}: {update.message.text or 'Attachment'}")

            if discord_channel_id:
                channel = discord_bot.get_channel(discord_channel_id)
                if channel:
                    if update.message.text:
                        await channel.send(f"**{username}** From Telegram: \n  {update.message.text}")
                    elif update.message.voice:
                        # Handle voice messages
                        file = await telegram_bot.get_file(update.message.voice.file_id)
                        file_path = os.path.join(TEMP_DIR, "voice.ogg")
                        await file.download_to_drive(file_path)
                        await channel.send(file=discord.File(file_path), content=f"**{username}** sent a voice message.")
                        os.remove(file_path)
                    elif update.message.photo or update.message.document:
                        file_id = (
                            update.message.photo[-1].file_id
                            if update.message.photo
                            else update.message.document.file_id
                        )
                        try:
                            file = await telegram_bot.get_file(file_id)
                            file_path = os.path.join(TEMP_DIR, os.path.basename(file.file_path))
                            await file.download_to_drive(file_path)
                            with open(file_path, "rb") as f:
                                await channel.send(
                                    content=f"**{username}** From Telegram sent a media:", file=discord.File(f)
                                )
                            os.remove(file_path)
                        except Exception as file_error:
                            logger.error(f"[Telegram → Discord] Error downloading/sending file: {file_error}")
                            await channel.send(f"**{username}** tried to send a file, but it was too large or inaccessible.")
    except Exception as e:
        logger.error(f"[Telegram → Discord] Error: {e}", exc_info=True)


# Discord → Telegram
@discord_bot.event
async def on_message(message):
    try:
        if message.author == discord_bot.user:
            return

        topic_id = next((tid for tid, cid in discord_channel_cache.items() if cid == message.channel.id), 0)
        logger.info(f"[Discord → Telegram] Message from {message.author.display_name} in channel {message.channel.name}: {message.content or 'Attachment'}")

        if topic_id is not None:
            if message.attachments:
                for attachment in message.attachments:
                    file_path = os.path.join(TEMP_DIR, attachment.filename)
                    await attachment.save(file_path)
                    logger.info(f"[Discord → Telegram] Saved attachment: {file_path}")
                    with open(file_path, "rb") as f:
                        await telegram_bot.send_document(
                            chat_id=TELEGRAM_GROUP_ID,
                            document=InputFile(f),
                            caption=f"**{message.author.display_name}** sent this from Discord",
                            message_thread_id=topic_id if topic_id != 0 else None,
                        )
                    logger.info(f"[Discord → Telegram] Sent attachment to Telegram: {file_path}")
                    os.remove(file_path)

            if message.content:
                await telegram_bot.send_message(
                    chat_id=TELEGRAM_GROUP_ID,
                    text=f"{message.author.display_name} From Discord: \n {message.content}",
                    message_thread_id=topic_id if topic_id != 0 else None,
                )
                logger.info(f"[Discord → Telegram] Sent text message to Telegram: {message.content}")
    except Exception as e:
        logger.error(f"[Discord → Telegram] Error: {e}", exc_info=True)

async def fetch_previous_telegram_messages():
    """
    Fetch and forward previous Telegram messages to Discord using get_updates.
    """
    logger.info("[Telegram] Fetching previous messages using `get_updates`...")
    try:
        # Fetch recent updates from Telegram
        updates = await telegram_bot.get_updates()
        logger.info(f"[Telegram] Fetched {len(updates)} updates.")

        # Process each update
        for update in updates:
            if update.message:
                logger.info(f"[Telegram] Processing message: {update.message.text or 'Media/Attachment'}")
                await handle_telegram_message(update, None)

    except Exception as e:
        logger.error(f"[Telegram] Error fetching previous messages: {e}", exc_info=True)


@discord_bot.event
async def on_ready():
    logger.info(f"[Discord] Logged in as {discord_bot.user}")
    await log_discord_channels()
    await sync_discord_channels()

    await fetch_previous_telegram_messages()


async def start_telegram_bot():
    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_telegram_message))

    logger.info("[Telegram] Starting Telegram bot...")
    await telegram_app.initialize()
    await telegram_app.start()
    return telegram_app


async def start_discord_bot():
    logger.info("[Discord] Starting Discord bot...")
    await discord_bot.start(DISCORD_BOT_TOKEN)


async def main():
    telegram_app = await start_telegram_bot()

    try:
        await asyncio.gather(
            telegram_app.updater.start_polling(),
            start_discord_bot(),
        )
    except Exception as e:
        logger.error(f"[Main] Error: {e}", exc_info=True)
    finally:
        logger.info("[Main] Shutting down bots...")
        await telegram_app.stop()
        await discord_bot.close()


if __name__ == "__main__":
    asyncio.run(main())
