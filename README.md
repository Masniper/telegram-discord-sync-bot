# Telegram to Discord Sync Bot

This bot synchronizes messages and media between a Telegram group (or topics) and Discord channels.

## Features
- Two-way message and media synchronization:
  - **Telegram → Discord**
  - **Discord → Telegram**
- Automatic creation and syncing of Discord channels based on Telegram topics.
- Supports:
  - Text
  - Voice messages
  - Images
  - Documents
- Logs all interactions for debugging.

## Prerequisites
1. **Python 3.8+** installed (recommended: Python 3.12 for the latest features and performance).
2. **Telegram Bot Token** and **Group ID** (obtained via [BotFather](https://t.me/BotFather)).
3. **Discord Bot Token** and **Server ID** (set up in the [Discord Developer Portal](https://discord.com/developers/applications)).
4. **Docker** (optional for containerized deployment).

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository_url>
cd telegram-discord-sync-bot
```

### 2. Set Up Environment Variables
Create a `.env` file in the root directory with the following contents:
```env
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN"
TELEGRAM_GROUP_ID=YOUR_TELEGRAM_GROUP_ID
DISCORD_SERVER_ID=YOUR_DISCORD_SERVER_ID
TOPICS=[["Topic1", "TopicID1"], ["Topic2", "TopicID2"]]
```

### 3. Install Dependencies
Install required Python libraries:
```bash
pip install -r requirements.txt
```

### 4. Run the Bot
To start the bot locally:
```bash
python main.py
```

---

## Docker Deployment

### 1. Build Docker Image
```bash
docker build -t telegram-discord-bot .
```

### 2. Run the Docker Container
```bash
docker run -d --env-file .env telegram-discord-bot
```

---

## Notes
- Ensure the Telegram bot is added to the group and has the appropriate permissions.
- Add the Discord bot to the server and grant access to the necessary channels.
- Use logs for debugging any issues:
  - Logs will be output in the console or the Docker container logs.

---

## Example Topics Configuration
The `TOPICS` environment variable maps Telegram topics to Discord channels. Example:
```json
[["General", "0"], ["Updates", "101"], ["Support", "102"]]
```

This ensures each topic in Telegram corresponds to a channel in Discord.

---

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
