# Especificación Técnica — GMC

## 1. Objetivo del Sistema

Consolidar fuentes de datos musicales heterogéneas (bookmarks HTML, Shazam CSV, exportación GDPR de Spotify, archivos TXT, Telegram) en una base de datos relacional única, enriquecer cada entrada con metadatos estructurados desde MusicBrainz (datos canónicos) y Last.fm (géneros), y exponerlas a través de una API REST consumida por un dashboard web.

---

## 2. Arquitectura

El sistema sigue un patrón **ETL + API + Worker**, desacoplado mediante una cola de mensajes. Opera completamente en local mediante Docker Compose.

### Componentes principales

**API Service (FastAPI):** Punto de entrada HTTP. Expone endpoints REST para el frontend y recibe el webhook de Telegram. No realiza operaciones costosas de forma síncrona.

**Worker (Celery):** Proceso separado que consume tareas de la cola Redis. Responsable de consultar MusicBrainz y Last.fm, normalizar metadatos y actualizar el estado de los registros. Gestiona el rate limit de MusicBrainz (1 req/s por política) sin bloquear la API.

**ETL Scripts:** Scripts de línea de comandos para la ingesta batch inicial. Se ejecutan una sola vez (o a demanda) contra los archivos históricos y no forman parte del servidor API.

**PostgreSQL:** Fuente de verdad. Almacena tanto los registros crudos (`sources`) como los normalizados (`tracks`, `artists`).

**Redis:** Message broker para Celery. No persiste estado de negocio.

---

## 3. Fuentes de Datos

| Fuente                                      | Formato      | Parser            | Mecanismo de obtención                       |
| ------------------------------------------- | ------------ | ----------------- | -------------------------------------------- |
| YouTube / web                               | HTML         | `bookmarks.py`    | Exportación de marcadores del navegador      |
| Shazam                                      | CSV          | `shazam.py`       | App → Exportar historial                     |
| Spotify                                     | JSON         | `spotify_gdpr.py` | Exportify (OAuth oficial) o GDPR export      |
| Manual (SoundCloud, Bandcamp, radios, etc.) | TXT          | `txt_manual.py`   | Archivos propios, formato `Artista - Título` |
| Telegram                                    | Webhook HTTP | API webhook       | Bot recibe mensajes en tiempo real           |

---

## 4. Modelo de Datos

### Tabla: `sources`

Registro crudo de cualquier entrada al sistema, independiente de su origen.

| Columna        | Tipo        | Descripción                                        |
| -------------- | ----------- | -------------------------------------------------- |
| `id`           | UUID PK     | Identificador único                                |
| `raw_text`     | TEXT        | Texto o URL original recibida                      |
| `source_type`  | ENUM        | `shazam`, `bookmark`, `spotify`, `txt`, `telegram` |
| `status`       | ENUM        | `pending`, `processed`, `failed`, `manual_review`  |
| `created_at`   | TIMESTAMPTZ | Fecha de ingesta                                   |
| `processed_at` | TIMESTAMPTZ | Fecha de procesamiento (nullable)                  |
| `error_detail` | TEXT        | Descripción del error si `status = failed`         |

### Tabla: `artists`

| Columna      | Tipo             | Descripción                                        |
| ------------ | ---------------- | -------------------------------------------------- |
| `id`         | UUID PK          |                                                    |
| `mbid`       | VARCHAR UNIQUE   | MusicBrainz Artist ID (nullable si no se encontró) |
| `name`       | VARCHAR NOT NULL | Nombre canónico según MusicBrainz                  |
| `created_at` | TIMESTAMPTZ      |                                                    |

### Tabla: `tracks`

| Columna           | Tipo              | Descripción                           |
| ----------------- | ----------------- | ------------------------------------- |
| `id`              | UUID PK           |                                       |
| `source_id`       | UUID FK → sources | Origen del registro                   |
| `mbid`            | VARCHAR UNIQUE    | MusicBrainz Recording ID (nullable)   |
| `title`           | VARCHAR NOT NULL  | Título canónico                       |
| `album`           | VARCHAR           |                                       |
| `album_cover_url` | TEXT              | URL de portada (obtenida vía Last.fm) |
| `duration_ms`     | INTEGER           |                                       |
| `genres`          | VARCHAR[]         | Array de géneros obtenidos de Last.fm |
| `created_at`      | TIMESTAMPTZ       |                                       |

### Tabla: `track_artists` (relación N:M)

| Columna     | Tipo              |
| ----------- | ----------------- |
| `track_id`  | UUID FK → tracks  |
| `artist_id` | UUID FK → artists |

---

## 5. API REST

Base URL: `/api/v1`

| Método | Ruta                | Descripción                          |
| ------ | ------------------- | ------------------------------------ |
| `GET`  | `/health`           | Health check del servicio            |
| `GET`  | `/tracks`           | Lista paginada de tracks procesados  |
| `GET`  | `/tracks/{id}`      | Detalle de un track                  |
| `GET`  | `/artists`          | Lista paginada de artistas           |
| `GET`  | `/sources/pending`  | Entradas pendientes de procesamiento |
| `GET`  | `/sources/failed`   | Entradas con error o revisión manual |
| `POST` | `/webhook/telegram` | Receptor de mensajes del bot         |

### Paginación estándar

Todos los endpoints de listado aceptan `?limit=20&offset=0`. El response incluye `total`, `limit`, `offset` e `items`.

---

## 6. Integraciones Externas

### MusicBrainz API — Enriquecimiento principal

MusicBrainz es una base de datos musical comunitaria y abierta. No requiere autenticación, pero su política exige un `User-Agent` identificativo y un rate limit de máximo 1 solicitud/segundo.

Se usa la librería oficial `musicbrainzngs` que gestiona el rate limiting automáticamente.

**Configuración obligatoria:**

```python
musicbrainzngs.set_useragent("gmc", "0.1.0", "contacto@email.com")
```

**Endpoint utilizado:** búsqueda de recordings por texto libre.

**Campos extraídos:** `id` (MBID), `title`, `length` (duración en ms), `release-list[0].title` (álbum), `artist-credit[].artist.id`, `artist-credit[].artist.name`.

**Manejo de errores:**

- Sin resultados → `status = manual_review`
- `ResponseError` / timeout → `status = failed`, registrar `error_detail`
- Rate limit inherente: el worker procesa las tareas secuencialmente para respetar 1 req/s

### Last.fm API — Géneros y portadas de álbum

Last.fm complementa a MusicBrainz con etiquetas de género (folksonomy) y URLs de imágenes de álbum. Requiere API key gratuita.

**Endpoints utilizados:**

- `track.getInfo` → géneros (tags), URL de portada del álbum
- `artist.getInfo` → tags del artista como fallback de género

**Manejo de errores:**

- Track no encontrado → géneros vacíos, `album_cover_url = null` (no bloquea el procesamiento)
- `error 29` (rate limit) → retry con backoff exponencial (Celery retry)

### Flujo de enriquecimiento combinado

```plaintext
source (pending)
    │
    ▼
MusicBrainz search(raw_text)
    ├─ encontrado → extraer MBID, título, álbum, artistas, duración
    └─ no encontrado → status = manual_review (fin)
    │
    ▼
Last.fm track.getInfo(artista, título)
    ├─ encontrado → añadir géneros y album_cover_url
    └─ no encontrado → continuar sin esos campos (no es error crítico)
    │
    ▼
Upsert en tracks + artists → source.status = processed
```

### Telegram Bot API — Webhook

El bot recibe cualquier mensaje de texto. Si el texto contiene una URL reconocida (youtube.com, soundcloud.com, bandcamp.com, spotify.com), se guarda en `sources`. De lo contrario, se intenta usar el texto completo como query de búsqueda. El bot responde de inmediato con confirmación; el procesamiento ocurre en background vía Celery.

---

## 7. ETL — Parsers por Fuente

### `bookmarks.py` (HTML)

- Usa `BeautifulSoup` para extraer `<a href>` de archivos HTML de exportación de marcadores.
- Filtra por dominios relevantes: `youtube.com`, `soundcloud.com`, `bandcamp.com`, `music.apple.com`.
- `raw_text` = URL; la query de búsqueda se construye a partir del título del `<a>` limpiando sufijos comunes (`" - YouTube"`, `"(Official Video)"`, etc.) con regex.

### `shazam.py` (CSV)

- Parsea el CSV oficial de Shazam (`Title`, `Artist`, `Date`).
- Maneja columnas faltantes y valores nulos sin excepción no controlada.
- `raw_text` = `f"{artist} {title}"` para usar directamente como query.

### `spotify_gdpr.py` (JSON)

- Parsea el JSON de Exportify o la exportación GDPR de Spotify.
- Campos usados: `trackName`, `artistName`.
- `raw_text` = `f"{artistName} {trackName}"`.

### `txt_manual.py` (TXT)

- Formato esperado: una entrada por línea, `Artista - Título` o `Título - Artista`.
- Intenta separar por `-`; si hay ambigüedad, guarda la línea completa como `raw_text` para que MusicBrainz resuelva.
- Ignora líneas en blanco y líneas que comiencen con `#` (comentarios).

---

## 8. Decisiones de Diseño

**UUIDs sobre IDs secuenciales:** Facilita merges entre entornos y evita exposición de volumen de datos en la URL de la API.

**Tabla `sources` como buffer:** Desacopla la ingesta del enriquecimiento. Cualquier dato que entre al sistema queda registrado aunque el procesamiento falle.

**MusicBrainz + Last.fm en lugar de Spotify API:** Spotify revocó el acceso libre para proyectos independientes. MusicBrainz provee IDs estables y datos canónicos bajo licencia abierta; Last.fm añade géneros y portadas. Ambos son gratuitos sin restricciones para uso personal.

**Celery en lugar de `asyncio` puro para el worker:** Las tareas de enriquecimiento tienen que respetar rate limits externos (1 req/s en MusicBrainz) y deben reintentarse de forma controlada. Celery provee retry con backoff, dead-letter queue y visibilidad de estado sin implementación manual.

**`genres` como `VARCHAR[]`:** PostgreSQL soporta arrays nativamente; evita una tabla de join adicional para una relación que en este contexto es de solo lectura y no requiere normalización estricta.

**Alembic para migraciones:** El esquema evolucionará. Manejar cambios con SQL crudo es error-prone en proyectos con múltiples entornos.
