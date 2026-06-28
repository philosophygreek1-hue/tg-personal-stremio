# 📹 Personal Video Stremio Server

A personal video library addon for Stremio, powered by **Telegram storage**, **FastAPI**, and **MongoDB**.

Based on the architecture of [weebzone/Telegram-Stremio](https://github.com/weebzone/Telegram-Stremio), adapted for personal video collections instead of movies/TV shows.

---

## What's Different from the Original

| Feature | Original | This Project |
|---------|----------|-------------|
| Content type | Movies & TV shows | Your own videos |
| Metadata | TMDB / IMDB | Your own titles |
| Organization | Genres | Folders you create |
| Naming | Auto from caption | You choose the name |
| Search | Movie title search | Your video title search |

---

## Setup

### 1. Create a Telegram Bot
Go to [@BotFather](https://t.me/BotFather) → `/newbot` → save the token.

### 2. Create a Private Telegram Channel
- Create a private channel
- Add your bot as **Admin**
- Get the channel ID from `web.telegram.org` URL

### 3. MongoDB
Use the same MongoDB Atlas cluster from your movie addon.
Just use a different database name (`personal_videos` is used automatically).

A single URI is enough:
```
mongodb+srv://user:pass@cluster.mongodb.net/
```

### 4. Configure
Copy `sample_config.env` to `config.env` and fill in:

```env
API_ID=
API_HASH=
BOT_TOKEN=
OWNER_ID=
AUTH_CHANNEL=      # your new private channel ID
DATABASE=          # mongodb+srv://...
BASE_URL=          # https://your-railway-url
PORT=8000
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

### 5. Deploy on Railway
Same as the movie addon — deploy as a **second Railway service** from this repo.

---

## How to Use

### Upload Videos
Send any video file to your private Telegram channel.
The bot will automatically save it to your library with the original filename as the title.

### Organize
Open your admin panel at `https://your-url/admin`:
- **Create folders** (Travel, Work, Family, etc.)
- **Rename videos** to friendly names
- **Move videos** between folders

### Watch in Stremio
Add your addon URL to Stremio:
```
https://your-url/stremio/default/manifest.json
```
*(any token works — no subscription system)*

Stremio will show:
- **📹 All Videos** catalog
- **📁 FolderName** catalog for each folder you create

---

## Admin Panel
`https://your-url/admin` — Login with your ADMIN_USERNAME / ADMIN_PASSWORD

- View all videos
- Rename videos
- Create/rename/delete folders
- Move videos between folders
- Delete videos from library (Telegram file stays intact)
