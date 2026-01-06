"""
Módulo base para integraciones de PyMusic
Este módulo proporciona una API simple para que las integraciones puedan
interactuar con PyMusic sin modificar el código base.
"""
import threading
from typing import Callable, Optional, Dict, Any, List


class PyMusicAPI:
    """
    API principal para que las integraciones interactúen con PyMusic
    """
    def __init__(self, music_player):
        self._player = music_player
        self._lock = threading.Lock()
    
    # ========== GETTERS - Obtener información ==========
    
    @property
    def song_name(self) -> str:
        """Obtiene el nombre de la canción actual"""
        with self._lock:
            return self._player.current_song_title or "No hay canción reproduciéndose"
    
    @property
    def song_id(self) -> Optional[str]:
        """Obtiene el ID de la canción actual"""
        with self._lock:
            return self._player.current_song_id
    
    @property
    def song_duration(self) -> int:
        """Obtiene la duración de la canción actual en segundos"""
        with self._lock:
            return self._player.current_song_duration or 0
    
    @property
    def playlist_name(self) -> Optional[str]:
        """Obtiene el nombre de la lista de reproducción actual"""
        with self._lock:
            return self._player.current_playlist_name
    
    @property
    def is_playing(self) -> bool:
        """Verifica si hay una canción reproduciéndose"""
        with self._lock:
            return self._player.is_playing and not self._player.is_paused
    
    @property
    def is_paused(self) -> bool:
        """Verifica si la reproducción está pausada"""
        with self._lock:
            return self._player.is_paused
    
    @property
    def volume(self) -> float:
        """Obtiene el volumen actual (0.0 - 3.0)"""
        with self._lock:
            return self._player.volume
    
    def get_playlist_songs(self) -> List[str]:
        """Obtiene la lista de IDs de canciones en la playlist actual"""
        with self._lock:
            return list(self._player.current_playlist) if self._player.current_playlist else []
    
    def get_all_playlists(self) -> Dict[str, str]:
        """Obtiene un diccionario con todas las playlists disponibles {id: nombre}"""
        try:
            import os
            import json
            playlists = {}
            for file in os.listdir(self._player.lists_dir):
                if file.endswith('.json'):
                    playlist_id = file[:-5]
                    with open(os.path.join(self._player.lists_dir, file), 'r') as f:
                        playlist_data = json.load(f)
                        playlists[playlist_id] = playlist_data.get('name', playlist_id)
            return playlists
        except Exception as e:
            print(f"Error al obtener playlists: {e}")
            return {}
    
    def get_all_songs(self) -> Dict[str, str]:
        """Obtiene un diccionario con todas las canciones disponibles {id: título}"""
        try:
            import os
            import json
            songs = {}
            metadata_file = os.path.join(self._player.songs_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    for song_id, song_data in metadata.items():
                        songs[song_id] = song_data.get('title', f'Canción {song_id}')
            return songs
        except Exception as e:
            print(f"Error al obtener canciones: {e}")
            return {}
    
    # ========== COMMANDS - Enviar órdenes ==========
    
    def next_song(self) -> bool:
        """Pasa a la siguiente canción"""
        try:
            with self._lock:
                if self._player.is_playing and self._player.current_playlist:
                    self._player.play_next_song()
                    return True
            return False
        except Exception as e:
            print(f"Error al pasar a la siguiente canción: {e}")
            return False
    
    def play_playlist(self, playlist_id: str) -> bool:
        """Reproduce una playlist por su ID"""
        try:
            with self._lock:
                self._player.play_playlist(playlist_id)
                return True
        except Exception as e:
            print(f"Error al reproducir playlist: {e}")
            return False
    
    def play_song(self, song_id: str) -> bool:
        """Reproduce una canción específica por su ID"""
        try:
            with self._lock:
                self._player.play_song(song_id)
                return True
        except Exception as e:
            print(f"Error al reproducir canción: {e}")
            return False
    
    def pause(self) -> bool:
        """Pausa la reproducción actual"""
        try:
            with self._lock:
                if self._player.is_playing:
                    self._player.toggle_pause()
                    return True
            return False
        except Exception as e:
            print(f"Error al pausar: {e}")
            return False
    
    def resume(self) -> bool:
        """Reanuda la reproducción si está pausada"""
        try:
            with self._lock:
                if self._player.is_paused:
                    self._player.toggle_pause()
                    return True
            return False
        except Exception as e:
            print(f"Error al reanudar: {e}")
            return False
    
    def stop(self) -> bool:
        """Detiene la reproducción actual"""
        try:
            with self._lock:
                self._player.stop_playback()
                return True
        except Exception as e:
            print(f"Error al detener: {e}")
            return False
    
    def set_volume(self, volume: float) -> bool:
        """Establece el volumen (0.0 - 3.0)"""
        try:
            with self._lock:
                volume = max(0.0, min(3.0, volume))
                self._player.volume = volume
                self._player.set_volume(str(int(volume * 100)))
                return True
        except Exception as e:
            print(f"Error al establecer volumen: {e}")
            return False


class IntegrationManager:
    """
    Gestor de integraciones que detecta y carga automáticamente las integraciones
    """
    def __init__(self, music_player):
        self._player = music_player
        self._integrations = []
        self._event_handlers = {
            'song_changed': [],
            'playlist_changed': [],
            'playback_started': [],
            'playback_stopped': [],
            'playback_paused': [],
            'playback_resumed': [],
        }
        self._api = PyMusicAPI(music_player)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        Registra un manejador de eventos
        
        Args:
            event_type: Tipo de evento ('song_changed', 'playlist_changed', etc.)
            handler: Función que se llamará cuando ocurra el evento
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
        else:
            print(f"Advertencia: Tipo de evento desconocido: {event_type}")
    
    def trigger_event(self, event_type: str, data: Dict[str, Any] = None):
        """Dispara un evento a todos los manejadores registrados"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if data:
                        handler(data)
                    else:
                        handler()
                except Exception as e:
                    print(f"Error en manejador de evento {event_type}: {e}")
    
    def load_integrations(self):
        """Carga automáticamente todas las integraciones en la carpeta integrations"""
        import os
        import importlib
        import sys
        import importlib.util
        
        integrations_dir = os.path.join(BASE_DIR, "integrations")
        
        if not os.path.exists(integrations_dir):
            return
        
        # Ignorar ciertos directorios
        ignore_dirs = {'__pycache__', 'example'}  # example es solo para documentación
        
        for item in os.listdir(integrations_dir):
            # Ignorar archivos y directorios especiales
            if item.startswith('.') or item in ignore_dirs:
                continue
                
            integration_path = os.path.join(integrations_dir, item)
            
            # Verificar que sea un directorio y tenga integration.py
            if os.path.isdir(integration_path):
                integration_file = os.path.join(integration_path, "integration.py")
                
                if os.path.exists(integration_file):
                    try:
                        # Crear el nombre del módulo
                        module_name = f"integrations_{item}_integration"
                        
                        # Cargar el módulo desde el archivo
                        spec = importlib.util.spec_from_file_location(module_name, integration_file)
                        if spec is None or spec.loader is None:
                            print(f"⚠ No se pudo crear spec para {item}")
                            continue
                            
                        module = importlib.util.module_from_spec(spec)
                        
                        # Añadir el directorio de la integración al path para imports relativos
                        if integration_path not in sys.path:
                            sys.path.insert(0, integration_path)
                        
                        # Ejecutar el módulo
                        spec.loader.exec_module(module)
                        
                        # Intentar inicializar la integración
                        if hasattr(module, 'initialize'):
                            integration_data = {
                                'name': item,
                                'module': module,
                                'api': self._api,
                                'manager': self
                            }
                            try:
                                module.initialize(self._api, self)
                                self._integrations.append(integration_data)
                                print(f"✓ Integración cargada: {item}")
                            except Exception as e:
                                print(f"⚠ Error al inicializar integración {item}: {e}")
                                import traceback
                                traceback.print_exc()
                        else:
                            print(f"⚠ Integración {item} no tiene función 'initialize'")
                    
                    except Exception as e:
                        print(f"⚠ Error al cargar integración {item}: {e}")
                        import traceback
                        traceback.print_exc()
    
    def get_api(self) -> PyMusicAPI:
        """Obtiene la instancia de la API para uso interno"""
        return self._api


# Importaciones necesarias para el módulo base
import os
import json
import importlib.util

# Obtener BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

