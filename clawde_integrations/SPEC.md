# Clawde Integration Specification v1.0

## File Format

Each integration is a single UTF-8 JSON file placed in `clawde_integrations/active/`.
The filename (without extension) is used as the integration ID for logging.

## Schema

```jsonc
{
  // Required
  "name": "string",              // Display name (max 64 chars)
  "process_match": ["string"],   // Case-insensitive process name substrings

  // Optional
  "title_keywords": ["string"],  // Case-insensitive substrings in window title
  "states": {
    "on_activate": {             // Triggered when process/title matches
      "state": "string",         // Custom state name (auto-prefixed with integration ID)
      "priority": 1-99,          // Higher = overrides lower-priority states
      "hat": "string | null",    // HatType name or null for no hat
      "bubble_text": "string | null",  // Chat bubble overlay text
      "animation": "string"      // Reserved for future use
    },
    "on_idle_after": {           // Fallback after N seconds of no interaction
      "seconds": 30-3600,
      "state": "IDLE | WATCHTOWER | WALKING",
      "bubble_text": "string | null"
    }
  },
  "interactions": {
    "on_pet": {"bubble_text": "string"},
    "on_drag": {"bubble_text": "string"}
  },
  "movement": {
    "preferred_zone": "taskbar | safehouse | window",
    "hide_probability": 0.0-1.0
  }
}
```

## Validation Rules

| Field | Rule |
|-------|------|
| `name` | Non-empty string, max 64 chars |
| `process_match` | Array of at least 1 non-empty string |
| `states.on_activate.priority` | Integer 1–99; values outside range are clamped |
| `states.on_activate.state` | Alphanumeric + underscore, max 32 chars |
| `states.on_idle_after.seconds` | Integer 30–3600 |
| `movement.hide_probability` | Float 0.0–1.0 |

Files that fail validation are skipped with a console warning and do not
prevent other integrations from loading.

## State Naming

Custom states are internally prefixed with the integration ID to avoid
collisions. For example, an integration file named `spotify.json` with
`"state": "MUSIC"` becomes `SPOTIFY_MUSIC` in the state machine.

## Loading Order

Files are loaded in alphabetical order by filename. If two integrations
match the same process, the first one wins.

## Runtime Behavior

- Integrations are loaded once at startup via `IntegrationLoader.load_all()`.
- Changes to files require a Clawde restart.
- The loader exposes `get_process_map()` and `get_title_keywords()` which
  are merged into `StateMachine.PROCESS_STATE_MAP` and
  `TITLE_KEYWORD_STATES` respectively.
- Bubble text from integrations is rendered as a temporary overlay by the
  renderer, identical in style to the hydration bubble but without auto-dismiss.