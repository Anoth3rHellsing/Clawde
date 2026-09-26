# Changelog

Todas las versiones notables de Clawde se documentan aquí. El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [0.1.0] — 2026-09-09

Primera versión pública de Clawde, la mascota de escritorio que reacciona a lo que estás haciendo.

### Añadido

- **Mascota overlay siempre visible** — un pequeño robot voxel naranja que vive en tu escritorio, por encima de todas las ventanas, sin aparecer en la barra de tareas.
- **Detección de contexto en tiempo real** — Clawde observa qué aplicación tienes en primer plano, el título de la ventana, si estás en pantalla completa y tu actividad de teclado/ratón mediante hooks de bajo nivel en Windows.
- **Animaciones contextuales por aplicación:**
  - VS Code, PyCharm, IntelliJ, Sublime Text → se pone gafas, sube a un taburete y señala un tablero holográfico con código; aplaude emocionado cuando escribes rápido.
  - Discord, Slack, Teams → se sienta en un mini-sofá con auriculares, micrófono y burbuja de chat.
  - Explorador de archivos / Finder → se asoma a un archivero miniatura con cajones abiertos.
  - Chrome, Edge, Firefox, Brave, Opera → sostiene una lupa gigante sobre una cinta transportadora.
  - Redes sociales (Twitter/X, Instagram, Facebook, TikTok, Reddit detectadas por título) → mira un mini-teléfono alternando caras de shock y risa.
  - Photoshop, Blender, GIMP → su cuerpo cambia de color continuamente, con paleta y pincel.
  - Notepad, Word, WordPad → sostiene una pluma estilográfica gigante con gota de tinta.
  - Hitman 3 → modo sigilo: se tira al suelo con chaleco táctico, gafas de sol y binoculares.
  - Cyberpunk 2077 → paneles verdes flotantes estilo Matrix con cables conectados a su cabeza.
  - Cualquier app en pantalla completa → se sienta atento mirando hacia arriba, asintiendo de vez en cuando.
- **Comportamientos aleatorios autónomos** — cuando estás inactivo, Clawde hace sus propias cosas cada 12–30 segundos: estornudar, saludar, estirarse, perseguir un bicho imaginario, hacer ejercicio, bostezar, dar una vuelta o quedarse pensando con un "?" flotante.
- **Sistema de estado con prioridades** — los estados forzados (acariciar, arrastrar) siempre ganan sobre los de aplicación, y estos sobre el idle, garantizando transiciones coherentes.
- **Barra de ánimo (Mood)** — sube cuando acaricias a Clawde y vuelve sola a neutro; un ánimo alto puede provocar un baile feliz espontáneo.
- **Panel de estado flotante** — muestra el estado actual y la barra de ánimo; colapsable con un clic.
- **Interacción con el ratón:**
  - Clic y mantener sobre Clawde = acariciar (ronronea con corazones flotantes).
  - Clic y arrastrar = reposicionarlo por la pantalla (se agita con líneas de velocidad).
- **Renderizado voxel 2D** — estilo pixel-art sin antialiasing, con brillo y sombra para imitar el aspecto de una figura impresa en 3D.
- **Partículas animadas** — corazones al acariciar, "Zzz" al bostezar, chispas al bailar y al escribir rápido.
- **Ejecutable autocontenido** — `Clawde.exe` compilado con PyInstaller, no requiere Python ni dependencias instaladas.
- **Soporte multiplataforma en el código** — detección de ventana preparada para Windows (win32) y macOS (Cocoa/Quartz), con polling de respaldo en otros sistemas.

### Notas técnicas

- Construido con Python 3.14 y PySide6 (Qt 6).
- Hooks de teclado/ratón tipados correctamente para Python de 64 bits (sin desbordamientos en `CallNextHookEx`).
- Máquina de estados desacoplada del renderizado para facilitar añadir nuevos comportamientos.