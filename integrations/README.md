# PyMusic Integration System

PyMusic includes an integration system that allows developers to create their own custom integrations without modifying the base code.

## What is an Integration?

An integration is a Python module that can:
- **Get information** from PyMusic (current song, playlist, status, etc.)
- **Send commands** to PyMusic (change song, play playlist, pause, etc.)
- **React to events** when changes occur in PyMusic (new song, playlist change, etc.)

## Creating an Integration

### Step 1: Create the Structure

Create a folder inside `\integrations\` with your integration name:

```
integrations/
  my_integration/
    integration.py  <- Required file
```

### Step 2: Implement `integration.py`

Each integration must have an `integration.py` file with an `initialize()` function:

```python
def initialize(pymusic_api, integration_manager):
    """
    This function is called automatically when PyMusic loads the integration.
    
    Args:
        pymusic_api: API to interact with PyMusic
        integration_manager: Manager to register events
    """
    # Your code here
    pass
```

### Step 3: Use the API

```python
def initialize(pymusic_api, integration_manager):
    # Get information
    song = pymusic_api.song_name
    playlist = pymusic_api.playlist_name
    
    # Send commands
    pymusic_api.next_song()
    pymusic_api.play_playlist("1L")
    
    # Register events
    def on_song_changed(data):
        print(f"New song: {data['song_title']}")
    
    integration_manager.register_event_handler('song_changed', on_song_changed)
```

## PyMusic API

### Properties (Read-Only)

| Property | Type | Description |
|----------|------|-------------|
| `song_name` | `str` | Current song name |
| `song_id` | `str` | Current song ID |
| `song_duration` | `int` | Duration in seconds |
| `playlist_name` | `str` | Current playlist name |
| `is_playing` | `bool` | True if playing |
| `is_paused` | `bool` | True if paused |
| `volume` | `float` | Current volume (0.0 - 3.0) |

### Information Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_playlist_songs()` | `List[str]` | Song IDs in current playlist |
| `get_all_playlists()` | `Dict[str, str]` | All playlists {id: name} |
| `get_all_songs()` | `Dict[str, str]` | All songs {id: title} |

### Control Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `next_song()` | `bool` | Skip to next song |
| `play_playlist(id)` | `bool` | Play a playlist |
| `play_song(id)` | `bool` | Play a specific song |
| `pause()` | `bool` | Pause playback |
| `resume()` | `bool` | Resume playback |
| `stop()` | `bool` | Stop playback |
| `set_volume(vol)` | `bool` | Set volume (0.0 - 3.0) |

## Available Events

You can register handlers for these events:

### `song_changed`
Fires when the song changes.

**Received data:**
```python
{
    'song_id': '123',
    'song_title': 'Song Name',
    'duration': 180  # seconds
}
```

**Example:**
```python
def on_song_changed(data):
    print(f"New song: {data['song_title']}")

integration_manager.register_event_handler('song_changed', on_song_changed)
```

### `playlist_changed`
Fires when the playlist changes.

**Received data:**
```python
{
    'playlist_id': '1L',
    'playlist_name': 'My Playlist'
}
```

### `playback_started`
Fires when playback starts.

**Example:**
```python
def on_started():
    print("Playback started")

integration_manager.register_event_handler('playback_started', on_started)
```

### `playback_stopped`
Fires when playback stops.

### `playback_paused`
Fires when playback is paused.

### `playback_resumed`
Fires when playback resumes.

## Integration Examples

### Example 1: Discord Bot

```python
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!')

def initialize(pymusic_api, integration_manager):
    @bot.command()
    async def now_playing(ctx):
        song = pymusic_api.song_name
        await ctx.send(f"Now playing: {song}")
    
    @bot.command()
    async def next(ctx):
        pymusic_api.next_song()
        await ctx.send("Next song!")
    
    def on_song_changed(data):
        # Send to Discord channel when song changes
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            bot.loop.create_task(channel.send(f"New song: {data['song_title']}"))
    
    integration_manager.register_event_handler('song_changed', on_song_changed)
    bot.run(TOKEN)
```

### Example 2: Twitch Integration

```python
import socket

def initialize(pymusic_api, integration_manager):
    def on_song_changed(data):
        # Send command to Twitch chat
        send_to_twitch(f"!song {data['song_title']}")
    
    integration_manager.register_event_handler('song_changed', on_song_changed)
```

### Example 3: HTTP Webhook

```python
import requests

def initialize(pymusic_api, integration_manager):
    def on_song_changed(data):
        # Send webhook when song changes
        requests.post('https://api.example.com/webhook', json={
            'song': data['song_title'],
            'duration': data['duration']
        })
    
    integration_manager.register_event_handler('song_changed', on_song_changed)
```

## Automatic Detection

PyMusic automatically detects all integrations on startup:

1. Searches all folders in `\integrations\`
2. Checks if they have an `integration.py` file
3. Loads and initializes each integration automatically

**You don't need to modify PyMusic's base code.**

## Important Notes

- ✅ All API operations are **thread-safe**
- ✅ Events fire on PyMusic's main thread
- ⚠️ Avoid blocking operations in event handlers
- ⚠️ If your integration needs to run in the background, use threads
- ✅ You can create additional files in your integration folder

## Troubleshooting

### My integration doesn't load

1. Verify your folder is in `\integrations\`
2. Verify you have an `integration.py` file (not `integration.py.py`)
3. Verify you have the `initialize(pymusic_api, integration_manager)` function
4. Check error messages in PyMusic console

### Error importing modules

If you need to use external modules, make sure they are installed in the same environment where you run PyMusic.

## See Complete Example

Check `\integrations\example\` to see a complete integration example.
