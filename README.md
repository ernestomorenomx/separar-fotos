# separar-fotos

Separa fotos por **cámara** (EXIF Make + Model) y por **fecha de captura**. Copia, nunca mueve, y deja un reporte de lo que hizo con cada archivo.

Nació de un problema real: un disco externo con miles de fotos de varias cámaras y años, mezcladas y duplicadas.

## Requisitos

- Python 3.9 o superior (sin librerías externas)
- [ExifTool](https://exiftool.org): `brew install exiftool` (macOS) o `apt install libimage-exiftool-perl` (Linux)

## Uso

```bash
# 1. Simular primero: no copia nada
python separar_fotos.py --origen /ruta/fotos --destino ./organizadas \
    --modelo "DMC-LZ7" --desde 2006-01-01 --hasta 2008-12-31 --dry-run

# 2. Correr de verdad
python separar_fotos.py --origen /ruta/fotos --destino ./organizadas \
    --modelo "DMC-LZ7" --desde 2006-01-01 --hasta 2008-12-31
```

| Opción | Qué hace |
|---|---|
| `--origen`, `--destino` | Obligatorias. Se busca en subcarpetas. |
| `--modelo` | Texto a buscar en "Make Model" (p. ej. `DMC-LZ7`). Sin él se aceptan todas las cámaras. |
| `--desde`, `--hasta` | Rango de fechas `AAAA-MM-DD`. |
| `--estructura` | `plano`, `anio` (por omisión) o `anio-mes`. |
| `--orden` | `nombre` (por omisión), `reciente` (del año más reciente al más antiguo) o `antiguo`. |
| `--sobrescribir` | Reemplaza los archivos que ya existan en el destino. No borra nada ni toca el origen; se niega si el destino está dentro del origen o lo contiene. |
| `--formato` | Reporte en `csv` (por omisión) o `json`. |
| `--reporte` | Ruta del reporte. |
| `--dry-run` | Simula. |
| `--sin-barra` | Oculta la barra de progreso (se oculta sola si la salida no es una terminal). |
| `--aviso` | Suena la campana de la terminal al terminar. |

## El reporte

Una fila por foto: `archivo_origen`, `archivo_destino`, `camara`, `fecha`, `fuente_fecha`, `estado`, `mensaje`.

- `fuente_fecha` es `exif` o `archivo`. Si es `archivo`, la foto no tenía fecha EXIF y se usó la fecha de modificación: conviene revisarla a mano.
- `estado`: `copiado`, `sobrescrito`, `simulado`, `omitido_camara`, `omitido_fecha`, `omitido_existente`, `error_lectura`, `error_copia`.

El código de salida es 1 si hubo errores de lectura o copia.

## Decisiones de diseño

- **Copia, no mueve.** Los originales no se tocan.
- **Nombres repetidos:** los resuelve un solo hilo antes de copiar (`IMG_1_A1.jpg`), así que dos fotos con el mismo nombre nunca se sobrescriben.
- **Se puede repetir:** una segunda corrida no duplica lo que ya se copió.
- **ExifTool por lotes** de 200 archivos, con reintento archivo por archivo si un lote falla.
- **Se ignoran** los archivos `._*` que macOS crea en discos externos.

## Rendimiento

Probado con una fototeca personal de unas 44,000 fotos de varias cámaras y años. La extracción más exigente (la que lee y copia más archivos) terminó en menos de cinco minutos. El script corrió directamente en una Mac con chip M4 y 16 GB de memoria. Las fotos estaban en un SSD NVMe de 1 TB dentro de una carcasa Orico con conexión USB-C. El tiempo depende del disco, de la conexión (USB o red) y de cuántas fotos coincidan con el filtro; es una medición de un equipo, no una garantía.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan un `exiftool` falso, así que corren sin tener ExifTool instalado.

## Privacidad

Los reportes contienen rutas de tu computadora. No los subas al repositorio (ver `.gitignore`).
