import os
import json
import random
import pygame
import pyperclip
import yt_dlp
import time
import threading
import asyncio
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from password import ADMIN_PASSWORD
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, DEFAULT_VOLUME
from downloader import SmartDownloader
from user_stats import UserStats  # <-- Añade esta línea
from spotdl import Spotdl  # Asegúrate de tener spotdl instalado y configurado correctamente
from pypresence import Presence

            
# Obtener la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))



class MusicPlayer:
    def __init__(self):
        # Cargar configuración de dispositivo de audio
        self.audio_device = self.load_audio_device_config()
        
        self.debug = True
        
        # Inicializar pygame mixer con el dispositivo configurado
        self.init_audio_device()
        
        self.volume = DEFAULT_VOLUME
        pygame.mixer.music.set_volume(self.volume)
        self.is_paused = False
        self.paused_position = 0
        self.current_playlist = []
        self.current_song_index = 0
        self.played_songs = set()
        self.check_thread = None
        self.is_playing = False
        self.downloading = False
        self.cancel_download = False
        self.stats = UserStats()  # Inicializar estadísticas
        
        # Información para Streamlabs e integraciones
        self.current_song_id = None
        self.current_song_title = None
        self.current_song_duration = 0
        self.current_playlist_name = None
        self.integration_manager = None  # Se inicializará en __main__
        
        # Crear directorios necesarios
        self.songs_dir = os.path.join(BASE_DIR, "Songs")
        self.lists_dir = os.path.join(BASE_DIR, "Lists")
        os.makedirs(self.songs_dir, exist_ok=True)
        os.makedirs(self.lists_dir, exist_ok=True)
        
        # Cargar o crear el contador de IDs
        self.song_counter_file = os.path.join(self.songs_dir, "counter.json")
        self.song_counter = self.load_song_counter()
        
        # Diccionario de comandos con sus atajos
        self.commands = {
            "download": self.download_spotify_track_new,
            "d": self.download_spotify_track_new,
            "create": self.create_playlist,
            "cl": self.create_playlist,
            "delete": self.delete_playlist,
            "del": self.delete_playlist,
            "play": self.play_playlist,
            "pl": self.play_playlist,
            "play_song": self.play_song,
            "ps": self.play_song,
            "help": self.show_help,
            "h": self.show_help,
            "lists": self.show_lists,
            "l": self.show_lists,
            "songs": self.show_songs,
            "sh": self.show_songs,
            "paste_osoodsodsds": self.paste_url,
            "volume": self.set_volume,
            "v": self.set_volume,
            "pass": self.play_next_song,
            "next": self.play_next_song,
            "p": self.play_next_song,
            "n": self.play_next_song,
            "check": self.check_playlist,
            "ch": self.check_playlist,
            "stop": self.stop_playback,
            "s": self.stop_playback,
            "cancel": self.cancel_current_download,
            "c": self.cancel_current_download,
            "edit": self.edit_playlist,
            "e": self.edit_playlist,
            "showlist": self.show_list_content,
            "sl": self.show_list_content,
            "adf": self.add_song_from_file,
            "pause": self.toggle_pause,
            "resume": self.resume_playback,
            "stats": self.show_stats,
            "rename_song": self.rename_song,
            "rs": self.rename_song,
            "rename_list": self.rename_playlist,
            "rl": self.rename_playlist,
            "changeoutput": self.change_audio_output,
            "co": self.change_audio_output,
        }
        
        # Inicializar cliente de Spotify
        try:
            self.spotify = Spotify(auth_manager=SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET
            ))
        except:
            print("Advertencia: No se pudo inicializar Spotify. Asegúrate de tener las credenciales configuradas en config.py")
            self.spotify = None
        
    def download_spotify_track_new(self, spotify_url):
        try:
            self.downloading = True
            self.cancel_download = False
            self.spotdl_client = Spotdl(client_id="", client_secret="")

            # 1. Obtener metadatos de la canción primero
            song_obj = self.spotdl_client.search([spotify_url])[0]
            temp_filename = f"{song_obj.song_id}.mp3" # ID interno de Spotify para el temporal
            temp_path = os.path.join(self.songs_dir, temp_filename)

            # 2. Descargar
            # spotDL maneja su propio sistema de descarga que garantiza audio funcional para PyGame
            print(f"Descargando: {song_obj.name} - {song_obj.artist}")
            
            # download() devuelve la ruta del archivo descargado
            # Nota: spotDL es síncrono por defecto, si necesitas progress_hook 
            # específico debes manejarlo mediante eventos de spotdl.
            path, song = self.spotdl_client.download(song_obj)
            
            if self.cancel_download:
                if os.path.exists(path):
                    os.remove(path)
                return None

            # 3. Integración con tu sistema de IDs internos
            new_id = self.get_next_song_id()
            new_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
            
            # Mover y renombrar desde la ruta que generó spotDL a tu ruta final
            os.rename(path, new_path)
            
            # 4. Guardar metadatos usando el nombre real de Spotify
            title = f"{song_obj.artist} - {song_obj.name}"
            self.save_song_metadata(new_id, title)
            
            print(f"Canción descargada con ID: {new_id}")
            time.sleep(1)
            return new_id

        except Exception as e:
            print(f"Error al descargar desde Spotify: {e}")
            return None
        finally:
            self.downloading = False
            self.cancel_download = False
        
    def search_song(self, *args):
        """Busca y descarga una canción por nombre"""
        if not args:
            print("Uso: search <nombre_canción> [artista] [álbum]")
            return

        # Inicializar el SmartDownloader si no existe
        if not hasattr(self, 'downloader'):
            self.downloader = SmartDownloader(self.songs_dir)

        # Procesar los argumentos
        song_name = args[0]
        artist_name = args[1] if len(args) > 1 else ""
        album_name = args[2] if len(args) > 2 else ""

        print(f"Buscando: {song_name} {artist_name} {album_name}")
        
        # Usar el SmartDownloader para buscar y descargar
        video_id = self.downloader.download_by_name(
            song_name=song_name,
            artist_name=artist_name,
            album_name=album_name
        )
        
        if video_id:
            # Obtener nuevo ID y renombrar el archivo
            new_id = self.get_next_song_id()
            
            # Buscar el archivo descargado (puede tener diferentes nombres/formats)
            old_path = None
            
            # Si es de fuente alternativa, el ID tiene prefijo "alt_"
            if video_id.startswith("alt_"):
                # Buscar archivos que empiecen con el ID sin el prefijo
                base_id = video_id.replace("alt_", "")
                for file in os.listdir(self.songs_dir):
                    if file.startswith(base_id) or file.startswith(f"jamendo_{base_id}") or file.startswith(f"{base_id}_"):
                        old_path = os.path.join(self.songs_dir, file)
                        break
            else:
                # Buscar archivos normales de YouTube/yt-dlp
                possible_paths = [
                    os.path.join(self.songs_dir, f"{video_id}.mp3"),
                    os.path.join(self.songs_dir, f"{video_id}.m4a"),
                    os.path.join(self.songs_dir, f"{video_id}.webm"),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        old_path = path
                        break
                
                # Buscar archivos que empiecen con el ID
                if not old_path:
                    for file in os.listdir(self.songs_dir):
                        if file.startswith(str(video_id)) or file.startswith(f"jamendo_{video_id}") or file.startswith(f"{video_id}_"):
                            old_path = os.path.join(self.songs_dir, file)
                            break
            
            # Si no se encuentra, buscar cualquier archivo nuevo (último recurso)
            if not old_path:
                try:
                    files = [(f, os.path.getmtime(os.path.join(self.songs_dir, f))) 
                            for f in os.listdir(self.songs_dir) 
                            if f.endswith(('.mp3', '.m4a', '.flac', '.ogg', '.webm')) and not f.startswith('counter')]
                    if files:
                        files.sort(key=lambda x: x[1], reverse=True)
                        # Tomar el más reciente (probablemente el que acabamos de descargar)
                        old_path = os.path.join(self.songs_dir, files[0][0])
                except:
                    pass
            
            if old_path and os.path.exists(old_path):
                # Convertir a MP3 si es necesario
                if not old_path.endswith('.mp3'):
                    try:
                        import subprocess
                        mp3_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
                        subprocess.run([
                            'ffmpeg', '-i', old_path, '-codec:a', 'libmp3lame',
                            '-qscale:a', '2', mp3_path
                        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        os.remove(old_path)
                        old_path = mp3_path
                    except:
                        # Si la conversión falla, renombrar con la extensión original
                        ext = os.path.splitext(old_path)[1]
                        new_path = os.path.join(self.songs_dir, f"{new_id}{ext}")
                        os.rename(old_path, new_path)
                        # Guardar metadatos
                        title = f"{song_name}"
                        if artist_name:
                            title = f"{song_name} - {artist_name}"
                        self.save_song_metadata(new_id, title)
                        print(f"✓ Canción descargada exitosamente con ID: {new_id}")
                        return new_id
                
                # Renombrar a MP3
                new_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
                os.rename(old_path, new_path)
                # Guardar metadatos
                title = f"{song_name}"
                if artist_name:
                    title = f"{song_name} - {artist_name}"
                self.save_song_metadata(new_id, title)
                print(f"✓ Canción descargada exitosamente con ID: {new_id}")
                return new_id
            else:
                print("Error: Archivo descargado no encontrado")
                return None
        else:
            print("No se pudo descargar la canción")
            return None

    def print_progress(self, current, total):
        """Imprime una barra de progreso y el porcentaje"""
        bar_length = 20
        filled_length = int(bar_length * current / total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        percentage = int(100 * current / total)
        print(f"\r[{bar}] {percentage}% ({current}/{total})", end='', flush=True)
        if current == total:
            print()  # Nueva línea al completar

    def paste_url(self):
        """Pega la URL del portapapeles y la procesa automáticamente"""
        try:
            url = pyperclip.paste()
            if "youtube.com" in url or "youtu.be" in url:
                print(f"URL de YouTube detectada: {url}")
                self.download_youtube_video(url)
            elif "spotify.com" in url:
                print(f"URL de Spotify detectada: {url}")
                if "/track/" in url:
                    self.download_spotify_track(url)
                elif "/playlist/" in url:
                    self.download_spotify_playlist(url)
                elif "/album/" in url:
                    self.download_spotify_album(url)
                else:
                    print("URL de Spotify no reconocida. Debe ser una canción o playlist.")
            else:
                print("URL no reconocida. Debe ser de YouTube o Spotify.")
        except Exception as e:
            print(f"Error al pegar URL: {e}")
        
    def process_command(self, command):
        try:
            if not command.strip():
                return

            # use shlex so quoted arguments (paths with spaces) are kept intact
            import shlex
            try:
                parts = shlex.split(command)
            except Exception:
                # fallback to simple split if shlex fails for whatever reason
                parts = command.split()

            if not parts:
                return

            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in self.commands:
                return self.commands[cmd](*args)
            else:
                print(f"Comando no reconocido: {cmd}")
                self.show_help()
        except Exception as e:
            print(f"Error al procesar comando: {e}")
            self.show_help()

    def show_help(self):
        print("""
available commands:
- Download/D [url_youtube] - downloads a youtube video
- Download_Spotify/DS [url_playlist] - downloads an spotify playlist (some songs may be unavailable on youtube)
- Create/CL [list_name] [id1] [id2] ... - creates a new list
  Ejemplo: Create ARandomList 1 2 5
- Edit/E [list_id] add/remove [id1] [id2] ... - Edit an alr existing list
  examples: 
  - Edit 1L add 6 7 8
  - Edit 1L remove 3 4
- Delete/DEL [list_id // song_id] [password] - delete a song or list
- Play/P [list_id] - plays a list
- Play_Song/PS [song_id] - plays an specific song
- Lists/L - shows all available lists
- Songs/SH - shows all available songs
- ShowList/SL [list_id] - shows a list's content
- Paste/PA - Paste whathever link you have copied and download the song
- Volume/V [0-300] - adjust volume (max 300% (i think max is actually 100))
- Pass/NEXT/N - Pasa a la siguiente canción
- Check/CH [list_id] - verify list integrity
- Stop/S - stop current playing song
- Cancel/C - stops current download
- Help/H - shows this 
- Search/Sch - name search on youtube
- ADF - add songs from a file, folder, or ZIP archive (supports MP3, WAV, OGG, FLAC, M4A, AAC, WMA, OPUS, WEBM)
- Pause/Resume - pause or resume the current song
- stats - shows your app stats
- Rename_Song/RS [song_id] [new_name] - rename a song
- Rename_List/RL [list_id] [new_name] - rename a playlist
- ChangeOutput/CO [device_name] - change audio output device (use "default" for default device)
        """)

    def show_lists(self):
        try:
            lists = os.listdir(self.lists_dir)
            if not lists:
                print("No hay listas de reproducción disponibles")
                return
            
            print("\nListas de reproducción disponibles:")
            for i, list_file in enumerate(lists, 1):
                with open(os.path.join(self.lists_dir, list_file), "r") as f:
                    playlist = json.load(f)
                    print(f"{i}. {list_file[:-5]}: {playlist['name']} ({len(playlist['songs'])} canciones)")
        except Exception as e:
            print(f"Error al mostrar listas: {e}")

    def show_songs(self):
        try:
            songs = [f for f in os.listdir(self.songs_dir) if f.lower().endswith('.mp3')]
            if not songs:
                print("No hay canciones disponibles")
                return
            
            # Cargar metadatos si existen
            metadata_file = os.path.join(self.songs_dir, 'metadata.json')
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    metadata = {}
            
            print("\nCanciones disponibles:")
            for i, song in enumerate(sorted(songs), 1):
                song_id = song[:-4]  # Quitar la extensión .mp3
                if song_id in metadata:
                    song_info = metadata[song_id]
                    title = song_info.get("title", f"Canción {song_id}")
                    added_date = song_info.get("added_date", "Fecha desconocida")
                    print(f"{i}. {title} (ID: {song_id}) - Añadida: {added_date}")
                else:
                    print(f"{i}. {song} (ID: {song_id})")
                    
        except Exception as e:
            print(f"Error al mostrar canciones: {e}")
            # Mostrar las canciones directamente del directorio en caso de error
            try:
                songs = [f for f in os.listdir(self.songs_dir) if f.lower().endswith('.mp3')]
                if songs:
                    print("\nLista de archivos MP3 encontrados:")
                    for i, song in enumerate(sorted(songs), 1):
                        print(f"{i}. {song}")
            except:
                print("No se pudieron listar los archivos MP3")

    def download_spotify_track(self, track_url):
        """Descarga una canción individual de Spotify"""
        if not self.spotify:
            print("Error: Spotify no está configurado correctamente")
            return
        
        try:
            # Extraer el ID de la canción de la URL
            track_id = track_url.split("/track/")[1].split("?")[0]
            
            # Obtener información de la canción
            track = self.spotify.track(track_id)
            song_name = track['name']
            artist = track['artists'][0]['name']
            album = track['album']['name']
            
            print(f"Buscando: {song_name} - {artist}")
            
            # Buscar en YouTube con términos más específicos
            search_query = f"{song_name} {artist} {album} official audio"
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    result = ydl.extract_info(f"ytsearch:{search_query}", download=False)
                    if result and 'entries' in result and result['entries']:
                        # Filtrar resultados para evitar podcasts y videos largos
                        valid_videos = []
                        for video in result['entries']:
                            title = video['title'].lower()
                            duration = video.get('duration', 0)
                            # Evitar podcasts, entrevistas y videos muy largos
                            if ('podcast' not in title and 
                                'interview' not in title and 
                                'live' not in title and
                                duration < 600):  # Menos de 10 minutos
                                valid_videos.append(video)
                        
                        if valid_videos:
                            video = valid_videos[0]
                            print(f"Encontrado: {video['title']}")
                            ydl.download([f"https://www.youtube.com/watch?v={video['id']}"])
                            # Guardar el título en un archivo de metadatos
                            self.save_song_metadata(video['id'], video['title'])
                            print(f"✓ Descargada: {song_name}")
                            time.sleep(1)
                            return video['id']
                        else:
                            print(f"No se encontró una versión adecuada para: {song_name}")
                            return None
                    else:
                        print(f"No se encontró el video para: {song_name}")
                        return None
                except Exception as e:
                    print(f"Error al descargar: {e}")
                    return None
                
        except Exception as e:
            print(f"Error al descargar canción de Spotify: {e}")
            return None

    def download_spotify_playlist(self, playlist_url):
        """Descarga una playlist de Spotify usando el sistema de confianza"""
        if not self.spotify:
            print("Error: Spotify no está configurado correctamente")
            return
        
        try:
            self.downloading = True
            self.cancel_download = False
            
            # Inicializar el SmartDownloader si no existe
            if not hasattr(self, 'downloader'):
                self.downloader = SmartDownloader(self.songs_dir)
            
            # Extraer el ID de la playlist de la URL
            playlist_id = playlist_url.split("/playlist/")[1].split("?")[0]
            
            # Obtener información de la playlist
            results = self.spotify.playlist(playlist_id)
            playlist_name = results['name']
            
            print(f"Descargando playlist: {playlist_name}")
            
            # Obtener todas las canciones de la playlist
            tracks = results['tracks']['items']
            total_tracks = len(tracks)
            downloaded_songs = []
            
            for i, track in enumerate(tracks, 1):
                if self.cancel_download:
                    print("\nDescarga cancelada")
                    # Eliminar archivos parciales
                    for song_id in downloaded_songs:
                        try:
                            os.remove(os.path.join(self.songs_dir, f"{song_id}.mp3"))
                        except:
                            pass
                    return None
                    
                try:
                    song_name = track['track']['name']
                    artist = track['track']['artists'][0]['name']
                    album = track['track']['album']['name']
                    
                    print(f"\n[{i}/{total_tracks}] Buscando: {song_name} - {artist}")
                    
                    # Usar el SmartDownloader para buscar y descargar
                    video_id = self.downloader.download_by_name(
                        song_name=song_name,
                        artist_name=artist,
                        album_name=album
                    )
                    
                    if video_id:
                        # Obtener nuevo ID y renombrar el archivo
                        new_id = self.get_next_song_id()
                        old_path = os.path.join(self.songs_dir, f"{video_id}.mp3")
                        new_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
                        
                        if os.path.exists(old_path):
                            os.rename(old_path, new_path)
                            # Guardar metadatos con el título de Spotify
                            title = f"{song_name} - {artist}"
                            self.save_song_metadata(new_id, title)
                            downloaded_songs.append(new_id)
                            print(f"✓ Descargada: {title}")
                        else:
                            print(f"Error: Archivo descargado no encontrado para: {song_name} - {artist}")
                    else:
                        print(f"No se pudo descargar: {song_name} - {artist}")
                        
                except Exception as e:
                    print(f"\nError al procesar canción: {e}")
                    continue
            
            if downloaded_songs:
                # Crear una lista de reproducción con las canciones descargadas
                playlist_id = self.create_playlist(f"Spotify - {playlist_name}", *downloaded_songs)
                print(f"\nPlaylist creada con ID: {playlist_id}")
                return playlist_id
            else:
                print("\nNo se pudo descargar ninguna canción de la playlist")
                return None
                
        except Exception as e:
            print(f"Error al descargar playlist de Spotify: {e}")
            return None
        finally:
            self.downloading = False
            self.cancel_download = False
            
    def download_spotify_album(self, album_url):
        if not self.spotify:
            print("Error: Spotify no está configurado correctamente")
            return
        
        try:
            album_id = album_url.split("/album/")[1].split("?")[0]
            album = self.spotify.album(album_id)
            album_name = album["name"]
            tracks = album["tracks"]["items"]
    
            print(f"Descargando álbum: {album_name}")
            
            downloaded_songs = []
            for track in tracks:
                song_name = track["name"]
                artist = track["artists"][0]["name"]
                search_query = f"{song_name} {artist} official audio"
                print(f"Buscando: {song_name} - {artist}")
                self.download_youtube_video(f"ytsearch:{search_query}")
            
            print(f"Álbum descargado: {album_name}")
        except Exception as e:
            print(f"Error al descargar álbum: {e}")
    
    def save_song_metadata(self, song_id, title):
        """Guarda los metadatos de la canción en un archivo JSON"""
        try:
            metadata_file = os.path.join(self.songs_dir, 'metadata.json')
            metadata = {}
            
            # Cargar metadatos existentes si el archivo existe
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Limpiar el título (eliminar caracteres especiales y extensiones)
            clean_title = title
            if clean_title.endswith('.mp3'):
                clean_title = clean_title[:-4]
            if clean_title.endswith('.webm'):
                clean_title = clean_title[:-5]
            
            # Actualizar metadatos
            metadata[song_id] = {
                "title": clean_title,
                "added_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Guardar metadatos
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar metadatos: {e}")

    def get_song_title(self, song_id):
        """Obtiene el título de una canción desde los metadatos"""
        try:
            metadata_file = os.path.join(self.songs_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if song_id in metadata:
                        return metadata[song_id].get("title", f"Canción {song_id}")
            return f"Canción {song_id}"
        except:
            return f"Canción {song_id}"
    
    def get_song_duration(self, song_id):
        """Obtiene la duración de una canción en segundos"""
        try:
            song_path = os.path.join(self.songs_dir, f"{song_id}.mp3")
            if os.path.exists(song_path):
                try:
                    import mutagen
                    audio = mutagen.File(song_path, easy=True)
                    if audio:
                        return int(audio.info.length)
                except:
                    pass
            return 0
        except:
            return 0

    def download_youtube_video(self, video_url):
        try:
            self.downloading = True
            self.cancel_download = False
            
            cookies_path = os.path.join(BASE_DIR, 'cookies.txt')
            
            # Estrategias de descarga (en orden de preferencia)
            strategies = [
                {
                    'name': 'Android + Web',
                    'opts': {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self.download_progress_hook],
                        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['android', 'web'],
                                'player_skip': ['webpage', 'configs'],
                            }
                        },
                        'user_agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
                        'referer': 'https://www.youtube.com/',
                        'noplaylist': True,
                    }
                },
                {
                    'name': 'iOS Client',
                    'opts': {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self.download_progress_hook],
                        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['ios'],
                            }
                        },
                        'user_agent': 'com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)',
                        'referer': 'https://www.youtube.com/',
                        'noplaylist': True,
                    }
                },
                {
                    'name': 'TV Client',
                    'opts': {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self.download_progress_hook],
                        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['tv_embedded', 'android'],
                            }
                        },
                        'user_agent': 'Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version',
                        'referer': 'https://www.youtube.com/tv',
                        'noplaylist': True,
                    }
                },
                {
                    'name': 'Cualquier formato',
                    'opts': {
                        'format': 'worstaudio/worst',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self.download_progress_hook],
                        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['mweb', 'android'],
                            }
                        },
                        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                        'referer': 'https://m.youtube.com/',
                        'noplaylist': True,
                    }
                },
            ]
            
            # Intentar cada estrategia
            for i, strategy in enumerate(strategies, 1):
                try:
                    if i > 1:
                        print(f"Intentando estrategia alternativa {i}: {strategy['name']}...")
                    
                    with yt_dlp.YoutubeDL(strategy['opts']) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                        
                        if self.cancel_download:
                            print("Descarga cancelada")
                            try:
                                os.remove(os.path.join(self.songs_dir, f"{info['id']}.mp3"))
                            except:
                                pass
                            return None
                        
                        # Obtener nuevo ID y renombrar el archivo
                        new_id = self.get_next_song_id()
                        old_path = os.path.join(self.songs_dir, f"{info['id']}.mp3")
                        new_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
                        
                        # Verificar si el archivo existe (puede tener otra extensión)
                        if not os.path.exists(old_path):
                            for ext in ['m4a', 'webm', 'opus']:
                                alt_old = os.path.join(self.songs_dir, f"{info['id']}.{ext}")
                                if os.path.exists(alt_old):
                                    old_path = alt_old
                                    # Convertir a MP3
                                    try:
                                        import subprocess
                                        subprocess.run([
                                            'ffmpeg', '-i', alt_old, '-codec:a', 'libmp3lame',
                                            '-qscale:a', '2', new_path
                                        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                                        os.remove(alt_old)
                                        # Guardar metadatos
                                        title = info.get('title', f'Video {info["id"]}')
                                        self.save_song_metadata(new_id, title)
                                        print(f"Canción descargada con ID: {new_id}")
                                        print(f"Título: {title}")
                                        time.sleep(1)
                                        return new_id
                                    except:
                                        pass
                        
                        if os.path.exists(old_path):
                            os.rename(old_path, new_path)
                            # Guardar metadatos con el título del video
                            title = info.get('title', f'Video {info["id"]}')
                            self.save_song_metadata(new_id, title)
                            print(f"Canción descargada con ID: {new_id}")
                            print(f"Título: {title}")
                            time.sleep(1)
                            return new_id
                        else:
                            raise Exception("Archivo descargado no encontrado")
                            
                except Exception as e:
                    if i < len(strategies):
                        continue  # Intentar siguiente estrategia
                    else:
                        print(f"Error: Todas las estrategias fallaron. Último error: {e}")
                        return None
        except Exception as e:
            print(f"Error al descargar video: {e}")
            return None
        finally:
            self.downloading = False
            self.cancel_download = False

    def toggle_pause(self, *args):
        """Pausa o reanuda la reproducción actual"""
        if not self.is_playing:
            print("No hay ninguna reproducción en curso")
            return

        if self.is_paused:
            # Reanudar la reproducción desde la posición guardada
            pygame.mixer.music.rewind()  # Rebobinar al inicio
            pygame.mixer.music.set_pos(self.paused_position)  # Ir a la posición guardada
            pygame.mixer.music.unpause()
            self.is_paused = False
            print(f"▶️  Reproducción reanudada en {int(self.paused_position)}s")
            # Disparar evento
            if self.integration_manager:
                self.integration_manager.trigger_event('playback_resumed')
        else:
            # Pausar la reproducción guardando la posición actual
            self.paused_position = pygame.mixer.music.get_pos() / 1000.0  # Guardar en segundos
            pygame.mixer.music.pause()
            self.is_paused = True
            print(f"⏸️  Reproducción pausada en {int(self.paused_position)}s")
            # Disparar evento
            if self.integration_manager:
                self.integration_manager.trigger_event('playback_paused')

    def resume_playback(self, *args):
        """Reanuda la reproducción si está pausada"""
        if not pygame.mixer.music.get_busy() and self.is_playing:
            self.is_paused = True
            pygame.mixer.music.unpause()
            print("Reproducción reanudada")
        elif not self.is_playing:
            print("No hay ninguna reproducción en curso")
        else:
            print("La reproducción ya está en curso")

    def download_progress_hook(self, d):
        """Hook para mostrar el progreso de la descarga"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                total = d['total_bytes']
                downloaded = d['downloaded_bytes']
                percentage = (downloaded / total) * 100
                print(f"\rDescargando: {percentage:.1f}%", end='', flush=True)
            elif 'total_bytes_estimate' in d:
                total = d['total_bytes_estimate']
                downloaded = d['downloaded_bytes']
                percentage = (downloaded / total) * 100
                print(f"\rDescargando: {percentage:.1f}%", end='', flush=True)
        elif d['status'] == 'finished':
            print("\nDescarga completada, procesando...")

    def add_song_from_file(self, file_path=None):
        """Añade canciones desde un archivo, carpeta o ZIP a la biblioteca"""
        try:
            if file_path is None:
                print("Por favor, introduce la ruta completa del archivo/carpeta/ZIP de audio:")
                file_path = input().strip('"')  # Eliminar comillas si el usuario las incluyó
            
            # Verificar si existe
            if not os.path.exists(file_path):
                print(f"Error: La ruta '{file_path}' no existe")
                return None
            
            # Detectar si es archivo, carpeta o ZIP
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                
                if ext == '.zip':
                    # Procesar archivo ZIP
                    return self._import_from_zip(file_path)
                else:
                    # Procesar archivo individual
                    return self._import_single_file(file_path)
            elif os.path.isdir(file_path):
                # Procesar carpeta
                return self._import_from_folder(file_path)
            else:
                print(f"Error: La ruta '{file_path}' no es válida")
                return None
                
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def _import_single_file(self, file_path):
        """Importa un archivo individual de audio"""
        import shutil
        import subprocess
        
        # Formatos de audio soportados (PyGame soporta MP3, OGG, WAV principalmente)
        audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.opus', '.webm']
        
        # Obtener la extensión del archivo
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Verificar que sea un formato de audio soportado
        if ext not in audio_extensions:
            print(f"Error: Formato de archivo no soportado: {ext}")
            print(f"Formatos soportados: {', '.join(audio_extensions)}")
            return None
        
        # Obtener el nombre del archivo sin la ruta y sin extensión (usar como título)
        filename = os.path.basename(file_path)
        song_title = os.path.splitext(filename)[0]
        
        # Obtener el ID para la nueva canción
        song_id = self.get_next_song_id()
        
        # Ruta de destino en la carpeta de canciones (siempre MP3)
        mp3_path = os.path.join(self.songs_dir, f"{song_id}.mp3")
        
        try:
            # Si ya es MP3, copiar directamente
            if ext == '.mp3':
                shutil.copy2(file_path, mp3_path)
            else:
                # Convertir a MP3 usando ffmpeg
                print(f"Convirtiendo {filename} a MP3...")
                try:
                    result = subprocess.run(
                        ['ffmpeg', '-i', file_path, '-codec:a', 'libmp3lame', 
                         '-qscale:a', '2', '-y', mp3_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error al convertir a MP3: {e.stderr.decode('utf-8', errors='ignore')}")
                    return None
                except FileNotFoundError:
                    print("Error: ffmpeg no está instalado. Por favor, instala ffmpeg para convertir archivos.")
                    return None
            
            # Guardar metadatos usando el nombre del archivo como título
            self.save_song_metadata(song_id, song_title)
            print(f"✓ Canción añadida: {song_title} (ID: {song_id})")
            self.stats.increment("songs_imported")
            
            return song_id
            
        except Exception as e:
            print(f"Error al procesar el archivo: {e}")
            
            return None
                
    def _import_from_folder(self, folder_path):
        """Importa todos los archivos de audio de una carpeta"""
        import shutil
        import subprocess
        
        audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.opus', '.webm']
        
        # Buscar todos los archivos de audio en la carpeta
        audio_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in audio_extensions:
                    audio_files.append(os.path.join(root, file))
        
        if not audio_files:
            print(f"No se encontraron archivos de audio en la carpeta: {folder_path}")
            return None
        
        print(f"Se encontraron {len(audio_files)} archivos de audio. Importando...")
        
        imported_songs = []
        failed_songs = []
        
        for i, file_path in enumerate(audio_files, 1):
            filename = os.path.basename(file_path)
            print(f"[{i}/{len(audio_files)}] Procesando: {filename}")
            
            song_id = self._import_single_file(file_path)
            if song_id:
                imported_songs.append(song_id)
            else:
                failed_songs.append(filename)
        
        print(f"\n✓ Importación completada:")
        print(f"  - {len(imported_songs)} canciones importadas exitosamente")
        if failed_songs:
            print(f"  - {len(failed_songs)} canciones fallaron:")
            for song in failed_songs:
                print(f"    - {song}")
        
        # Crear lista de reproducción automáticamente si hay más de una canción
        if len(imported_songs) > 1:
            folder_name = os.path.basename(os.path.normpath(folder_path))
            playlist_id = self.create_playlist(f"Importado: {folder_name}", *imported_songs)
            print(f"\n✓ Lista de reproducción creada automáticamente: {playlist_id}")
        
        return imported_songs if imported_songs else None
    
    def _import_from_zip(self, zip_path):
        """Importa archivos de audio desde un archivo ZIP"""
        import zipfile
        import tempfile
        import shutil
        import subprocess
        
        audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.opus', '.webm']
        
        # Crear directorio temporal para extraer el ZIP
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Extraer el ZIP
            print(f"Extrayendo archivo ZIP: {os.path.basename(zip_path)}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Buscar todos los archivos de audio en el ZIP extraído
            audio_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext.lower() in audio_extensions:
                        audio_files.append(os.path.join(root, file))
            
            if not audio_files:
                print("No se encontraron archivos de audio en el ZIP")
                return None
            
            print(f"Se encontraron {len(audio_files)} archivos de audio en el ZIP. Importando...")
            
            imported_songs = []
            failed_songs = []
            
            for i, file_path in enumerate(audio_files, 1):
                filename = os.path.basename(file_path)
                print(f"[{i}/{len(audio_files)}] Procesando: {filename}")
                
                song_id = self._import_single_file(file_path)
                if song_id:
                    imported_songs.append(song_id)
                else:
                    failed_songs.append(filename)
            
            print(f"\n✓ Importación desde ZIP completada:")
            print(f"  - {len(imported_songs)} canciones importadas exitosamente")
            if failed_songs:
                print(f"  - {len(failed_songs)} canciones fallaron:")
                for song in failed_songs:
                    print(f"    - {song}")
            
            # Crear lista de reproducción automáticamente si hay más de una canción
            if len(imported_songs) > 1:
                zip_name = os.path.splitext(os.path.basename(zip_path))[0]
                playlist_id = self.create_playlist(f"Importado: {zip_name}", *imported_songs)
                print(f"\n✓ Lista de reproducción creada automáticamente: {playlist_id}")
            
            return imported_songs if imported_songs else None
            
        except zipfile.BadZipFile:
            print(f"Error: El archivo '{zip_path}' no es un archivo ZIP válido")
            return None
        except Exception as e:
            print(f"Error al procesar el archivo ZIP: {e}")
            return None
        finally:
            # Limpiar directorio temporal
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


    def create_playlist(self, playlist_name, *songs):
        playlist_id = f"{len(os.listdir(self.lists_dir)) + 1}L"
        playlist_data = {
            "name": playlist_name,
            "songs": list(songs)
        }
        with open(os.path.join(self.lists_dir, f"{playlist_id}.json"), "w") as f:
            json.dump(playlist_data, f)
        print(f"Lista creada con ID: {playlist_id}")
        self.stats.increment("playlists_created")
        return playlist_id

    def delete_playlist(self, item_id, password):
        if password != ADMIN_PASSWORD:
            print("Contraseña incorrecta")
            return False
        try:
            # Verificar si es una lista o una canción
            if item_id.endswith('L'):  # Es una lista
                os.remove(os.path.join(self.lists_dir, f"{item_id}.json"))
                print(f"Lista {item_id} eliminada")
                self.stats.increment("playlists_deleted")
            else:  # Es una canción
                # Eliminar el archivo MP3
                mp3_path = os.path.join(self.songs_dir, f"{item_id}.mp3")
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                    # Eliminar de los metadatos
                    self.remove_song_metadata(item_id)
                    # Eliminar de todas las listas
                    self.remove_song_from_playlists(item_id)
                    print(f"Canción {item_id} eliminada")
                    self.stats.increment("songs_deleted")
                else:
                    print(f"No se encontró la canción {item_id}")
            return True
        except Exception as e:
            print(f"Error al eliminar: {e}")
            return False

    def remove_song_metadata(self, song_id):
        """Elimina una canción de los metadatos"""
        try:
            metadata_file = os.path.join(self.songs_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                if song_id in metadata:
                    del metadata[song_id]
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al eliminar metadatos: {e}")

    def remove_song_from_playlists(self, song_id):
        """Elimina una canción de todas las listas de reproducción"""
        try:
            for playlist_file in os.listdir(self.lists_dir):
                playlist_path = os.path.join(self.lists_dir, playlist_file)
                with open(playlist_path, "r") as f:
                    playlist = json.load(f)
                
                if song_id in playlist['songs']:
                    playlist['songs'].remove(song_id)
                    with open(playlist_path, "w") as f:
                        json.dump(playlist, f, indent=2)
        except Exception as e:
            print(f"Error al eliminar canción de las listas: {e}")

    def play_playlist(self, playlist_id):
        try:
            with open(os.path.join(self.lists_dir, f"{playlist_id}.json"), "r") as f:
                playlist = json.load(f)
            
            old_playlist_name = self.current_playlist_name
            self.current_playlist = playlist["songs"]
            self.current_playlist_name = playlist["name"]
            self.played_songs = set()
            print(f"Reproduciendo lista: {playlist['name']}")
            
            # Disparar evento de cambio de playlist
            if self.integration_manager and old_playlist_name != playlist["name"]:
                self.integration_manager.trigger_event('playlist_changed', {
                    'playlist_id': playlist_id,
                    'playlist_name': playlist["name"]
                })
            
            # Detener el hilo anterior si existe
            self.is_playing = False
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join()
            
            # Detener cualquier reproducción actual
            pygame.mixer.music.stop()
            
            # Iniciar reproducción
            self.is_playing = True
            self.play_next_song()
            
            # Esperar un momento para que la canción empiece a reproducirse
            time.sleep(0.5)
            
            # Iniciar el hilo de verificación
            self.check_thread = threading.Thread(target=self.check_song_end)
            self.check_thread.daemon = True  # El hilo se cerrará cuando el programa principal termine
            self.check_thread.start()
            
        except Exception as e:
            print(f"Error al reproducir playlist: {e}")

    def check_song_end(self):
        """Verifica si la canción actual ha terminado y reproduce la siguiente"""
        # Esperar un momento antes de empezar a verificar para evitar llamadas duplicadas
        time.sleep(2)
        while self.is_playing:
            if self.is_paused == False:
                if not pygame.mixer.music.get_busy() and self.current_playlist:
                    self.play_next_song()
            time.sleep(1)  # Verificar cada segundo

    def play_next_song(self):
        if not self.current_playlist:
            self.is_playing = False
            return

        available_songs = [s for s in self.current_playlist if s not in self.played_songs]
        if not available_songs:
            self.played_songs.clear()
            available_songs = self.current_playlist

        next_song = random.choice(available_songs)
        self.played_songs.add(next_song)
        
        try:
            # Detener cualquier reproducción actual antes de cargar una nueva canción
            pygame.mixer.music.stop()
            pygame.mixer.music.load(os.path.join(self.songs_dir, f"{next_song}.mp3"))
            pygame.mixer.music.play()
            title = self.get_song_title(next_song)
            duration = self.get_song_duration(next_song)
            
            # Actualizar información para Streamlabs e integraciones
            old_song_id = self.current_song_id
            self.current_song_id = next_song
            self.current_song_title = title
            self.current_song_duration = duration
            
            self.stats.increment("songs_played")
            print("")
            print(f"Reproduciendo: {title}")
            print("")
            print("command >")
            
            # Disparar evento de cambio de canción
            if self.integration_manager and old_song_id != next_song:
                self.integration_manager.trigger_event('song_changed', {
                    'song_id': next_song,
                    'song_title': title,
                    'duration': duration
                })
                if not old_song_id:  # Primera canción
                    self.integration_manager.trigger_event('playback_started')
        except Exception as e:
            print(f"Error al reproducir canción: {e}")
            self.is_playing = False

    def play_song(self, song_id):
        try:
            # Detener el hilo anterior si existe
            self.is_playing = False
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join()
            
            # Detener cualquier reproducción actual
            pygame.mixer.music.stop()
            
            # Iniciar reproducción
            self.is_playing = True
            pygame.mixer.music.load(os.path.join(self.songs_dir, f"{song_id}.mp3"))
            pygame.mixer.music.play()
            title = self.get_song_title(song_id)
            duration = self.get_song_duration(song_id)
            
            # Actualizar información para Streamlabs e integraciones
            old_song_id = self.current_song_id
            self.current_song_id = song_id
            self.current_song_title = title
            self.current_song_duration = duration
            self.current_playlist_name = None  # No hay playlist cuando se reproduce una canción individual
            
            print("")
            print(f"Reproduciendo: {title}")
            print("")
            print("command >")
            
            # Disparar evento de cambio de canción
            if self.integration_manager and old_song_id != song_id:
                self.integration_manager.trigger_event('song_changed', {
                    'song_id': song_id,
                    'song_title': title,
                    'duration': duration
                })
                self.integration_manager.trigger_event('playback_started')
            
            # Iniciar el hilo de verificación
            self.check_thread = threading.Thread(target=self.check_song_end)
            self.check_thread.daemon = True
            self.check_thread.start()
            
        except Exception as e:
            print(f"Error al reproducir canción: {e}")

    def set_volume(self, volume_str):
        """Ajusta el volumen del reproductor (0-100)"""
        try:
            volume = float(volume_str) / 100
            # Limitar el volumen máximo al 50% del sistema
            volume = min(volume, 3.0)
            if 0 <= volume <= 3.0:
                self.volume = volume
                pygame.mixer.music.set_volume(volume)
                print(f"Volumen ajustado a {int(volume * 100)}%")
            else:
                print("El volumen debe estar entre 0 y 50")
        except ValueError:
            print("Por favor, introduce un número entre 0 y 50")

    def check_playlist(self, playlist_id):
        """Verifica que todas las canciones de una lista existan"""
        try:
            # Verificar que la lista existe
            if not playlist_id.endswith('L'):
                playlist_id = f"{playlist_id}L"
            
            playlist_path = os.path.join(self.lists_dir, f"{playlist_id}.json")
            if not os.path.exists(playlist_path):
                print(f"Error: La lista {playlist_id} no existe")
                return False

            # Cargar la lista
            with open(playlist_path, "r") as f:
                playlist = json.load(f)
            
            print(f"\nVerificando lista: {playlist['name']}")
            print(f"Total de canciones: {len(playlist['songs'])}")
            
            # Verificar cada canción
            missing_songs = []
            for song_id in playlist['songs']:
                song_path = os.path.join(self.songs_dir, f"{song_id}.mp3")
                if not os.path.exists(song_path):
                    missing_songs.append(song_id)
                    print(f"❌ Canción no encontrada: {self.get_song_title(song_id)} (ID: {song_id})")
                else:
                    print(f"✓ Canción encontrada: {self.get_song_title(song_id)} (ID: {song_id})")
            
            # Mostrar resumen
            if missing_songs:
                print(f"\n⚠️  Se encontraron {len(missing_songs)} canciones faltantes:")
                for song_id in missing_songs:
                    print(f"- {self.get_song_title(song_id)} (ID: {song_id})")
                
                # Preguntar si quiere eliminar las canciones faltantes
                response = input("\n¿Deseas eliminar las canciones faltantes de la lista? (s/n): ")
                if response.lower() == 's':
                    playlist['songs'] = [s for s in playlist['songs'] if s not in missing_songs]
                    with open(playlist_path, "w") as f:
                        json.dump(playlist, f, indent=2)
                    print(f"✅ Lista actualizada. Canciones restantes: {len(playlist['songs'])}")
            else:
                print("\n✅ Todas las canciones están presentes en la lista")
            
            return True
        except Exception as e:
            print(f"Error al verificar la lista: {e}")
            return False

    def stop_playback(self):
        """Detiene la reproducción actual"""
        try:
            self.is_playing = False
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join()
            pygame.mixer.music.stop()
            self.current_playlist = []
            self.played_songs.clear()
            print("Reproducción detenida")
            # Disparar evento
            if self.integration_manager:
                self.integration_manager.trigger_event('playback_stopped')
        except Exception as e:
            print(f"Error al detener la reproducción: {e}")

    def cancel_current_download(self):
        """Cancela la descarga actual"""
        if self.downloading:
            self.cancel_download = True
            print("Cancelando descarga...")
        else:
            print("No hay ninguna descarga en progreso")

    def load_song_counter(self):
        """Carga o crea el contador de IDs de canciones"""
        try:
            if os.path.exists(self.song_counter_file):
                with open(self.song_counter_file, 'r') as f:
                    return json.load(f)
            else:
                # Crear el directorio Songs si no existe
                os.makedirs(self.songs_dir, exist_ok=True)
                # Inicializar el contador
                counter = {"next_id": 1}
                with open(self.song_counter_file, 'w') as f:
                    json.dump(counter, f)
                return counter
        except Exception as e:
            print(f"Error al cargar el contador: {e}")
            return {"next_id": 1}

    def save_song_counter(self):
        """Guarda el contador de IDs de canciones"""
        try:
            with open(self.song_counter_file, 'w') as f:
                json.dump(self.song_counter, f)
        except Exception as e:
            print(f"Error al guardar el contador: {e}")

    def get_next_song_id(self):
        """Obtiene el siguiente ID de canción disponible"""
        song_id = str(self.song_counter["next_id"])
        self.song_counter["next_id"] += 1
        self.save_song_counter()
        return song_id
    
    def load_audio_device_config(self):
        """Carga la configuración del dispositivo de audio desde un archivo"""
        try:
            config_file = os.path.join(BASE_DIR, "audio_config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('audio_device', None)
        except Exception as e:
            print(f"Error al cargar configuración de audio: {e}")
        return None
    
    def save_audio_device_config(self, device_name):
        """Guarda la configuración del dispositivo de audio en un archivo"""
        try:
            config_file = os.path.join(BASE_DIR, "audio_config.json")
            config = {'audio_device': device_name}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al guardar configuración de audio: {e}")
    
    def init_audio_device(self, device_name=None):
        """Inicializa pygame mixer con el dispositivo de audio especificado"""
        try:
            # Cerrar mixer actual si está inicializado
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            
            # Si no se especifica dispositivo, usar el guardado o None (por defecto)
            if device_name is None:
                device_name = self.audio_device
            
            # Inicializar mixer con el dispositivo
            if device_name:
                try:
                    pygame.mixer.init(devicename=device_name)
                    print(f"✓ Dispositivo de audio inicializado: {device_name}")
                except Exception as e:
                    print(f"⚠ Error al inicializar dispositivo '{device_name}': {e}")
                    print("Usando dispositivo por defecto...")
                    pygame.mixer.init()
                    self.audio_device = None
                    self.save_audio_device_config(None)
            else:
                pygame.mixer.init()
                print("✓ Dispositivo de audio: Por defecto")
        except Exception as e:
            print(f"Error al inicializar dispositivo de audio: {e}")
            pygame.mixer.init()
    
    def get_audio_devices(self):
        """Obtiene la lista de dispositivos de audio disponibles"""
        devices = []
        try:
            # Intentar obtener dispositivos usando pygame
            # Nota: pygame.mixer.get_device() puede no estar disponible en todas las versiones
            # Por ahora, usaremos un método alternativo
            
            # En Windows, podemos intentar obtener dispositivos usando índices
            # Primero guardamos el estado actual
            current_volume = self.volume if hasattr(self, 'volume') else DEFAULT_VOLUME
            was_playing = self.is_playing if hasattr(self, 'is_playing') else False
            
            # Probar dispositivos comunes
            test_devices = [None]  # Dispositivo por defecto siempre disponible
            
            # Intentar obtener dispositivos del sistema
            # En Windows, los dispositivos pueden tener nombres como "Speakers", "Headphones", etc.
            # Por ahora, permitiremos que el usuario especifique el nombre directamente
            
            return test_devices
        except Exception as e:
            print(f"Error al obtener dispositivos de audio: {e}")
            return [None]
    
    def change_audio_output(self, *args):
        """Cambia el dispositivo de salida de audio"""
        try:
            if not args:
                print("Uso: changeoutput <nombre_dispositivo>")
                print("Ejemplo: changeoutput Speakers")
                print("Ejemplo: changeoutput Headphones")
                print("Ejemplo: changeoutput default (para usar el dispositivo por defecto)")
                print("\nNota: El nombre del dispositivo debe coincidir exactamente con el nombre del dispositivo en tu sistema.")
                print("Para ver los dispositivos disponibles, revisa la configuración de sonido de Windows.")
                return False
            
            device_name = " ".join(args)
            
            # Si es "default" o "none", usar None
            if device_name.lower() in ['default', 'none', '']:
                device_name = None
            
            # Guardar el volumen actual
            current_volume = self.volume
            
            # Detener la reproducción si está activa
            was_playing = self.is_playing
            current_song = self.current_song_id if was_playing else None
            if was_playing:
                self.stop_playback()
            
            # Cambiar el dispositivo
            old_device = self.audio_device
            self.audio_device = device_name
            self.init_audio_device(device_name)
            
            # Verificar que el mixer se inicializó correctamente
            if not pygame.mixer.get_init():
                print("⚠ Error: No se pudo inicializar el dispositivo de audio")
                # Intentar restaurar el dispositivo anterior
                self.audio_device = old_device
                self.init_audio_device(old_device)
                return False
            
            # Restaurar el volumen
            self.volume = current_volume
            pygame.mixer.music.set_volume(self.volume)
            
            # Guardar la configuración
            self.save_audio_device_config(device_name)
            
            if device_name:
                print(f"✓ Dispositivo de audio cambiado a: {device_name}")
            else:
                print(f"✓ Dispositivo de audio cambiado a: Por defecto")
            
            # Si estaba reproduciendo, informar que necesita reiniciar la reproducción
            if was_playing and current_song:
                print("ℹ Nota: La reproducción se detuvo. Usa 'play' o 'play_song' para continuar.")
            
            return True
            
        except Exception as e:
            print(f"Error al cambiar dispositivo de audio: {e}")
            import traceback
            traceback.print_exc()
            return False

    def edit_playlist(self, playlist_id, action, *song_ids):
        """Edita una lista de reproducción existente"""
        try:
            # Verificar que la lista existe
            if not playlist_id.endswith('L'):
                playlist_id = f"{playlist_id}L"
            
            playlist_path = os.path.join(self.lists_dir, f"{playlist_id}.json")
            if not os.path.exists(playlist_path):
                print(f"Error: La lista {playlist_id} no existe")
                return False

            # Cargar la lista
            with open(playlist_path, "r") as f:
                playlist = json.load(f)
            
            # Verificar la acción
            action = action.lower()
            if action not in ['add', 'remove']:
                print("Error: La acción debe ser 'add' o 'remove'")
                return False

            # Verificar que las canciones existen
            valid_songs = []
            for song_id in song_ids:
                song_path = os.path.join(self.songs_dir, f"{song_id}.mp3")
                if not os.path.exists(song_path):
                    print(f"Advertencia: La canción {song_id} no existe")
                else:
                    valid_songs.append(song_id)

            # Realizar la acción
            if action == 'add':
                # Añadir canciones (evitando duplicados)
                for song_id in valid_songs:
                    if song_id not in playlist['songs']:
                        playlist['songs'].append(song_id)
                print(f"✓ Añadidas {len(valid_songs)} canciones a la lista")
            else:  # remove
                # Eliminar canciones
                original_count = len(playlist['songs'])
                playlist['songs'] = [s for s in playlist['songs'] if s not in valid_songs]
                removed_count = original_count - len(playlist['songs'])
                print(f"✓ Eliminadas {removed_count} canciones de la lista")

            # Guardar la lista actualizada
            with open(playlist_path, "w") as f:
                json.dump(playlist, f, indent=2)
            
            # Mostrar resumen
            print(f"\nLista actualizada: {playlist['name']}")
            print(f"Total de canciones: {len(playlist['songs'])}")
            return True

        except Exception as e:
            print(f"Error al editar la lista: {e}")
            return False

    def show_list_content(self, playlist_id):
        """Muestra el contenido detallado de una lista de reproducción"""
        try:
            # Verificar que la lista existe
            if not playlist_id.endswith('L'):
                playlist_id = f"{playlist_id}L"
            
            playlist_path = os.path.join(self.lists_dir, f"{playlist_id}.json")
            if not os.path.exists(playlist_path):
                print(f"Error: La lista {playlist_id} no existe")
                return False

            # Cargar la lista
            with open(playlist_path, "r") as f:
                playlist = json.load(f)
            
            # Cargar metadatos
            metadata_file = os.path.join(self.songs_dir, 'metadata.json')
            metadata = {}
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            print(f"\nLista: {playlist['name']}")
            print(f"ID: {playlist_id}")
            print(f"Total de canciones: {len(playlist['songs'])}")
            print("\nCanciones:")
            
            for i, song_id in enumerate(playlist['songs'], 1):
                if song_id in metadata:
                    song_info = metadata[song_id]
                    title = song_info.get("title", f"Canción {song_id}")
                    added_date = song_info.get("added_date", "Fecha desconocida")
                    print(f"{i}. {title}")
                    print(f"   ID: {song_id} - Añadida: {added_date}")
                else:
                    print(f"{i}. Canción {song_id}")
                    print(f"   ID: {song_id}")
            
            return True
        except Exception as e:
            print(f"Error al mostrar la lista: {e}")
            return False
            
    def show_stats(self, *args):
        """Muestra las estadísticas del usuario."""
        print(self.stats.get_formatted_stats())
    
    def rename_song(self, song_id, *new_name_parts):
        """Renombra una canción cambiando su título en los metadatos"""
        try:
            if not song_id:
                print("Uso: rename_song <song_id> <nuevo_nombre>")
                print("Ejemplo: rename_song 1 Mi Canción Favorita")
                return False
            
            # Unir todas las partes del nuevo nombre
            new_name = " ".join(new_name_parts) if new_name_parts else None
            
            if not new_name:
                print("Error: Debes proporcionar un nuevo nombre para la canción")
                print("Uso: rename_song <song_id> <nuevo_nombre>")
                return False
            
            # Verificar que la canción existe
            song_path = os.path.join(self.songs_dir, f"{song_id}.mp3")
            if not os.path.exists(song_path):
                print(f"Error: La canción con ID {song_id} no existe")
                return False
            
            # Obtener el título actual
            old_title = self.get_song_title(song_id)
            
            # Actualizar los metadatos
            self.save_song_metadata(song_id, new_name)
            
            print(f"✓ Canción renombrada exitosamente:")
            print(f"  Antes: {old_title}")
            print(f"  Ahora: {new_name}")
            
            return True
            
        except Exception as e:
            print(f"Error al renombrar la canción: {e}")
            return False
    
    def rename_playlist(self, playlist_id, *new_name_parts):
        """Renombra una lista de reproducción"""
        try:
            if not playlist_id:
                print("Uso: rename_list <list_id> <nuevo_nombre>")
                print("Ejemplo: rename_list 1L Mi Playlist Favorita")
                return False
            
            # Asegurar que el ID termine en 'L'
            if not playlist_id.endswith('L'):
                playlist_id = f"{playlist_id}L"
            
            # Unir todas las partes del nuevo nombre
            new_name = " ".join(new_name_parts) if new_name_parts else None
            
            if not new_name:
                print("Error: Debes proporcionar un nuevo nombre para la lista")
                print("Uso: rename_list <list_id> <nuevo_nombre>")
                return False
            
            # Verificar que la lista existe
            playlist_path = os.path.join(self.lists_dir, f"{playlist_id}.json")
            if not os.path.exists(playlist_path):
                print(f"Error: La lista con ID {playlist_id} no existe")
                return False
            
            # Cargar la lista
            with open(playlist_path, 'r', encoding='utf-8') as f:
                playlist = json.load(f)
            
            # Obtener el nombre anterior
            old_name = playlist.get('name', 'Sin nombre')
            
            # Actualizar el nombre
            playlist['name'] = new_name
            
            # Guardar la lista actualizada
            with open(playlist_path, 'w', encoding='utf-8') as f:
                json.dump(playlist, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Lista renombrada exitosamente:")
            print(f"  Antes: {old_name}")
            print(f"  Ahora: {new_name}")
            
            # Actualizar el nombre actual si esta lista está siendo reproducida
            if self.current_playlist_name == old_name:
                self.current_playlist_name = new_name
            
            return True
            
        except Exception as e:
            print(f"Error al renombrar la lista: {e}")
            return False
        
    def update_discord_app(self):
        """Esta función se encargará de Discord en un hilo separado"""
        client_id = '1492995111682834646'
        rpc = Presence(client_id)
        
        try:
            rpc.connect()
            print("\nDiscord RPC conectado en segundo plano.")
            
            while True:
                # Actualizamos el estado con la canción actual
                rpc.update(
                    state=f"Listening to: {self.current_song_title}",
                    details=f"Paused: {self.is_paused}", # Puedes usar variables de tu clase
                    large_image="logo",
                    large_text="PyMusic Player",
                )
                if self.debug == True:
                    print("\nactualizado\n")
                time.sleep(5) # Discord solo permite actualizar cada 15 seg
        except Exception as e:
            print(f"Error en Discord RPC: {e}")

    def start(self):
        # 1. Iniciamos Discord en un hilo "daemon" (se cierra si cierras la app)
        discord_thread = threading.Thread(target=self.update_discord_app, daemon=True)
        discord_thread.start()

        # 2. Aquí sigue el código de tu reproductor (el que bloquea la pantalla o interfaz)
        print("\nIniciando reproductor de música...")


#    DiscordRichPresence discordPresence;
#    memset(&discordPresence, 0, sizeof(discordPresence));
#    discordPresence.state = "Hearing to music";
#    discordPresence.details = "https://github.com/PDG-AI/PyMusic-free-music-reproducer-1.0";
#    discordPresence.startTimestamp = 1507665886;
#    discordPresence.endTimestamp = 1507665886;
#    discordPresence.largeImageKey = "logo";
#    discordPresence.largeImageText = "PyMusic";
#    discordPresence.smallImageText = "Rogue - Level 100";
#    discordPresence.partyId = "ae488379-351d-4a4f-ad32-2b9b01c91657";
#    discordPresence.partySize = 1;
#    discordPresence.partyMax = 1;
#    discordPresence.joinSecret = "MTI4NzM0OjFpMmhuZToxMjMxMjM= ";
#    Discord_UpdatePresence(&discordPresence);




if __name__ == "__main__":
    player = MusicPlayer()
    player.start()
    print("PyMusic - A local music reproducer, for free")
    print("Write 'Help' too see ALL available commands")
    print("Tip: copy any URL (youtube or spotify) and write Paste to process it and download that song automatically")
    print("Remember, not all songs are available on youtube to download, unless you film them with OBS and export to .mp3......")
    
    # Inicializar sistema de integraciones
    try:
        from integrations.integration_base import IntegrationManager
        integration_manager = IntegrationManager(player)
        player.integration_manager = integration_manager
        integration_manager.load_integrations()
        print(f"\n✓ Sistema de integraciones cargado ({len(integration_manager._integrations)} integraciones)")
    except Exception as e:
        print(f"\n⚠ Advertencia: No se pudo cargar el sistema de integraciones: {e}")
        player.integration_manager = None
    
    # Iniciar servidor Streamlabs en un hilo separado
    try:
        from integrations.streamlabs.server import start_server
        streamlabs_thread = threading.Thread(target=start_server, args=(player, 8765), daemon=True)
        streamlabs_thread.start()
        print("✓ Servidor Streamlabs iniciado en http://localhost:8765")
        print("  Accede al overlay en: http://localhost:8765/")
    except Exception as e:
        print(f"⚠ Advertencia: No se pudo iniciar el servidor Streamlabs: {e}")
    
    while True:
        try:
            command = input("\nCommand > ")
            if command.lower() == "exit":
                break
            player.process_command(command)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
