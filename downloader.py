import os
import json
import time
import re
import difflib
from typing import List, Dict, Optional, Tuple
import yt_dlp

class SmartDownloader:
    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        self.exclude_keywords = [
            "review", "rework", "podcast", "interview", "live", "cover",
            "neuro", "evil", "neurofunk", "neurohop", "neurobass", "neurodub",
            "remix", "bootleg", "mashup", "edit", "flip", "flipped",
            "flipz", "flipzter", "bootleg", "bootlegged", "bootleggers"
        ]
        
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
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',  # Asegurar que siempre busque en YouTube
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
        """Descarga un video usando su información"""
        try:
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
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_info['url']])
                return video_info['video_id']
                
        except Exception as e:
            print(f"Error al descargar video: {e}")
            return None
    
    def download_by_name(self, song_name: str, artist_name: str = "", album_name: str = "") -> Optional[str]:
        """Descarga una canción por nombre usando el sistema de confianza"""
        if artist_name:
            search_query = f"{song_name} {artist_name}"
            expected_title = f"{song_name} - {artist_name}"
        else:
            search_query = song_name
            expected_title = song_name
        
        if album_name:
            search_query += f" {album_name}"
        
        search_query += " official audio"
        
        print(f"Buscando: {search_query}")
        
        try:
            # Buscar resultados con confianza
            results = self.search_with_confidence(search_query, expected_title, max_results=5)
            
            if not results:
                print("No se encontraron resultados adecuados.")
                return None
                
            # Si el mejor resultado tiene alta confianza (>70), descargarlo directamente
            if results[0]['confidence'] >= 70:
                print(f"Descargando: {results[0]['title']} (Confianza: {results[0]['confidence']:.1f}%)")
                return self.download_video(results[0])
                
            # Si no hay suficiente confianza, mostrar opciones
            print("\nNo se encontró una coincidencia segura. Opciones disponibles:")
            for i, result in enumerate(results[:10], 1):
                duration = result.get('duration', 0)
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                print(f"{i}. [{result.get('confidence', 0):.1f}%] {result.get('title', 'Sin título')} ({minutes}:{seconds:02d})")
                
            while True:
                try:
                    choice = input("\nSeleccione un número (o 's' para salir): ").strip().lower()
                    if choice == 's':
                        return None
                        
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(results):
                        selected = results[choice_idx]
                        duration = selected.get('duration', 0)
                        minutes = int(duration) // 60
                        seconds = int(duration) % 60
                        
                        print(f"\n=== Canción seleccionada ===")
                        print(f"Título: {selected.get('title', 'Desconocido')}")
                        print(f"Duración: {minutes}:{seconds:02d}")
                        print(f"Confianza: {selected.get('confidence', 0):.1f}%")
                        print("===========================")
                        
                        confirm = input("\n¿Desea descargar esta canción? (s/n): ").strip().lower()
                        if confirm == 's':
                            return self.download_video(selected)
                        else:
                            print("Búsqueda cancelada.")
                            return None
                    else:
                        print("Opción inválida. Intente de nuevo.")
                        
                except ValueError:
                    print("Por favor ingrese un número o 's' para salir.")
        except Exception as e:
            print(f"Error al procesar la búsqueda: {e}")
            return None