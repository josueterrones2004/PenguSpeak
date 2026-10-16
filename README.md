<div align="center">

# 🐧 PenguSpeak

**A Spanish-first Discord TTS bot focused on low latency, natural voice playback and reliable real-time sessions.**

[![Version](https://img.shields.io/badge/version-1.3.0-5865F2?style=flat-square)](https://github.com/josueterrones2004/PenguSpeak/releases/tag/v1.3.0)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.7.1-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Edge TTS](https://img.shields.io/badge/Edge_TTS-primary-0078D7?style=flat-square)](https://github.com/rany2/edge-tts)
[![Azure Speech](https://img.shields.io/badge/Azure_Speech-fallback-0089D6?style=flat-square&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/products/ai-services/ai-speech)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)

**[🌐 Official website](https://josueterrones2004.github.io/PenguSpeak-Web/)** · **[📦 Releases](https://github.com/josueterrones2004/PenguSpeak/releases)** · **[📝 Changelog](CHANGELOG.md)**

</div>

---

PenguSpeak is a **Text-to-Speech bot for Discord** written in Python. It is built for people who want to hear chat messages while playing, talking with friends or simply without constantly looking at a text channel.

Each user can choose their own voice and spoken nickname. PenguSpeak keeps independent queues per server, processes messages contextually and streams audio progressively to reduce the delay between a message being sent and speech beginning.

> **Current stable version:** `1.3.0`
>
> **Language:** PenguSpeak is intentionally built for **Spanish**. Its voice catalog, spoken output and user-facing TTS experience are centered around Spanish, and there are currently **no plans to add English voices**.

## ✨ What it includes

- 🔊 Continuous TTS with `/tts iniciar` and `/tts detener`.
- 💬 Manual playback with `/tts decir`.
- 🎙️ **22 Spanish voices** from different countries and regions.
- 👤 Per-user voice preferences.
- 🏷️ Custom spoken nicknames.
- ⚙️ Interactive configuration panel with `/tts configurar`.
- 💾 Persistent preferences stored with SQLite.
- 🧠 Context-aware handling of messages, replies, mentions and media.
- 😄 Unicode and custom Discord emoji support.
- 🎟️ Sticker name reading.
- 🖼️ Image detection.
- 🎥 Video detection.
- 🔗 Link detection.
- 📎 Attachment detection.
- 📚 Independent queue per Discord server.
- ⚡ Progressive audio playback and next-message prefetching.
- ⏭️ Users can skip only their own queued messages.
- 🔄 Automatic voice reconnection when a valid session is still active.
- 🔒 Session protection to avoid silently moving an active session to another voice channel.
- 🔇 Voice connections use `self_deaf=True`; PenguSpeak does not need to listen to channel audio.
- 💤 Automatic session and inactivity management.
- 🛟 Automatic failover between Edge TTS and Azure Speech when needed.
- 📱 Runs on Linux and can also be used on Android through Termux with a compatible environment.

---

## 🇪🇸 Spanish by design

PenguSpeak is not intended to be a general-purpose multilingual TTS bot.

The project is specifically focused on Spanish-speaking Discord communities. Its available voices, default behavior, spoken phrases and commands are designed around Spanish usage.

The current voice catalog contains **22 Spanish voices**, and English voices are not part of the project roadmap at this time.

The README and project documentation are written in English so the codebase is easier to understand and evaluate internationally, but the bot itself remains Spanish-focused.

---

## 🔊 Two ways to use TTS

### Continuous TTS

With `/tts iniciar`, PenguSpeak starts reading the messages written by that user while they remain in the voice channel associated with the current session.

```text
/tts iniciar
```

To stop automatic reading:

```text
/tts detener
```

Continuous TTS is per-user. Enabling PenguSpeak for one person does not automatically enable it for everyone else in the channel.

### Manual TTS

`/tts decir` plays a one-time message without enabling continuous mode.

```text
/tts decir texto: Hola a todos
```

---

## 🧠 Context-aware message processing

PenguSpeak does more than pass raw text directly to a speech provider. Before synthesis, it builds a spoken sentence that tries to preserve the context of the Discord message.

| Content | Behavior |
| --- | --- |
| 💬 Plain text | Reads the message content. |
| ↩️ Reply | Can mention who the user is replying to. |
| 👤 User mention | Speaks the matching username or configured nickname. |
| 🏷️ Role mention | Identifies the mentioned role. |
| 📣 `@everyone` / `@here` | Recognizes the mention when Discord marks it as a real mention. |
| 🖼️ Image | Announces that the user sent an image. |
| 🎥 Video | Announces that the user sent a video. |
| 🔗 Link | Announces that a link was sent without reading the full URL. |
| 📎 File | Announces that a file was sent. |
| 🎟️ Sticker | Uses the sticker name when available. |
| 😄 Unicode emoji | Converts the emoji into a speakable name. |
| 🎨 Custom emoji | Humanizes the custom Discord emoji name. |

For example, a message containing both text and an image can become something similar to:

```text
Yarin envió una imagen y dice: mira esto
```

If the message is a reply or contains mentions, PenguSpeak adds that context when appropriate.

### 😄 Emojis

Unicode emojis are converted into names that can be pronounced naturally by the TTS system. Custom Discord emojis use their emoji name as a base.

```text
<:penguDance:123456789>
→ pengu Dance
```

The project also keeps a small easter egg:

```text
👀 → ojitos void
```

### 🎟️ Stickers

When a Discord message contains a sticker with an available name, PenguSpeak can announce it in speech.

```text
sticker Gato feliz
```

### 🖼️ Images, videos, links and files

PenguSpeak detects common attachment types and includes that information in the spoken sentence instead of reading long URLs or awkward file names.

Examples:

```text
Yarin envió una imagen
Yarin envió un video y dice: mira esto
Yarin envió un enlace
Yarin envió un archivo
```

---

## 🎙️ Spanish voices

PenguSpeak includes **22 Spanish voices** and lets each user select a personal preference directly from Discord. When an equivalent voice exists in both providers, the preference is preserved when switching between Edge TTS and Azure Speech.

The default voice is **🇲🇽 Jorge · Mexico**.

### 👨 Male voices

| Voice | Region |
| --- | --- |
| 🇲🇽 Jorge | Mexico |
| 🇪🇸 Álvaro | Spain |
| 🇦🇷 Tomas | Argentina |
| 🇧🇴 Marcelo | Bolivia |
| 🇨🇱 Lorenzo | Chile |
| 🇨🇷 Juan | Costa Rica |
| 🇨🇺 Manuel | Cuba |
| 🇩🇴 Emilio | Dominican Republic |
| 🇬🇹 Andres | Guatemala |
| 🇳🇮 Federico | Nicaragua |
| 🇵🇦 Roberto | Panama |
| 🇵🇪 Alex | Peru |
| 🇵🇷 Victor | Puerto Rico |

### 👩 Female voices

| Voice | Region |
| --- | --- |
| 🇲🇽 Dalia | Mexico |
| 🇧🇴 Sofia | Bolivia |
| 🇨🇱 Catalina | Chile |
| 🇩🇴 Ramona | Dominican Republic |
| 🇬🇹 Marta | Guatemala |
| 🇭🇳 Karla | Honduras |
| 🇳🇮 Yolanda | Nicaragua |
| 🇵🇦 Margarita | Panama |
| 🇵🇪 Camila | Peru |

Voices can be explored through `/voces hombres`, `/voces mujeres` or directly from `/tts configurar`. When demo files are available, the voice browser can attach them so users can listen before choosing.

---

## ⚙️ Configuration panel

`/tts configurar` opens a private interactive panel so users can customize PenguSpeak without remembering every command.

From there, users can:

- 🎙️ Browse male voices.
- 🎙️ Browse female voices.
- ✏️ Edit their spoken nickname.
- 🗑️ Remove their nickname.
- 🔄 Reset their voice or all stored preferences.
- 🔃 Refresh the state shown by the panel.

The panel controls can only be used by the user who opened it.

---

## 🏷️ Spoken nicknames

PenguSpeak lets users configure an alternate name for TTS output.

```text
/apodo poner apodo: Yarin
```

The nickname can also be checked or removed:

```text
/apodo actual
/apodo quitar
```

Nicknames accept letters, numbers and spaces. Special symbols are rejected to keep pronunciation predictable.

---

## ⚡ Queues, streaming and low latency

Each Discord server gets its own queue, preventing activity in one server from interfering with playback in another.

PenguSpeak prepares audio while managing the queue and can begin preparing the next message before its turn arrives. The goal is to reduce noticeable pauses between consecutive messages.

The system also tracks the current item, cancelled items and pending streams so it can react to skips, disconnects and state changes without unnecessarily clearing the entire session.

### Progressive playback

Audio is streamed progressively instead of waiting for the complete TTS result before playback begins.

A thread-safe buffer sits between asynchronous TTS generation and FFmpeg playback, allowing Discord audio to begin while more compressed audio is still arriving from the active speech provider.

### Prefetching

The queue worker can prepare upcoming TTS streams ahead of playback. This reduces the delay between consecutive messages when a session is active and several messages are waiting.

### ⏭️ Skipping messages

`/tts saltar` is limited to the requesting user's own messages.

If the currently playing message belongs to that user, PenguSpeak can stop it. Otherwise, it looks for that user's next pending item in the queue.

Messages belonging to other users are not removed.

---

## 🛟 Edge TTS + Azure Speech failover

**Edge TTS** is PenguSpeak's primary speech engine.

If Edge becomes unavailable and Azure credentials are configured, **Azure Speech** automatically takes over as a fallback provider. While Azure is active, PenguSpeak periodically checks whether Edge has recovered and switches back when the primary engine becomes available again.

When a TTS session is active, PenguSpeak can notify Discord users about provider changes and recovery so unexpected latency or voice differences have some context.

```text
Edge TTS
   │
   ├── available ───────────────→ normal TTS
   │
   └── error
        ↓
    Azure Speech
        │
        └── periodic recovery checks → back to Edge
```

Azure Speech is optional and requires your own credentials.

---

## 🔒 Voice sessions

PenguSpeak keeps each active TTS session associated with the voice channel where it started.

- An active session cannot be silently moved to another voice channel.
- Messages are only read while the user remains in the session's voice channel.
- If an active user leaves that channel, their TTS is disabled and their pending items are removed.
- When the last active TTS user leaves, PenguSpeak clears the queue and disconnects.
- The bot connects with `self_deaf=True` because it only needs to play audio, not listen to users.
- If Discord interrupts the connection while the session is still valid, PenguSpeak can attempt to reconnect to the original channel.

---

## 🎙️ Commands

The bot's command names remain in Spanish because PenguSpeak itself is designed for Spanish-speaking users.

| Command | Purpose |
| --- | --- |
| `/tts iniciar` | Enables automatic reading for the user. |
| `/tts detener` | Disables automatic reading and clears the user's pending messages. |
| `/tts decir` | Plays a one-time TTS message. |
| `/tts saltar` | Skips the current or next queued message belonging to the user. |
| `/tts configurar` | Opens the interactive voice and nickname configuration panel. |
| `/voz actual` | Shows the currently selected voice. |
| `/voces hombres` | Opens the male voice browser. |
| `/voces mujeres` | Opens the female voice browser. |
| `/apodo poner` | Creates or changes the spoken nickname. |
| `/apodo quitar` | Removes the custom nickname. |
| `/apodo actual` | Shows the current nickname. |

Slash commands are synchronized automatically when the bot starts.

---

## 📋 Requirements

PenguSpeak requires:

- Python.
- FFmpeg.
- A Discord application with **Message Content Intent** enabled.
- Permissions to view and send messages, use application commands, connect to voice channels and speak.

### Arch Linux / CachyOS

```bash
sudo pacman -S ffmpeg
```

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install ffmpeg
```

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/josueterrones2004/PenguSpeak.git
cd PenguSpeak
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your `.env` file from the example:

```bash
cp .env.example .env
```

Configure your Discord token:

```dotenv
DISCORD_TOKEN=your_discord_token
```

To enable Azure Speech as a fallback, also add:

```dotenv
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=your_region
```

Start PenguSpeak:

```bash
python bot.py
```

Or run it directly through the virtual environment interpreter:

```bash
.venv/bin/python bot.py
```

---

## 🤖 Discord setup

In the **Discord Developer Portal**, enable:

- **Message Content Intent**.

Make sure the bot can also:

- View the required channels.
- Send messages.
- Use application commands.
- Connect to voice channels.
- Speak in voice channels.

PenguSpeak uses Discord voice state information to determine whether a user is still part of the active TTS session.

---

## 📱 Android / Termux

PenguSpeak can also run on Android through Termux and a compatible Linux environment.

An existing installation can be kept up to date with:

```bash
git pull
pip install -r requirements.txt
```

Tools such as `tmux` can be used inside the environment to keep the process running.

---

## 📁 Project structure

```text
PenguSpeak/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
├── LICENSE
├── demos/
│   ├── male/
│   └── female/
└── penguspeak/
    ├── __init__.py
    ├── audio.py
    ├── database.py
    ├── queue.py
    ├── state.py
    ├── text.py
    ├── views.py
    └── voices.py
```

### Main components

- `bot.py` — Discord events, slash commands and voice session coordination.
- `audio.py` — TTS providers, progressive streaming, FFmpeg and Edge/Azure failover.
- `database.py` — persistent voice and nickname preferences using SQLite.
- `queue.py` — per-server queues, prefetching, playback and cancellation.
- `state.py` — session state, active users and inactivity management.
- `text.py` — context-aware processing for messages, emojis, mentions and attachments.
- `views.py` — configuration panel, selectors and voice browser.
- `voices.py` — Edge/Azure voice catalog and cross-provider mappings.

---

## 🔐 Security

The Discord bot token and Azure credentials must stay outside the repository.

Do not publish:

- `.env`
- Discord tokens
- Azure keys
- SQLite databases containing user preferences
- private log files

The project's `.gitignore` already excludes `.env` files, local databases and common log files.

---

## 🔄 Updating PenguSpeak

For an existing installation:

```bash
git pull
pip install -r requirements.txt
```

Then restart the bot normally.

---

## 🌐 Official website

PenguSpeak has its own website with project information:

**https://josueterrones2004.github.io/PenguSpeak-Web/**

The website lives in a separate repository: [PenguSpeak-Web](https://github.com/josueterrones2004/PenguSpeak-Web).

---

## 📦 Version

Current stable version:

**PenguSpeak v1.3.0**

See [CHANGELOG.md](CHANGELOG.md) for version history and [Releases](https://github.com/josueterrones2004/PenguSpeak/releases) for published versions.

---

## 📜 License

PenguSpeak is available under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

🐧 **PenguSpeak**

Built with Python, discord.py, Edge TTS, Azure Speech and FFmpeg.

</div>
