# Clawde Integrations API

Clawde puede reaccionar a aplicaciones externas mediante archivos JSON colocados en la carpeta `active/`. Cada integración define estados custom, sombreros, burbujas de texto y comportamientos de movimiento que se activan automáticamente cuando Clawde detecta un proceso o título de ventana coincidente.

## Cómo crear una integración

1. Crea un archivo `.json` en la carpeta `clawde_integrations/active/`.
2. Sigue el formato descrito en [SPEC.md](SPEC.md).
3. Reinicia Clawde para cargar la nueva integración.

## Estructura básica

```json
{
  "name": "Mi App",
  "process_match": ["miapp.exe"],
  "title_keywords": ["mi app"],
  "states": {
    "on_activate": {
      "state": "CUSTOM_MUSIC",
      "priority": 48,
      "hat": "HEADPHONES",
      "bubble_text": "🎵 Escuchando música"
    }
  },
  "interactions": {
    "on_pet": {"bubble_text": "🎶 ¡Buena canción!"}
  },
  "movement": {
    "preferred_zone": "taskbar",
    "hide_probability": 0.2
  }
}
```

## Campos disponibles

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nombre descriptivo de la integración |
| `process_match` | string[] | Lista de nombres de proceso (ej: `["spotify.exe"]`) |
| `title_keywords` | string[] | Palabras clave para buscar en el título de ventana |
| `states.on_activate` | object | Estado a activar cuando se detecta el proceso |
| `states.on_idle_after` | object | Estado al que volver tras N segundos sin actividad |
| `interactions.on_pet` | object | Burbuja de texto al acariciar a Clawde |
| `interactions.on_drag` | object | Burbuja de texto al arrastrar a Clawde |
| `movement.preferred_zone` | string | Zona preferida: `"taskbar"`, `"safehouse"`, `"window"` |
| `movement.hide_probability` | float | Probabilidad (0.0–1.0) de esconderse detrás de ventanas |

## Estados base disponibles para extender

Puedes usar estos estados como fallback en `on_idle_after`:

- `IDLE` — Respiración suave, parpadeo
- `WATCHTOWER` — Observando alrededor
- `WALKING` — Caminando por la barra de tareas
- `HYDRATION_REMINDER` — Recordatorio de agua

## Sombreros disponibles

Los siguientes sombreros pueden usarse en el campo `hat`:

- `SUN_HAT` — Sombrero de paja amarillo
- `NIGHT_CAP` — Gorro de dormir azul
- `RAIN_HAT` — Capucha impermeable amarilla
- `CHEF_HAT` — Gorro de chef blanco
- `HARD_HAT` — Casco de construcción amarillo
- `STEALTH_BERET` — Boina negra táctica
- `CYBER_VISOR` — Visor neón verde
- `PARTY_HAT` — Cono de fiesta multicolor
- `WATER_DROPLET` — Gota de agua azul
- `WALKING_CAP` — Gorra pequeña azul

Para definir sombreros custom, usa cualquier string no listado y Clawde lo ignorará silenciosamente (futuras versiones soportarán sprites custom).

## Ejemplos completos

Consulta la carpeta `examples/` para integraciones funcionales:

- [`examples/spotify.json`](examples/spotify.json) — Reacción a Spotify
- [`examples/slack.json`](examples/slack.json) — Reacción a Slack

## Notas importantes

- Las integraciones se cargan al inicio de Clawde. Los cambios requieren reinicio.
- Los archivos JSON inválidos se saltan con un warning en consola.
- La prioridad de estados custom debe estar entre 1 y 99. Valores fuera de rango se ignoran.
- Solo se carga el primer match encontrado (orden alfabético de archivo).