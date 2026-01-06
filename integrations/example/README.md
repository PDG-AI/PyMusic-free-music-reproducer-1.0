# Ejemplo de Integración para PyMusic

Este es un ejemplo de cómo crear una integración personalizada para PyMusic.

## Estructura

```
integrations/
  tu_integracion/
    integration.py  <- Archivo requerido
    otros_archivos.py  <- Archivos adicionales opcionales
    README.md  <- Documentación (opcional)
```

## API Disponible

### Obtener Información (GET)

```python
# Información de la canción actual
pymusic_api.song_name          # Nombre de la canción
pymusic_api.song_id            # ID de la canción
pymusic_api.song_duration      # Duración en segundos
pymusic_api.playlist_name      # Nombre de la playlist actual
pymusic_api.is_playing         # True si está reproduciendo
pymusic_api.is_paused          # True si está pausado
pymusic_api.volume             # Volumen actual (0.0 - 3.0)

# Obtener listas
pymusic_api.get_playlist_songs()  # Lista de IDs de canciones en la playlist actual
pymusic_api.get_all_playlists()   # Dict {id: nombre} de todas las playlists
pymusic_api.get_all_songs()       # Dict {id: título} de todas las canciones
```

### Enviar Comandos (SET)

```python
# Control de reproducción
pymusic_api.next_song()        # Pasa a la siguiente canción
pymusic_api.play_playlist(id)  # Reproduce una playlist
pymusic_api.play_song(id)      # Reproduce una canción específica
pymusic_api.pause()            # Pausa la reproducción
pymusic_api.resume()           # Reanuda la reproducción
pymusic_api.stop()             # Detiene la reproducción
pymusic_api.set_volume(vol)    # Establece el volumen (0.0 - 3.0)
```

### Eventos Disponibles

Puedes registrar manejadores para estos eventos:

- `song_changed` - Se dispara cuando cambia la canción (recibe `data` con `song_id`, `song_title`, `duration`)
- `playlist_changed` - Se dispara cuando cambia la playlist (recibe `data` con `playlist_id`, `playlist_name`)
- `playback_started` - Se dispara cuando comienza la reproducción
- `playback_stopped` - Se dispara cuando se detiene la reproducción
- `playback_paused` - Se dispara cuando se pausa la reproducción
- `playback_resumed` - Se dispara cuando se reanuda la reproducción

## Ejemplo de Uso

```python
def initialize(pymusic_api, integration_manager):
    # Obtener información
    print(f"Canción actual: {pymusic_api.song_name}")
    
    # Registrar evento
    def on_song_changed(data):
        print(f"Nueva canción: {data['song_title']}")
    
    integration_manager.register_event_handler('song_changed', on_song_changed)
    
    # Enviar comando
    pymusic_api.next_song()
```

## Notas

- La función `initialize()` es obligatoria y se llama automáticamente
- Todos los métodos de la API son thread-safe
- Los eventos se disparan en el mismo hilo que PyMusic, ten cuidado con operaciones bloqueantes

