# separar-fotos

Organiza tus fotos por cámara y por fecha sin tocar los archivos originales.

La idea es simple: en lugar de tener una carpeta llena de fotos mezcladas, el programa las revisa, identifica la cámara que las tomó y las copia en carpetas ordenadas por año, mes o semana.

Esto sirve si tienes un disco duro con miles de fotos de varias cámaras y quieres separarlas de forma clara, sin perder nada.

## ¿Para quién sirve?

- Si tienes un disco duro con fotos viejas mezcladas.
- Si usas varias cámaras o móviles distintos.
- Si quieres organizar una colección grande sin perder el original.
- Si prefieres una herramienta con interfaz gráfica y sin complicarte con terminales.

## ¿Qué hace exactamente?

- Recorre tu carpeta de origen y busca fotos.
- Lee la información EXIF para saber:
  - qué cámara hizo la foto
  - en qué fecha se tomó
- Puede filtrar por:
  - una cámara
  - varias cámaras a la vez
  - rango de fechas
- Crea una copia en una carpeta destino ordenada por:
  - año
  - año/mes
  - año/semana
  - sin subcarpetas
- Genera un informe con lo que hizo: copiado, ignorado, simulado, error, etc.

Importante: nunca mueve tus fotos originales. Siempre crea copias.

## Requisitos

Necesitas Python 3.9 o superior.

Además, debes tener instalado ExifTool:

- macOS: `brew install exiftool`
- Ubuntu/Debian: `sudo apt install libimage-exiftool-perl`
- Windows: descarga la versión de ExifTool y asegúrate de que esté en el PATH

## La forma más fácil de usar: interfaz gráfica

Puedes abrir la aplicación con una sola orden:

```bash
python app.py
```

### Flujo recomendado de la interfaz

1. Selecciona la carpeta con tus fotos.
2. Pulsa "Inventariar cámaras".
3. La app busca qué cámaras aparecen en ese disco.
4. Elige una o varias cámaras.
5. Opcionalmente pon fechas para filtrar.
6. Elige cómo quieres organizar:
   - año
   - año/mes
   - año/semana
   - plano
7. Pulsa "Organizar fotos".
8. El programa crea las copias y genera el reporte.

### Ventajas de la interfaz

- No necesitas recordar comandos.
- Puedes seleccionar cámaras desde una lista.
- Puedes probar primero sin copiar nada usando modo de prueba.
- Puedes guardar el reporte en CSV o JSON.

## También puedes usarlo desde la terminal

### 1) Probar sin copiar nada

```bash
python separar_fotos.py --origen /ruta/tu/coleccion --destino ./organizadas --modelo "DMC-LZ7" --dry-run
```

Esto solo simula la operación y no escribe nada en el destino.

### 2) Organizar solo una cámara

```bash
python separar_fotos.py --origen /ruta/tu/coleccion --destino ./organizadas --modelo "DMC-LZ7" --desde 2006-01-01 --hasta 2008-12-31
```

### 3) Organizar varias cámaras a la vez

```bash
python separar_fotos.py --origen /ruta/tu/coleccion --destino ./organizadas --modelo "DMC-LZ7" --modelo "IXUS" --modelo "Sony" --desde 2010-01-01 --hasta 2024-12-31
```

### 4) Ordenar por semana en vez de por mes

```bash
python separar_fotos.py --origen /ruta/tu/coleccion --destino ./organizadas --estructura anio-semana
```

Esto crea carpetas tipo:

```text
organizadas/
  2024/
    semana-01/
    semana-02/
```

### 5) Ver qué cámaras hay en tu disco sin copiar nada

```bash
python separar_fotos.py --origen /ruta/tu/coleccion --inventario-camaras
```

Esto muestra algo como:

```text
Panasonic DMC-LZ7    1423
Canon IXUS           870
Sony DSC-HX90       340
```

## Cómo se organizan las fotos

Por defecto, el programa usa esta estructura:

```text
organizadas/
  2024/
    01/
      foto1.jpg
      foto2.jpg
```

Si usas `anio-mes`, quedará así:

```text
organizadas/
  2024/
    01/
    02/
    12/
```

Si usas `anio-semana`, quedará así:

```text
organizadas/
  2024/
    semana-01/
    semana-15/
    semana-42/
```

## Qué es el reporte

El programa genera un archivo CSV o JSON con una línea por foto.

Cada fila incluye:

- archivo origen
- archivo destino
- cámara
- fecha
- fuente de la fecha
- estado
- mensaje

Ejemplo de una línea:

```csv
archivo_origen,archivo_destino,camara,fecha,fuente_fecha,estado,mensaje
/Volumes/DISCO/fotos/IMG_001.jpg,/Users/tu/organizadas/2024/01/IMG_001.jpg,Panasonic DMC-LZ7,2007-05-01 10:00:00,exif,copiado,
```

## Caso de uso real

Imagina que tienes un disco externo con fotos de:

- una cámara antigua
- un móvil viejo
- otra cámara de viajes
- miles de fotos mezcladas

El flujo sería:

1. Abres la app.
2. Seleccionas el disco externo.
3. La app te dice qué cámaras aparecen.
4. Seleccionas las cámaras que te interesan.
5. Fijas el rango desde/hasta si quieres.
6. El programa copia las fotos a la carpeta destino.
7. Al final tienes tus fotos ordenadas sin tocar el origen.

## Consejos útiles

- Antes de copiar todo, usa `--dry-run` o el modo prueba de la GUI.
- Si solo quieres revisar una cámara concreta, usa `--modelo`.
- Si quieres una organización más clara, usa `anio-mes`.
- Si quieres ver bloques de tiempo más pequeños, usa `anio-semana`.
- Revisa el reporte si alguna foto no se pudo leer.

## Solución de problemas

### ExifTool no está instalado

La app te lo dirá claramente. Instálalo y vuelve a probar.

### No veo ninguna cámara

- Revisa que la carpeta origen contenga fotos válidas.
- Asegúrate de que los archivos tengan extensión admitida.
- Comprueba que no sea una carpeta vacía.

### Las fotos no se copian

- Revisa el reporte generado.
- Mirá si hay errores de lectura o copia.
- Si el destino es una carpeta dentro del origen, el programa lo rechazará por seguridad.

## Seguridad y privacidad

- Los originales no se mueven ni se modifican.
- Las copias van solo a la carpeta destino que tú elijas.
- Los reportes pueden contener rutas de carpetas locales; guárdalos con cuidado.

## Licencia

Este proyecto se distribuye bajo la licencia MIT.

## Desarrollo

Si quieres colaborar o modificar la lógica:

```bash
python -m unittest discover -s tests -v
```

## En resumen

Este proyecto está pensado para que una persona normal pueda:

- seleccionar un disco duro
- detectar qué cámaras aparecieron ahí
- elegir las cámaras que quiere
- organizar fotos por tiempo
- sin perder los originales

Es una forma práctica de ordenar una galería grande sin complicaciones.


