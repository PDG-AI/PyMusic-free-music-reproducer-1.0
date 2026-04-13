import os
import json
import time
import re
import difflib
from typing import List, Dict, Optional, Tuple
import yt_dlp

# Importar fuentes alternativas
try:
    from alternative_sources import AlternativeDownloader
    HAS_ALTERNATIVE_SOURCES = True
except ImportError:
    HAS_ALTERNATIVE_SOURCES = False

class SmartDownloader:
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        self.exclude_keywords = [
        ]
        # Inicializar fuentes alternativas si están disponibles
        if HAS_ALTERNATIVE_SOURCES:
            try:
                self.alternative_downloader = AlternativeDownloader(songs_dir)
            except:
                self.alternative_downloader = None
        else:
            self.alternative_downloader = None
        
    def calculate_confidence(self, expected_title: str, result_title: str, duration: int) -> int:
        """Calcula la puntuación de confianza para un resultado de búsqueda"""
        confidence = 100
        
        # Excluir resultados con palabras clave no deseadas
        title_lower = result_title.lower()
        for keyword in self.exclude_keywords:
            if keyword in title_lower:
                return 0  # Excluir completamente
        
        # Penalización por duración
        if duration > 600:  # Más de 10 minutos
            return 0  # Excluir completamente
        elif duration > 300:  # Más de 5 minutos
            confidence -= 50
        
        # Calcular similitud de caracteres
        expected_clean = self.clean_title(expected_title)
        result_clean = self.clean_title(result_title)
        
        expected_parts = [p.strip() for p in expected_clean.split('-')]
        result_parts = [p.strip() for p in result_clean.split('-')]
        
        total_expected_chars = len(expected_clean.replace(' ', ''))
        matching_chars = 0
        
        for exp_part in expected_parts:
            best_match = None
            best_ratio = 0
            
            for res_part in result_parts:
                ratio = difflib.SequenceMatcher(None, exp_part.lower(), res_part.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = res_part
            
            if best_match:
                matching_chars += len(exp_part) * best_ratio
        
        if total_expected_chars > 0:
            match_percentage = (matching_chars / total_expected_chars) * 100
            missing_chars = total_expected_chars - matching_chars
            confidence -= (missing_chars * 10)  # -10 por cada carácter incorrecto
            confidence = max(confidence, 0)
        
        return min(confidence, 100)
    
    def clean_title(self, title: str) -> str:
        """Limpia el título eliminando caracteres especiales y texto extra"""
        title = re.sub(r'\([^)]*\)', '', title)
        title = re.sub(r'\[[^\]]*\]', '', title)
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    
    def search_with_confidence(self, search_query: str, expected_title: str, max_results: int = 10) -> List[Dict]:
        """Busca videos con sistema de confianza"""
        cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',  # Asegurar que siempre busque en YouTube
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Aumentar el número de resultados para tener más opciones
                search_results = ydl.extract_info(f"ytsearch{max_results*2}:{search_query}", download=False)
                
                if not search_results or 'entries' not in search_results:
                    return []
                
                results_with_confidence = []
                
                for video in search_results['entries']:
                    if not video:
                        continue
                    
                    title = video.get('title', '')
                    duration = int(video.get('duration', 0))
                    video_id = video.get('id', '')
                    
                    # Saltar videos sin ID o título
                    if not video_id or not title:
                        continue
                    
                    # Calcular confianza
                    confidence = self.calculate_confidence(expected_title, title, duration)
                    
                    if confidence > 0:
                        results_with_confidence.append({
                            'title': title,
                            'video_id': video_id,
                            'duration': duration,
                            'confidence': confidence,
                            'url': f"https://www.youtube.com/watch?v={video_id}"
                        })
                
                # Ordenar por confianza y tomar los mejores resultados
                results_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)
                return results_with_confidence[:max_results]  # Devolver solo los mejores resultados
                
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return []
    
    def download_video(self, video_info: Dict) -> Optional[str]:
        """
        Descarga un video usando su información con múltiples estrategias.
        Soporta YouTube, YouTube Music, SoundCloud y otras fuentes compatibles con yt-dlp.
        """
        cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        video_url = video_info['url']
        video_id = video_info['video_id']
        
        # Detectar la fuente basándose en la URL
        is_soundcloud = 'soundcloud.com' in video_url.lower()
        is_youtube_music = 'music.youtube.com' in video_url.lower()
        is_youtube = 'youtube.com' in video_url.lower() or 'youtu.be' in video_url.lower()
        
        # Estrategias base (funcionan para todas las fuentes)
        base_strategies = [
            {
                'name': 'Mejor calidad disponible',
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
                    'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                    'noplaylist': True,
                }
            },
            {
                'name': 'Cualquier formato disponible',
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
                    'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                    'noplaylist': True,
                }
            },
        ]
        
        # Estrategias específicas para YouTube (solo si es YouTube)
        youtube_strategies = []
        if is_youtube or is_youtube_music:
            youtube_strategies = [
                {
                    'name': 'Android + Web (con cookies)',
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
            ]
        
        # Combinar estrategias: primero las específicas de YouTube, luego las genéricas
        strategies = youtube_strategies + base_strategies
        
        # Lista de estrategias a intentar (en orden de preferencia)
        strategies = [
            {
                'name': 'Android + Web (con cookies)',
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
                'name': 'Web Client (sin restricciones)',
                'opts': {
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['web'],
                        }
                    },
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'referer': 'https://www.youtube.com/',
                    'noplaylist': True,
                }
            },
            {
                'name': 'Cualquier formato disponible',
                'opts': {
                    'format': 'worstaudio/worst',  # Aceptar cualquier calidad disponible
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(self.songs_dir, '%(id)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
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
                    print(f"  Intentando estrategia {i}: {strategy['name']}...")
                
                with yt_dlp.YoutubeDL(strategy['opts']) as ydl:
                    ydl.download([video_url])
                    
                    # Verificar que el archivo se descargó
                    expected_file = os.path.join(self.songs_dir, f"{video_id}.mp3")
                    if os.path.exists(expected_file):
                        return video_id
                    # También verificar otros formatos posibles
                    for ext in ['m4a', 'webm', 'opus']:
                        alt_file = os.path.join(self.songs_dir, f"{video_id}.{ext}")
                        if os.path.exists(alt_file):
                            # Convertir a MP3 si es necesario
                            try:
                                import subprocess
                                subprocess.run([
                                    'ffmpeg', '-i', alt_file, '-codec:a', 'libmp3lame', 
                                    '-qscale:a', '2', expected_file
                                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                                os.remove(alt_file)
                                return video_id
                            except:
                                pass
                    
                    return video_id
                    
            except Exception as e:
                if i < len(strategies):
                    continue  # Intentar siguiente estrategia
                else:
                    print(f"  Todas las estrategias fallaron. Último error: {e}")
                    return None
        
        return None
    
    def search_by_name(self, song_name, artist_name="", album_name="", max_results=5):
        """Busca canciones por nombre, artista y álbum"""
        try:
            search_query = f"{song_name} {artist_name} {album_name} official audio"
            cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
            ydl_opts = {
                'format': 'bestaudio/best',
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
                'noplaylist': True,
                'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                'extract_flat': 'in_playlist',
                'force_generic_extractor': True
            }
            
            results = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:  # Asegurarse de que la entrada no sea None
                            results.append({
                                'title': entry.get('title', 'Sin título'),
                                'video_id': entry.get('id', ''),
                                'duration': entry.get('duration', 0),
                                'url': entry.get('url', '')
                            })
            return results
            
        except Exception as e:
            print(f"Error al buscar canciones: {e}")
            return []
    
    def download_by_name(self, song_name, artist_name="", album_name=""):
        """
        Busca y descarga una canción por nombre, artista y álbum.
        Intenta múltiples fuentes: YouTube, YouTube Music, SoundCloud, etc.
        Retorna el video_id del video descargado, o None si falla.
        """
        # Construir el título esperado para el sistema de confianza
        expected_title = f"{song_name}"
        if artist_name:
            expected_title = f"{song_name} - {artist_name}"
        if album_name:
            expected_title = f"{song_name} - {artist_name} - {album_name}"
        
        # Construir la query de búsqueda
        search_query = f"{song_name} {artist_name} {album_name} official audio"
        
        # Lista de fuentes a intentar (en orden de preferencia)
        sources = [
            {
                'name': 'YouTube',
                'search_prefix': 'ytsearch',
                'base_url': 'https://www.youtube.com/watch?v=',
            },
            {
                'name': 'YouTube Music',
                'search_prefix': 'ytmsearch',
                'base_url': 'https://music.youtube.com/watch?v=',
            },
            {
                'name': 'SoundCloud',
                'search_prefix': 'scsearch',
                'base_url': 'https://soundcloud.com/',
            },
        ]
        
        # Intentar cada fuente
        for source in sources:
            try:
                print(f"Buscando en {source['name']}...")
                
                # Buscar en la fuente actual
                results = self._search_in_source(
                    source['search_prefix'], 
                    search_query, 
                    expected_title, 
                    max_results=5
                )
                
                if not results:
                    print(f"  No se encontraron resultados en {source['name']}")
                    continue
                
                # Tomar el mejor resultado
                best_result = results[0]
                print(f"  Mejor resultado en {source['name']}: {best_result['title']} (confianza: {best_result['confidence']}%)")
                
                # Descargar el video
                video_id = self.download_video(best_result)
                
                if video_id:
                    print(f"  ✓ Descargado exitosamente desde {source['name']}")
                    return video_id
                else:
                    print(f"  Error al descargar desde {source['name']}")
                    continue
                    
            except Exception as e:
                print(f"  Error en {source['name']}: {e}")
                continue
        
        # Si todas las fuentes yt-dlp fallaron, intentar fuentes alternativas
        if self.alternative_downloader:
            print("Intentando fuentes alternativas (Internet Archive, Jamendo)...")
            try:
                alt_results = self.alternative_downloader.search_all_sources(
                    song_name, artist_name, max_results=5
                )
                
                if alt_results:
                    # Usar el primer resultado (ya ordenado por relevancia)
                    best_alt = alt_results[0]
                    print(f"  Encontrado en {best_alt['source']}: {best_alt['title']} - {best_alt.get('artist', 'Unknown')}")
                    
                    # Descargar desde fuente alternativa
                    result = self.alternative_downloader.download_from_source(best_alt)
                    
                    if result and len(result) == 2 and result[0] and result[1]:
                        alt_id, temp_path = result
                        # El archivo ya está descargado en temp_path
                        # Retornar un ID especial para que main.py lo maneje
                        # Usaremos el identifier como ID temporal
                        return f"alt_{alt_id}"
                    else:
                        print(f"  Error descargando desde {best_alt['source']}")
                else:
                    print("  No se encontraron resultados en fuentes alternativas")
            except Exception as e:
                print(f"  Error en fuentes alternativas: {e}")
        
        # Si todas las fuentes fallaron
        print(f"No se pudo descargar desde ninguna fuente para: {song_name} {artist_name}")
        return None
    
    def _search_in_source(self, search_prefix: str, search_query: str, expected_title: str, max_results: int = 5) -> List[Dict]:
        """Busca en una fuente específica usando el sistema de confianza"""
        try:
            cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'referer': 'https://www.youtube.com/',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Buscar en la fuente específica
                search_results = ydl.extract_info(f"{search_prefix}{max_results*2}:{search_query}", download=False)
                
                if not search_results or 'entries' not in search_results:
                    return []
                
                results_with_confidence = []
                
                for video in search_results['entries']:
                    if not video:
                        continue
                    
                    title = video.get('title', '')
                    duration = int(video.get('duration', 0))
                    video_id = video.get('id', '')
                    url = video.get('url', '') or video.get('webpage_url', '')
                    
                    # Si no hay URL, construirla según la fuente
                    if not url and video_id:
                        if 'ytm' in search_prefix:
                            url = f"https://music.youtube.com/watch?v={video_id}"
                        elif 'youtube' in search_prefix or 'ytsearch' in search_prefix:
                            url = f"https://www.youtube.com/watch?v={video_id}"
                        elif 'sc' in search_prefix or 'soundcloud' in search_prefix:
                            # SoundCloud usa diferentes formatos de URL
                            url = video.get('webpage_url', '') or f"https://soundcloud.com/track/{video_id}"
                        else:
                            url = f"https://www.youtube.com/watch?v={video_id}"  # Fallback
                    
                    if not video_id or not title:
                        continue
                    
                    # Calcular confianza
                    confidence = self.calculate_confidence(expected_title, title, duration)
                    
                    if confidence > 0:
                        results_with_confidence.append({
                            'title': title,
                            'video_id': video_id,
                            'duration': duration,
                            'confidence': confidence,
                            'url': url
                        })
                
                # Ordenar por confianza y tomar los mejores resultados
                results_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)
                return results_with_confidence[:max_results]
                
        except Exception as e:
            print(f"Error en búsqueda de {search_prefix}: {e}")
            return []
