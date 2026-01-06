"""
integration example for PyMusic, delete file if you dont want to get random prints when starting the app

NOTE: you can connect this to discord, twitch, etc. and send commands to the app with messages or idk what the fuck you want to do with it.

this is an example file to show how to create a custom integration.
to create your own integration:
1. create a folder inside of \integrations\ with the name of your integration
2. create integration.py file inside of that folder
3. Implement initialize() function wich receives PyMusicAPI and IntegrationManager
4. use the API to obtain information or send commands
5. register events if you need to react to changes
"""

def initialize(pymusic_api, integration_manager):
    """
    loads when PyMusic loads the integration.
    
    Args:
        pymusic_api: to interact with PyMusic via API
        integration_manager: to register events
    """
    print("integration example loaded")
    
    # ========== EXAMPLE: Get information ==========
    
    # obtain current information
    current_song = pymusic_api.song_name
    current_playlist = pymusic_api.playlist_name
    is_playing = pymusic_api.is_playing
    
    print(f"current song: {current_song}")
    print(f"current playlist: {current_playlist}")
    print(f"playing: {is_playing}")
    
    # obtain playlists
    all_playlists = pymusic_api.get_all_playlists()
    print(f"available_playlists": {list(all_playlists.keys())}")
    
    # ========== EJEMPLO: Registrar manejadores de eventos ==========
    
    def on_song_changed(data):  #gives data variable with the new song information
        """called when the song changes"""
        print(f"new song: {data.get('song_title', 'Desconocida')}")
        print(f"ID: {data.get('song_id', 'N/A')}")
        print(f"Duration: {data.get('duration', 0)} seconds")
    
    def on_playlist_changed(data):  #gives data variable with the new playlist information
        """called when the playlist changes"""
        print(f"new playlist: {data.get('playlist_name', 'Desconocida')}")
        print(f"ID: {data.get('playlist_id', 'N/A')}")
    
    def on_playback_started():
        """called when the playback starts"""
        print("playback started")
    
    def on_playback_stopped():
        """called when the playback stops"""
        print("playback stopped")
    
    def on_playback_paused():
        """called when the playback is paused"""
        print("playback paused")
    
    def on_playback_resumed():
        """called when the playback is resumed"""
        print("playback resumed")
    
    # register events
    integration_manager.register_event_handler('song_changed', on_song_changed)
    integration_manager.register_event_handler('playlist_changed', on_playlist_changed)
    integration_manager.register_event_handler('playback_started', on_playback_started)
    integration_manager.register_event_handler('playback_stopped', on_playback_stopped)
    integration_manager.register_event_handler('playback_paused', on_playback_paused)
    integration_manager.register_event_handler('playback_resumed', on_playback_resumed)
    
    # ========== EXAMPLE COMMANDS: (comented to not execute automatically) ==========
    
    # just uncomment the lines you need to use
    
    # # go to next song
    # pymusic_api.next_song()
    
    # # play specific playlist
    # pymusic_api.play_playlist("1L")
    
    # # play specific song
    # pymusic_api.play_song("1")
    
    # # Pause
    # pymusic_api.pause()
    
    # # resume
    # pymusic_api.resume()
    
    # # stop
    # pymusic_api.stop()
    
    # # change volume (0.0 - 3.0)
    # pymusic_api.set_volume(1.5)
    
    print("successfully loaded integration")

