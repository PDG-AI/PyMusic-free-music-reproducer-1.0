import json
import os
import time
from typing import Dict, Any

class UserStats:
    def __init__(self, stats_file: str = "user_stats.json"):
        self.stats_file = stats_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Any]:
        """Carga las estadísticas desde el archivo o crea unas nuevas si no existe."""
        default_stats = {
            "songs_played": 0,
            "songs_skipped": 0,
            "playlists_created": 0,
            "playlists_deleted": 0,
            "songs_downloaded": 0,
            "songs_imported": 0,
            "songs_deleted": 0,
            "total_play_time": 0,  # en segundos
            "first_run": int(time.time()),
            "last_updated": int(time.time())
        }
        
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return {**default_stats, **json.load(f)}
        except Exception as e:
            print(f"Error cargando estadísticas: {e}")
        
        return default_stats
    
    def _save_stats(self):
        """Guarda las estadísticas en el archivo."""
        self.stats["last_updated"] = int(time.time())
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=4)
        except Exception as e:
            print(f"Error guardando estadísticas: {e}")
    
    def increment(self, stat_name: str, amount: int = 1):
        """Incrementa un contador de estadísticas."""
        if stat_name in self.stats and isinstance(self.stats[stat_name], (int, float)):
            self.stats[stat_name] += amount
            self._save_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Devuelve todas las estadísticas."""
        return self.stats.copy()
    
    def get_formatted_stats(self) -> str:
        """Devuelve las estadísticas formateadas como texto."""
        stats = self.stats
        total_days = (time.time() - stats["first_run"]) / (24 * 3600)
        songs_per_day = stats["songs_played"] / max(1, total_days)
        
        return f"""
User Statistics
───────────────────────────
Played songs: {stats["songs_played"]}
Skipped songs: {stats["songs_skipped"]}
Created lists: {stats["playlists_created"]}
Deleted lists: {stats["playlists_deleted"]}
Downloaded lists: {stats["songs_downloaded"]}
Imported Lists: {stats["songs_imported"]}
Deleted songs: {stats["songs_deleted"]}
Total play time: {self._format_seconds(stats["total_play_time"])}
Days using wathever this is: {int(total_days)} días
Songs per day: {songs_per_day:.1f}
───────────────────────────
Last update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats["last_updated"]))}
"""
    
    @staticmethod
    def _format_seconds(seconds: int) -> str:
        """Formatea segundos a un string legible (HH:MM:SS)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
