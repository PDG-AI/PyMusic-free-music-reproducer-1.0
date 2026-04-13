"""
Fuentes alternativas de descarga de música que no usan yt-dlp
Incluye APIs directas y scraping de sitios legales
"""
import os
import json
import requests
import time
from typing import List, Dict, Optional
from urllib.parse import quote, urlencode


class InternetArchiveSource:
    """Fuente de descarga desde Internet Archive (archive.org)"""
    
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        self.base_url = "https://archive.org"
        self.api_url = "https://archive.org/advancedsearch.php"
    
    def search(self, song_name: str, artist_name: str = "", max_results: int = 10) -> List[Dict]:
        """Busca música en Internet Archive"""
        try:
            # Construir query de búsqueda
            query_parts = [f"title:{song_name}"]
            if artist_name:
                query_parts.append(f"creator:{artist_name}")
            
            query = " AND ".join(query_parts)
            
            params = {
                'q': query,
                'fl': 'identifier,title,creator,downloads,item_size',
                'output': 'json',
                'rows': max_results,
                'sort': '[downloads desc]',  # Ordenar por descargas
            }
            
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'response' in data and 'docs' in data['response']:
                for item in data['response']['docs']:
                    # Filtrar solo items de audio
                    identifier = item.get('identifier', '')
                    if not identifier:
                        continue
                    
                    # Obtener detalles del item
                    item_url = f"{self.base_url}/metadata/{identifier}"
                    try:
                        item_response = requests.get(item_url, timeout=5)
                        item_data = item_response.json()
                        
                        # Buscar archivos de audio
                        files = item_data.get('files', [])
                        audio_file = None
                        for file_info in files:
                            filename = file_info.get('name', '')
                            if filename.endswith(('.mp3', '.flac', '.ogg', '.m4a')):
                                # Preferir MP3
                                if filename.endswith('.mp3') or not audio_file:
                                    audio_file = {
                                        'name': filename,
                                        'size': file_info.get('size', 0),
                                        'format': file_info.get('format', ''),
                                    }
                        
                        if audio_file:
                            results.append({
                                'title': item.get('title', 'Unknown'),
                                'artist': item.get('creator', 'Unknown'),
                                'identifier': identifier,
                                'download_url': f"{self.base_url}/download/{identifier}/{audio_file['name']}",
                                'format': audio_file['format'],
                                'size': audio_file['size'],
                                'source': 'Internet Archive',
                            })
                    except:
                        continue
            
            return results
            
        except Exception as e:
            print(f"Error buscando en Internet Archive: {e}")
            return []
    
    def download(self, item_info: Dict) -> Optional[str]:
        """Descarga un item de Internet Archive"""
        try:
            download_url = item_info['download_url']
            identifier = item_info['identifier']
            filename = os.path.basename(download_url)
            
            print(f"  Descargando desde Internet Archive: {item_info['title']}")
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Guardar temporalmente con el identifier
            temp_path = os.path.join(self.songs_dir, f"{identifier}_{filename}")
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return identifier, temp_path
            
        except Exception as e:
            print(f"  Error descargando desde Internet Archive: {e}")
            return None, None


class FreeMusicArchiveSource:
    """Fuente de descarga desde Free Music Archive (si está disponible)"""
    
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        # Nota: FMA cerró en 2018, pero algunos mirrors pueden estar disponibles
        self.base_url = "https://freemusicarchive.org"
    
    def search(self, song_name: str, artist_name: str = "", max_results: int = 10) -> List[Dict]:
        """Busca en Free Music Archive (puede no estar disponible)"""
        # FMA cerró, pero dejamos la estructura por si hay mirrors
        return []


class JamendoSource:
    """Fuente de descarga desde Jamendo (música libre con API)"""
    
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        self.api_url = "https://api.jamendo.com/v3.0/tracks"
        # API key pública de ejemplo (limitada, obtener una propia en jamendo.com)
        # Por ahora deshabilitamos Jamendo ya que requiere registro
        self.api_key = None  # Se puede obtener gratis en jamendo.com
    
    def search(self, song_name: str, artist_name: str = "", max_results: int = 10) -> List[Dict]:
        """Busca música en Jamendo"""
        if not self.api_key or self.api_key == "YOUR_API_KEY":
            # Jamendo requiere API key, deshabilitado por defecto
            return []
        
        try:
            # Construir query
            query = song_name
            if artist_name:
                query = f"{artist_name} {song_name}"
            
            params = {
                'client_id': self.api_key,
                'format': 'json',
                'limit': max_results,
                'search': query,
                'order': 'popularity_total',
            }
            
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'results' in data:
                for track in data['results']:
                    # Solo tracks con descarga disponible
                    if track.get('audio', ''):
                        results.append({
                            'title': track.get('name', 'Unknown'),
                            'artist': track.get('artist_name', 'Unknown'),
                            'track_id': track.get('id', ''),
                            'download_url': track.get('audio', ''),
                            'duration': track.get('duration', 0),
                            'source': 'Jamendo',
                        })
            
            return results
            
        except Exception as e:
            print(f"Error buscando en Jamendo: {e}")
            return []
    
    def download(self, item_info: Dict) -> Optional[str]:
        """Descarga un track de Jamendo"""
        try:
            download_url = item_info['download_url']
            track_id = item_info['track_id']
            
            print(f"  Descargando desde Jamendo: {item_info['title']}")
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Guardar temporalmente
            temp_path = os.path.join(self.songs_dir, f"jamendo_{track_id}.mp3")
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return track_id, temp_path
            
        except Exception as e:
            print(f"  Error descargando desde Jamendo: {e}")
            return None, None


class AlternativeDownloader:
    """Gestor de fuentes alternativas de descarga"""
    
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        # Solo Internet Archive por ahora (más confiable)
        self.sources = [
            InternetArchiveSource(songs_dir),
            # JamendoSource(songs_dir),  # Requiere API key, deshabilitado por defecto
            # FreeMusicArchiveSource(songs_dir),  # Deshabilitado hasta encontrar mirror
        ]
    
    def search_all_sources(self, song_name: str, artist_name: str = "", max_results: int = 5) -> List[Dict]:
        """Busca en todas las fuentes alternativas"""
        all_results = []
        
        for source in self.sources:
            try:
                results = source.search(song_name, artist_name, max_results)
                all_results.extend(results)
            except Exception as e:
                print(f"Error en fuente {source.__class__.__name__}: {e}")
                continue
        
        return all_results
    
    def download_from_source(self, item_info: Dict) -> Optional[tuple]:
        """Descarga desde la fuente especificada. Retorna (item_id, temp_path) o None"""
        source_name = item_info.get('source', '')
        
        for source in self.sources:
            # Buscar la fuente correcta
            if source_name in source.__class__.__name__ or source_name.replace(' ', '') in source.__class__.__name__:
                result = source.download(item_info)
                if result and len(result) == 2:
                    return result
        
        return None

