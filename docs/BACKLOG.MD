# Product Backlog — GMC

## Workflow de Trabajo (Scrum-lite)

### Convenciones generales

**Duración de sprint:** 1–2 semanas según disponibilidad.

**Ramas Git:** `feature/GMC-{ID}-{descripcion-corta}` → PR hacia `main`.

**Commits:** Conventional Commits — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`.

### Definition of Done (DoD)

Una historia se considera terminada cuando:

- El código corre sin errores en el entorno Docker local.
- Está mergeado en `main` con al menos un commit descriptivo.
- El `README.md` o la sección correspondiente de este backlog refleja el cambio si es relevante.
- Sigue las convenciones de estilo (PEP 8 + type hints para Python, ESLint standard para JS).

### Ceremonias adaptadas (trabajo individual)

**Sprint Planning (30 min):** Seleccionar historias del backlog, estimar en puntos de historia simples (1, 2, 3) y moverlas a "En curso".

**Daily async (5 min):** Nota rápida en el tablero: ¿qué avancé? ¿qué sigue? ¿hay algún bloqueador?

**Sprint Review (30 min):** Demo personal — probar endpoints con un cliente HTTP, revisar la BD con un cliente SQL.

**Retrospectiva (15 min):** ¿Qué salió bien? ¿Qué me frenó? Una acción de mejora concreta para el siguiente sprint.

---

## Épica 1: Infraestructura y Persistencia de Datos

*Objetivo: Base del proyecto operativa. Al finalizar esta épica, la BD está levantada, modelada y accesible desde FastAPI.*

---

**GMC-01 · Entorno local con Docker Compose**

Como desarrollador, quiero orquestar PostgreSQL y Redis en contenedores para tener un entorno de desarrollo reproducible.

Criterios de aceptación:
- `docker-compose.yml` en la raíz levanta PostgreSQL 15, Redis y el worker Celery sin errores.
- Las credenciales se leen exclusivamente desde `.env` (el archivo `.env.example` se commitea, `.env` está en `.gitignore`).
- Los datos de PostgreSQL persisten en un volumen Docker entre reinicios.

---

**GMC-02 · Esqueleto de FastAPI y conexión a BD**

Como desarrollador, quiero el punto de entrada de la API configurado y conectado a la base de datos.

Criterios de aceptación:
- `GET /health` responde `{"status": "ok", "db": "connected"}`.
- La sesión de base de datos se inyecta vía dependencia (`Depends`), no como variable global.
- Si PostgreSQL no está disponible, la API responde 503 con mensaje de error explícito.

---

**GMC-03 · Modelos ORM y migraciones con Alembic**

Como desarrollador, quiero definir el esquema relacional en SQLAlchemy y versionarlo con Alembic.

Criterios de aceptación:
- Modelos `Source`, `Track`, `Artist`, `TrackArtist` definidos según la SPEC.
- Campo `genres` en `Track` definido como `ARRAY(String)` en SQLAlchemy.
- `alembic upgrade head` crea todas las tablas con PKs, FKs y constraints correctamente.
- La primera revisión de Alembic está commiteada en el repositorio.

---

## Épica 2: Motor ETL Histórico

*Objetivo: Importar el historial acumulado (archivos estáticos) a la tabla `sources`.*

---

**GMC-04 · Parser de bookmarks HTML**

Como usuario, quiero un script que extraiga URLs musicales desde el archivo HTML exportado de mi navegador.

Criterios de aceptación:
- Script en Python usando `BeautifulSoup`.
- Filtra y conserva solo URLs de dominios relevantes: `youtube.com`, `soundcloud.com`, `bandcamp.com`, `music.apple.com`.
- Limpia el texto del `<a>` con regex para remover sufijos como `" - YouTube"`, `"(Official Video)"`, `"(Official Music Video)"`, `" Lyrics"`.
- Retorna una lista de dicts con al menos `raw_text` y `source_type = "bookmark"`.
- Maneja archivos malformados sin fallar silenciosamente.

---

**GMC-05 · Parser de historial Shazam (CSV)**

Como usuario, quiero un script que lea el CSV de Shazam y extraiga título, artista y fecha de descubrimiento.

Criterios de aceptación:
- Usa `pandas` o el módulo `csv` estándar.
- Maneja columnas faltantes o valores nulos sin lanzar excepción no controlada.
- `raw_text` = concatenación `{artista} {título}` para usar como query.
- `source_type = "shazam"`.

---

**GMC-06 · Parser de exportación Spotify (JSON)**

Como usuario, quiero un script que lea el JSON de Exportify o la exportación GDPR de Spotify.

Criterios de aceptación:
- Parsea el JSON de Exportify (campos: `Track Name`, `Artist Name(s)`) y el GDPR de Spotify (campos: `trackName`, `artistName`); el script detecta automáticamente el formato por las claves presentes.
- `raw_text` = `"{artistName} {trackName}"`.
- `source_type = "spotify"`.
- Si el JSON está vacío o malformado, imprime un error descriptivo sin lanzar excepción no controlada.

---

**GMC-07 · Parser de archivos TXT manuales**

Como usuario, quiero un script que lea archivos de texto plano con entradas en formato libre.

Criterios de aceptación:
- Formato soportado: `Artista - Título` (una entrada por línea).
- Ignora líneas en blanco y líneas que comiencen con `#`.
- Si una línea no contiene ` - `, se guarda la línea completa como `raw_text` sin modificar (MusicBrainz intentará resolverlo).
- `source_type = "txt"`.

---

**GMC-08 · Ingesta batch a `sources`**

Como desarrollador, quiero que los parsers inserten los registros directamente en la BD con estado `pending`.

Criterios de aceptación:
- Usa bulk insert de SQLAlchemy para eficiencia.
- Si un `raw_text` ya existe en `sources` con el mismo `source_type`, se ignora el duplicado (upsert o skip).
- Al finalizar, imprime un resumen: registros insertados, duplicados ignorados, errores.

---

## Épica 3: Core API y Enriquecimiento

*Objetivo: El sistema puede buscar metadatos reales en MusicBrainz y Last.fm, y exponerlos vía API REST.*

---

**GMC-09 · Cliente MusicBrainz**

Como sistema, necesito un cliente que busque metadatos de un track en MusicBrainz respetando el rate limit.

Criterios de aceptación:
- Usa la librería `musicbrainzngs`.
- `set_useragent` configurado con nombre de app, versión y contacto leídos desde variables de entorno.
- Función `search_recording(query: str) -> RecordingData | None` con tipo de retorno explícito.
- Si no hay resultados, retorna `None`.
- Si hay error de red o timeout, lanza excepción tipada (no genérica).

---

**GMC-10 · Cliente Last.fm**

Como sistema, necesito un cliente que obtenga géneros y portada de álbum desde Last.fm.

Criterios de aceptación:
- Usa `httpx` (async) o `requests` para llamar a `track.getInfo`.
- API key leída desde variable de entorno.
- Función `get_track_info(artist: str, title: str) -> LastFmTrackInfo | None`.
- Si el track no se encuentra o la respuesta está incompleta, retorna `None` sin lanzar excepción (es enriquecimiento secundario, no crítico).

---

**GMC-11 · Endpoints CRUD básicos**

Como frontend, necesito endpoints para consultar la biblioteca.

Criterios de aceptación:
- `GET /api/v1/tracks` con paginación (`limit`, `offset`) y respuesta con `total`.
- `GET /api/v1/tracks/{id}` con detalle completo incluyendo artistas y géneros.
- `GET /api/v1/artists` con paginación.
- Respuestas validadas con schemas Pydantic.

---

## Épica 4: Procesamiento Asíncrono

*Objetivo: El enriquecimiento de datos corre en background sin bloquear la API.*

---

**GMC-12 · Configuración de Celery + Redis**

Como desarrollador, quiero un worker Celery funcional usando Redis como broker.

Criterios de aceptación:
- El worker arranca como servicio en `docker-compose.yml`.
- Se puede despachar y confirmar la ejecución de una tarea de prueba desde la API.
- Los logs del worker son visibles con `docker compose logs worker`.

---

**GMC-13 · Tarea de enriquecimiento principal**

Como sistema, quiero una tarea que procese un registro `pending` de `sources`, lo enriquezca con MusicBrainz y Last.fm, y actualice la BD.

Criterios de aceptación:
- Flujo: `source.status = pending` → buscar en MusicBrainz → si hay resultado, buscar en Last.fm → crear/actualizar `track` y `artists` → `source.status = processed`.
- Si MusicBrainz no encuentra la canción: `source.status = manual_review`.
- Si Last.fm no devuelve datos: el track se guarda igualmente con `genres = []` y `album_cover_url = null`.
- Si ocurre un error inesperado: `source.status = failed`, `source.error_detail` registra el mensaje.
- Usa transacciones de BD para evitar estados inconsistentes.
- Reintento automático con backoff en caso de rate limit (error 29) de Last.fm.

---

## Épica 5: Ingestión Continua (Telegram Bot)

*Objetivo: Registrar canciones nuevas en tiempo real desde el celular o la laptop.*

---

**GMC-14 · Registro del bot y webhook**

Como usuario, quiero enviar mensajes a un bot de Telegram y que mi backend los reciba instantáneamente.

Criterios de aceptación:
- Bot registrado en BotFather.
- `POST /api/v1/webhook/telegram` recibe y valida el payload de Telegram.
- El webhook apunta al servidor local vía ngrok durante desarrollo.

---

**GMC-15 · Encolamiento desde Telegram**

Como sistema, cuando reciba un mensaje con URL o texto musical, debo guardarlo y disparar el enriquecimiento.

Criterios de aceptación:
- El bot responde "✓ Recibido, procesando..." de forma inmediata.
- El mensaje se inserta en `sources` con `source_type = "telegram"` y `status = pending`.
- La tarea Celery (GMC-13) se dispara automáticamente.
- URLs reconocidas: `youtube.com`, `soundcloud.com`, `bandcamp.com`, `open.spotify.com`.

---

## Épica 6: Interfaz de Usuario (Frontend)

*Objetivo: Dashboard web para explorar y gestionar la biblioteca.*

---

**GMC-16 · Setup de React + Vite + Tailwind**

Como desarrollador, quiero el proyecto frontend inicializado y configurado.

Criterios de aceptación:
- Proyecto creado con `create-vite` (template React).
- Tailwind CSS configurado y funcional.
- Corre en `http://localhost:5173` sin errores.
- Proxy a `http://localhost:8000` configurado en `vite.config.js` para evitar CORS en desarrollo.

---

**GMC-17 · Dashboard de biblioteca musical**

Como usuario, quiero ver una cuadrícula con mis canciones procesadas, con título, artista, género y portada del álbum.

Criterios de aceptación:
- Consume `GET /api/v1/tracks` con paginación.
- Muestra la portada del álbum cuando está disponible; imagen placeholder cuando no.
- Muestra géneros como chips/etiquetas.
- Muestra spinner durante carga y mensaje de error en caso de fallo de red.
- Paginación funcional.

---

**GMC-18 · Vista de pendientes y errores**

Como usuario, quiero ver qué canciones fallaron o están pendientes para gestionarlas manualmente.

Criterios de aceptación:
- Tabla con registros de `sources` filtrada por `status = failed` o `manual_review`.
- Botón para reintentar el enriquecimiento (dispatcha la tarea Celery nuevamente).
- Campo para ingresar metadatos manualmente si MusicBrainz no encontró el track.
