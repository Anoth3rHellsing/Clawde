# Clawde — Tu mascota de escritorio que siente lo que haces

**Versión 0.1.0** · Windows · Gratis

---

## 🧡 Conoce a Clawde

Clawde es un pequeño compañero naranja que vive en tu escritorio y **reacciona en tiempo real a lo que estás haciendo**. No es un widget estático ni un adorno: observa tu pantalla, entiende en qué aplicación estás, y cambia de pose, accesorio y ánimo para acompañarte.

Mientras programas, se pone sus gafas y aplaude cuando escribes rápido. Mientras juegas a Hitman, se tira al suelo en modo sigilo con chaleco táctico y binoculares. Mientras chateas en Discord, se relaja en su mini-sofá con auriculares. Y cuando no haces nada… hace sus propias cositas: estornuda, saluda, persigue un bicho imaginario o se queda pensando.

Es como tener un Tamagotchi que **no necesita que lo alimentes** — solo que lo dejes vivir contigo mientras trabajas, juegas o navegas.

---

## ✨ Lo que hace

### 🎯 Reacciona a tus aplicaciones
Clawde detecta automáticamente qué tienes abierto y se transforma:

- **Programando** (VS Code, PyCharm, IntelliJ, Sublime) → gafas de nerd, taburete y un tablero holográfico con código. ¿Escribes rápido? Aplaude emocionado.
- **Chateando** (Discord, Slack, Teams) → mini-sofá, auriculares con micro y burbuja de conversación.
- **Navegando** (Chrome, Edge, Firefox, Brave, Opera) → lupa gigante sobre una cinta transportadora de páginas.
- **Redes sociales** (Twitter/X, Instagram, Facebook, TikTok, Reddit) → mini-teléfono en mano, alternando caras de shock y risa.
- **Creando arte** (Photoshop, Blender, GIMP) → su cuerpo cambia de color sin parar, con paleta y pincel.
- **Escribiendo** (Notepad, Word) → pluma estilográfica gigante con gota de tinta.
- **Explorando archivos** → se asoma curioso a un archivero con los cajones abiertos.
- **Pantalla completa** (cine, vídeos, juegos) → se sienta atento mirando hacia arriba, asintiendo de vez en cuando.

### 🎮 Modos gamer dedicados
- **Hitman 3** → se pone en posición prona con chaleco táctico verde, gafas de sol y binoculares. Modo sigilo activado.
- **Cyberpunk 2077** → paneles verdes flotantes estilo Matrix con cables conectados a su cabecita. Netrunning puro.

### 🎲 Hace sus propias cosas
Cuando estás tranqui, Clawde no se queda parado. Cada poco rato decide hacer algo por su cuenta:

- 🤧 **Estornudar** con una pequeña salpicadura
- 👋 **Saludarte** agitando el bracito
- 🙆 **Estirarse** abriendo los brazos
- 🪰 **Perseguir un bicho** imaginario que zumba sobre su cabeza (¡sus ojos lo siguen!)
- 💪 **Hacer ejercicio** con jumping jacks y gotita de sudor
- 🥱 **Bostezar** con la boca abierta y "Zzz" flotando
- 🌀 **Dar una vuelta** completa con arcos de movimiento
- 🤔 **Quedarse pensando** con un "?" flotante sobre su cabeza

### 💖 Interactúa con él
- **Acarícialo** → haz clic y mantén sobre Clawde. Ronroneará con corazones flotantes y su ánimo subirá.
- **Muévelo** → arrástralo a cualquier rincón de la pantalla. Se agitará con líneas de velocidad mientras lo mueves.
- **Mira su panel** → a su izquierda flota un panel con su estado actual y su barra de ánimo. Puedes colapsarlo si quieres minimalismo.

### 😊 Sistema de ánimo
Clawde tiene una barra de **Mood** que sube cuando lo acaricias y vuelve sola a neutro con el tiempo. Si está muy feliz, puede arrancar un **baile espontáneo** con chispas de colores. Sin hambre, sin sueño, sin obligaciones: solo buen rollo.

---

## 🎨 Diseño

- **Estética voxel / pixel-art** — bloques nítidos sin antialiasing, con brillo y sombra que imitan el aspecto de una figura impresa en 3D.
- **Naranja cálido** (#E47448) fiel al personaje original.
- **Siempre visible** — flota por encima de todas las ventanas pero **no aparece en la barra de tareas** ni interrumpe tu flujo de trabajo.
- **Ligero** — consume recursos mínimos y no ralentiza tu equipo.

---

## 🔒 Privacidad

Clawde **solo observa lo necesario** para saber en qué aplicación estás y si hay actividad de teclado/ratón. 

- ✅ Todo el procesamiento es **local**, en tu máquina.
- ✅ **No envía nada** a internet, servidores ni terceros.
- ✅ No registra lo que escribes, solo detecta *que* estás escribiendo.
- ✅ No requiere cuenta, login ni conexión a red.
- ✅ Código fuente disponible para auditoría.

---

## ⚙️ Requisitos

- **Windows 10 / 11** (64 bits)
- **~50 MB** de espacio en disco
- **Sin dependencias externas** — el ejecutable `Clawde.exe` es autocontenido. No necesitas instalar Python ni nada más.

---

## 🚀 Cómo usarlo

1. Descarga `Clawde.exe`.
2. Haz doble clic. Listo.
3. Verás a Clawde aparecer en la esquina inferior derecha de tu pantalla.
4. Déjalo vivir ahí mientras trabajas, juegas o navegas. O arrástralo donde prefieras.
5. Para cerrar: simplemente cierra el proceso desde el administrador de tareas, o añade un acceso directo con cierre programado.

**Tip:** Añade `Clawde.exe` a la carpeta de inicio de Windows (`shell:startup`) si quieres que te acompañe cada vez que enciendes el equipo.

---

## 🐛 Cosas que debes saber (v0.1.0)

- Es la **primera versión pública**. Puede haber estados que aún no reaccionen a alguna app concreta — si usas algo que Clawde ignora, ¡avísanos!
- La detección de redes sociales se basa en palabras clave del título de la ventana; algunos sitios pueden no dispararla si usan títulos genéricos.
- El renderizado es intencionadamente pixelado/voxel — no es un bug, es el estilo.
- En esta versión no hay configuración persistente (posición, tamaño). Vuelve a la esquina inferior derecha al reiniciar.

---

## 🗺️ Próximas versiones (roadmap)

- 🎨 Skins y colores personalizables
- 💾 Guardar posición y preferencias entre sesiones
- 🎵 Reacciones a música (Spotify, YouTube Music)
- 🌙 Modo nocturno automático
- 🐾 Sonidos opcionales (ronroneos, estornudos, bips)
- 🪟 Soporte nativo para macOS y Linux
- 🎁 Más comportamientos aleatorios y animaciones festivas (Navidad, Halloween, etc.)

---

## 💬 Feedback

¿Clawde te hizo sonreír? ¿Se quedó quieto cuando esperabas que reaccionara? ¿Quieres que reconozca tu editor, juego o app favorita? 

Las sugerencias son bienvenidas — este bichito crece con quienes lo usan.

---

*Hecho con cariño para acompañarte mientras haces lo tuyo.* 🧡