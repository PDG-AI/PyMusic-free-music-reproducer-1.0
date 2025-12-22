import os
import json
import random
import pygame
import pyperclip
import yt_dlp
import time
import threading
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from password import ADMIN_PASSWORD
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, DEFAULT_VOLUME
from downloader import SmartDownloader

# Obtener la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.volume = DEFAULT_VOLUME
        pygame.mixer.music.set_volume(self.volume)
        self.current_playlist = []
        self.current_song_index = 0
        self.played_songs = set()
        self.check_thread = None
        self.is_playing = False
        self.downloading = False
        self.cancel_download = False
        
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
            "download": self.download_youtube_video,
            "d": self.download_youtube_video,
            "download_spotify": self.download_spotify_playlist,
            "ds": self.download_spotify_playlist,
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
            "paste": self.paste_url,
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
            "search": self.search_song,
            "sch": self.search_song
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
        song_id = self.downloader.download_by_name(
            song_name=song_name,
            artist_name=artist_name,
            album_name=album_name
        )
        
        if song_id:
            print(f"✓ Canción descargada exitosamente con ID: {song_id}")
        else:
            print("No se pudo descargar la canción")

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
            cmd, *args = command.lower().split()  # Convertir a minúsculas
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
Comandos disponibles:
- Download/D [url_youtube] - Descarga un video de YouTube como MP3
- Download_Spotify/DS [url_playlist] - Descarga una playlist de Spotify
- Create/CL [nombre_lista] [id1] [id2] ... - Crea una nueva lista
  Ejemplo: Create MiLista 1 2 3 4 5
- Edit/E [id_lista] add/remove [id1] [id2] ... - Edita una lista existente
  Ejemplos: 
  - Edit 1L add 6 7 8
  - Edit 1L remove 3 4
- Delete/DEL [id_lista_o_cancion] [contraseña] - Elimina una lista o canción
- Play/P [id_lista] - Reproduce una lista
- Play_Song/PS [id_cancion] - Reproduce una canción específica
- Lists/L - Muestra todas las listas de reproducción
- Songs/SH - Muestra todas las canciones disponibles
- ShowList/SL [id_lista] - Muestra el contenido detallado de una lista
- Paste/PA - Pega y procesa automáticamente una URL del portapapeles
- Volume/V [0-50] - Ajusta el volumen del reproductor (máximo 50%)
- Pass/NEXT/N - Pasa a la siguiente canción
- Check/CH [id_lista] - Verifica la integridad de una lista
- Stop/S - Detiene la reproducción actual
- Cancel/C - Cancela la descarga actual
- Help/H - Muestra esta ayuda
- Search/Sch - busqueda por nombre en youtube
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
                    song_id = self.downloader.download_by_name(
                        song_name=song_name,
                        artist_name=artist,
                        album_name=album
                    )
                    
                    if song_id:
                        # Guardar metadatos con el título de Spotify
                        title = f"{song_name} - {artist}"
                        self.save_song_metadata(song_id, title)
                        downloaded_songs.append(song_id)
                        print(f"✓ Descargada: {title}")
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

    def download_youtube_video(self, video_url):
        try:
            self.downloading = True
            self.cancel_download = False
            
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
                'progress_hooks': [self.download_progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if self.cancel_download:
                    print("Descarga cancelada")
                    # Eliminar archivo parcial si existe
                    try:
                        os.remove(os.path.join(self.songs_dir, f"{info['id']}.mp3"))
                    except:
                        pass
                    return None
                
                # Obtener nuevo ID y renombrar el archivo
                new_id = self.get_next_song_id()
                old_path = os.path.join(self.songs_dir, f"{info['id']}.mp3")
                new_path = os.path.join(self.songs_dir, f"{new_id}.mp3")
                os.rename(old_path, new_path)
                
                # Guardar metadatos con el título del video
                title = info.get('title', f'Video {info["id"]}')
                self.save_song_metadata(new_id, title)
                print(f"Canción descargada con ID: {new_id}")
                print(f"Título: {title}")
                time.sleep(1)
                return new_id
        except Exception as e:
            print(f"Error al descargar video: {e}")
            return None
        finally:
            self.downloading = False
            self.cancel_download = False

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

    def create_playlist(self, playlist_name, *songs):
        playlist_id = f"{len(os.listdir(self.lists_dir)) + 1}L"
        playlist_data = {
            "name": playlist_name,
            "songs": list(songs)
        }
        with open(os.path.join(self.lists_dir, f"{playlist_id}.json"), "w") as f:
            json.dump(playlist_data, f)
        print(f"Lista creada con ID: {playlist_id}")
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
            
            self.current_playlist = playlist["songs"]
            self.played_songs = set()
            print(f"Reproduciendo lista: {playlist['name']}")
            
            # Detener el hilo anterior si existe
            self.is_playing = False
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join()
            
            # Iniciar reproducción
            self.is_playing = True
            self.play_next_song()
            
            # Iniciar el hilo de verificación
            self.check_thread = threading.Thread(target=self.check_song_end)
            self.check_thread.daemon = True  # El hilo se cerrará cuando el programa principal termine
            self.check_thread.start()
            
        except Exception as e:
            print(f"Error al reproducir playlist: {e}")

    def check_song_end(self):
        """Verifica si la canción actual ha terminado y reproduce la siguiente"""
        while self.is_playing:
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
            pygame.mixer.music.load(os.path.join(self.songs_dir, f"{next_song}.mp3"))
            pygame.mixer.music.play()
            title = self.get_song_title(next_song)
            print(f"Reproduciendo: {title}")
        except Exception as e:
            print(f"Error al reproducir canción: {e}")
            self.is_playing = False

    def play_song(self, song_id):
        try:
            # Detener el hilo anterior si existe
            self.is_playing = False
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join()
            
            # Iniciar reproducción
            self.is_playing = True
            pygame.mixer.music.load(os.path.join(self.songs_dir, f"{song_id}.mp3"))
            pygame.mixer.music.play()
            title = self.get_song_title(song_id)
            print(f"Reproduciendo: {title}")
            
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

if __name__ == "__main__":
    player = MusicPlayer()
    print("PyMusic - Reproductor de Música Local")
    print("Escribe 'Help' para ver los comandos disponibles")
    print("Consejo: Copia una URL de YouTube o Spotify y usa el comando 'Paste' para procesarla")
    
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
