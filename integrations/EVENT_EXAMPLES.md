# Event Examples - PyMusic Integrations

## How Events Work

Events have **two parts**:
1. **The event type** (string): `'playlist_changed'`, `'song_changed'`, etc.
2. **Your callback function** (you can name it whatever you want)

## Practical Examples

### Example 1: Simple Event

```python
def initialize(pymusic_api, integration_manager):
    
    # Your function can be named whatever you want
    def when_playlist_changes(data):
        print(f"New playlist: {data['playlist_name']}")
    
    # But the event type is fixed (string)
    integration_manager.register_event_handler('playlist_changed', when_playlist_changes)
```

### Example 2: Multiple Events

```python
def initialize(pymusic_api, integration_manager):
    
    # Function for song change
    def my_song_function(data):
        print(f"Song: {data['song_title']}")
    
    # Function for playlist change
    def my_playlist_function(data):
        print(f"Playlist: {data['playlist_name']}")
    
    # Register both
    integration_manager.register_event_handler('song_changed', my_song_function)
    integration_manager.register_event_handler('playlist_changed', my_playlist_function)
```

### Example 3: Events Without Data

Some events don't receive data, they're just called:

```python
def initialize(pymusic_api, integration_manager):
    
    def when_starts():
        print("Music started playing!")
    
    def when_stops():
        print("Music stopped")
    
    # These events don't receive 'data' parameter
    integration_manager.register_event_handler('playback_started', when_starts)
    integration_manager.register_event_handler('playback_stopped', when_stops)
```

### Example 4: Using Lambda (Anonymous Functions)

```python
def initialize(pymusic_api, integration_manager):
    
    # You can use lambda for simple functions
    integration_manager.register_event_handler(
        'song_changed', 
        lambda data: print(f"New song: {data['song_title']}")
    )
```

## Available Event Types

### Events WITH data (receive a `data` parameter):

| Event | Data received |
|-------|--------------|
| `'song_changed'` | `{'song_id': '123', 'song_title': 'Name', 'duration': 180}` |
| `'playlist_changed'` | `{'playlist_id': '1L', 'playlist_name': 'My Playlist'}` |

### Events WITHOUT data (don't receive parameters):

| Event | When it fires |
|-------|---------------|
| `'playback_started'` | When playback starts |
| `'playback_stopped'` | When playback stops |
| `'playback_paused'` | When paused |
| `'playback_resumed'` | When resumed |

## Complete Real Example

```python
def initialize(pymusic_api, integration_manager):
    
    # Function for when song changes
    def on_song_changed(data):
        song_name = data['song_title']
        song_id = data['song_id']
        duration = data['duration']
        
        # Here you could send to Discord, Twitch, etc.
        print(f"🎵 New song: {song_name} ({duration}s)")
    
    # Function for when playlist changes
    def on_playlist_changed(data):
        playlist_name = data['playlist_name']
        playlist_id = data['playlist_id']
        
        print(f"📋 New playlist: {playlist_name} ({playlist_id})")
    
    # Function for when it starts
    def on_started():
        print("▶️ Playback started")
    
    # Register all events
    integration_manager.register_event_handler('song_changed', on_song_changed)
    integration_manager.register_event_handler('playlist_changed', on_playlist_changed)
    integration_manager.register_event_handler('playback_started', on_started)
```

## Summary

- ✅ Your **function name** can be anything: `on_playlist_changed`, `my_function`, `when_changes`, etc.
- ✅ The **event type** is a fixed string: `'playlist_changed'`, `'song_changed'`, etc.
- ✅ Some events receive `data`, others don't
- ✅ You can register multiple functions for the same event
