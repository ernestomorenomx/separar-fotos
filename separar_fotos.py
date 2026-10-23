#!/usr/bin/env python3
"""Separa fotos por cámara y fecha de captura usando los metadatos EXIF.

Copia (nunca mueve) las fotos que coinciden con una o varias cámaras y un rango
 de fechas a una carpeta de destino, ordenadas por año o por año/mes, y escribe
 un reporte CSV o JSON con lo que hizo con cada archivo.

Requiere ExifTool instalado (https://exiftool.org). No usa librerías externas.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

EXTENSIONES = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic", ".orf", ".cr2", ".nef", ".raw"}
TAMANO_LOTE = 200
COLUMNAS = ["archivo_origen", "archivo_destino", "camara", "fecha", "fuente_fecha", "estado", "mensaje"]

log = logging.getLogger("separar_fotos")


@dataclass
class Registro:
    archivo_origen: str
    archivo_destino: str = ""
    camara: str = ""
    fecha: str = ""
    fuente_fecha: str = ""  # "exif" o "archivo" (fecha de modificación, si no hay EXIF)
    estado: str = ""  # copiado | sobrescrito | simulado | omitido_camara | omitido_fecha | omitido_existente | error_lectura | error_copia
    mensaje: str = ""


# --------------------------------------------------------------------------- Progreso


class Progreso:
    """Barra de progreso en la terminal, sin dependencias. Solo se dibuja si la salida
    es una terminal (así no ensucia logs ni pruebas)."""

    def __init__(self, total: int, etiqueta: str, activo: bool = True):
        self.total, self.etiqueta, self.hecho = total, etiqueta, 0
        self.activo = activo and total > 0 and sys.stderr.isatty()
        self._t0 = time.monotonic()
        self._ultimo = 0.0

    @staticmethod
    def _tiempo(segundos: float) -> str:
        m, s = divmod(int(segundos), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def avanzar(self, n: int = 1) -> None:
        self.hecho += n
        if not self.activo:
            return
        ahora = time.monotonic()
        if self.hecho < self.total and ahora - self._ultimo < 0.1:
            return  # no redibujar más de 10 veces por segundo
        self._ultimo = ahora
        fraccion = self.hecho / self.total
        lleno = int(30 * fraccion)
        transcurrido = ahora - self._t0
        faltante = transcurrido / fraccion - transcurrido if fraccion else 0
        sys.stderr.write(
            f"\r{self.etiqueta} [{'█' * lleno}{'░' * (30 - lleno)}] "
            f"{self.hecho}/{self.total} {fraccion:6.1%}  faltan {self._tiempo(faltante)}   "
        )
        sys.stderr.flush()

    def cerrar(self) -> None:
        if self.activo:
            sys.stderr.write("\n")
            sys.stderr.flush()


# --------------------------------------------------------------------------- ExifTool


def verificar_exiftool() -> None:
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        sys.exit("ExifTool no está instalado o no está en el PATH (macOS: brew install exiftool).")


def _leer_lote(rutas: list[Path]) -> dict[str, dict]:
    """Lee los metadatos de un lote de archivos con una sola llamada a ExifTool."""
    cmd = [
        "exiftool",
        "-json",
        "-Make",
        "-Model",
        "-DateTimeOriginal",
        "-CreateDate",
        "-ignoreMinorErrors",
        "-charset",
        "filename=utf8",
        "-@",
        "-",
    ]
    entrada = "\n".join(str(r) for r in rutas)
    res = subprocess.run(cmd, input=entrada, capture_output=True, text=True, encoding="utf-8")
    if not res.stdout.strip():
        raise RuntimeError(res.stderr.strip() or "ExifTool no devolvió datos")
    return {os.path.normpath(d["SourceFile"]): d for d in json.loads(res.stdout)}


def leer_metadatos(archivos: list[Path], hilos: int, barra: bool = False) -> dict[Path, dict | None]:
    """Devuelve {archivo: metadatos}; None si no se pudo leer ese archivo."""
    lotes = [archivos[i : i + TAMANO_LOTE] for i in range(0, len(archivos), TAMANO_LOTE)]

    def procesar(lote: list[Path]) -> dict[Path, dict | None]:
        try:
            datos = _leer_lote(lote)
        except Exception as e:  # el lote falló: reintentar archivo por archivo
            log.warning("Lote con error (%s); reintentando archivo por archivo", e)
            datos = {}
            for r in lote:
                try:
                    datos.update(_leer_lote([r]))
                except Exception:
                    pass
        return {r: datos.get(os.path.normpath(str(r))) for r in lote}

    resultado: dict[Path, dict | None] = {}
    progreso = Progreso(len(archivos), "Leyendo metadatos", barra)
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        for parcial in ex.map(procesar, lotes):
            resultado.update(parcial)
            progreso.avanzar(len(parcial))
    progreso.cerrar()
    return resultado


# --------------------------------------------------------------------------- Planeación


def parsear_fecha(valor) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:  # p. ej. "0000:00:00 00:00:00"
        return None


def describir(archivo: Path, meta: dict) -> tuple[str, datetime, str]:
    """Cámara (Make + Model), fecha de captura y de dónde salió la fecha."""
    camara = f"{meta.get('Make', '')} {meta.get('Model', '')}".strip()
    fecha = parsear_fecha(meta.get("DateTimeOriginal")) or parsear_fecha(meta.get("CreateDate"))
    if fecha:
        return camara, fecha, "exif"
    return camara, datetime.fromtimestamp(archivo.stat().st_mtime), "archivo"


def _es_el_mismo(origen: Path, destino: Path) -> bool:
    a, b = origen.stat(), destino.stat()
    return a.st_size == b.st_size and int(a.st_mtime) == int(b.st_mtime)


def _carpeta(destino: Path, fecha: datetime, estructura: str) -> Path:
    if estructura == "anio":
        return destino / f"{fecha.year}"
    if estructura == "anio-mes":
        return destino / f"{fecha.year}" / f"{fecha.month:02d}"
    if estructura == "anio-semana":
        iso_year, iso_week, _ = fecha.isocalendar()
        return destino / str(iso_year) / f"semana-{iso_week:02d}"
    return destino


def _clave_orden(archivo: Path, metadatos: dict, orden: str):
    """Clave para ordenar los archivos: por nombre, o por fecha de captura."""
    if orden == "nombre":
        return (str(archivo),)
    meta = metadatos.get(archivo)
    try:
        fecha = describir(archivo, meta)[1] if meta is not None else datetime.min
    except OSError:
        fecha = datetime.min
    return (fecha, str(archivo))


def normalizar_modelos(modelos: Iterable[str] | str | None) -> list[str]:
    """Acepta un string, una lista o una secuencia con varios modelos."""
    if modelos is None:
        return []
    if isinstance(modelos, str):
        items = [modelos]
    else:
        items = list(modelos)
    resultado: list[str] = []
    for item in items:
        for parte in str(item).split(","):
            valor = parte.strip()
            if valor:
                resultado.append(valor)
    return resultado


def coincide_con_modelo(camara: str, modelos: list[str]) -> bool:
    if not modelos:
        return True
    texto = camara.lower()
    return any(modelo.lower() in texto for modelo in modelos)


def inventario_camaras(origen: Path, hilos: int = 4, barra: bool = False) -> list[tuple[str, int]]:
    """Devuelve (camera_name, cantidad) ordenado por número de fotos."""
    archivos = escanear(origen)
    metadatos = leer_metadatos(archivos, hilos, barra)
    conteo: dict[str, int] = {}
    for archivo in archivos:
        meta = metadatos.get(archivo)
        if meta is None:
            continue
        camara, _, _ = describir(archivo, meta)
        if camara:
            conteo[camara] = conteo.get(camara, 0) + 1
    return sorted(conteo.items(), key=lambda elem: (-elem[1], elem[0]))


def planear(
    archivos: Iterable[Path],
    metadatos: dict,
    destino: Path,
    modelos: list[str] | None,
    desde: date | None,
    hasta: date | None,
    estructura: str,
    orden: str = "nombre",
    sobrescribir: bool = False,
) -> list[Registro]:
    """Decide qué pasa con cada archivo.

    Si modelos está informado, solo acepta archivos cuyo 'Make Model' contenga
    cualquiera de esos textos. Esto permite seleccionar varias cámaras a la vez.
    """
    reservados: set[Path] = set()
    registros: list[Registro] = []
    lista = sorted(archivos, key=lambda a: _clave_orden(a, metadatos, orden), reverse=(orden == "reciente"))
    modelos_norm = normalizar_modelos(modelos)
    for archivo in lista:
        reg = Registro(archivo_origen=str(archivo))
        registros.append(reg)
        meta = metadatos.get(archivo)
        if meta is None:
            reg.estado, reg.mensaje = "error_lectura", "ExifTool no pudo leer el archivo"
            continue
        camara, fecha, fuente = describir(archivo, meta)
        reg.camara, reg.fecha, reg.fuente_fecha = camara, fecha.isoformat(sep=" "), fuente

        if not coincide_con_modelo(camara, modelos_norm):
            reg.estado, reg.mensaje = "omitido_camara", f"cámara distinta o ausente ({camara or 'sin dato'})"
            continue
        if (desde and fecha.date() < desde) or (hasta and fecha.date() > hasta):
            reg.estado, reg.mensaje = "omitido_fecha", "fuera del rango de fechas"
            continue

        carpeta = _carpeta(destino, fecha, estructura)
        candidato, n = carpeta / archivo.name, 1
        while candidato in reservados or (candidato.exists() and not sobrescribir):
            if candidato.exists() and candidato not in reservados and _es_el_mismo(archivo, candidato):
                reg.archivo_destino, reg.estado = str(candidato), "omitido_existente"
                reg.mensaje = "ya estaba copiado en una corrida anterior"
                break
            candidato = carpeta / f"{archivo.stem}_A{n}{archivo.suffix}"
            n += 1
        else:
            reservados.add(candidato)
            reg.archivo_destino, reg.estado = str(candidato), "pendiente"
            if sobrescribir and candidato.exists():
                reg.mensaje = "reemplaza un archivo existente del destino"
    return registros


# --------------------------------------------------------------------------- Ejecución


def _copiar(reg: Registro) -> None:
    try:
        destino = Path(reg.archivo_destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        existia = destino.exists()
        shutil.copy2(reg.archivo_origen, destino)
        reg.estado = "sobrescrito" if existia else "copiado"
    except Exception as e:
        reg.estado, reg.mensaje = "error_copia", str(e)


def ejecutar(registros: list[Registro], dry_run: bool, hilos: int, barra: bool = False) -> None:
    pendientes = [r for r in registros if r.estado == "pendiente"]
    if dry_run:
        for r in pendientes:
            r.estado = "simulado"
        return
    progreso = Progreso(len(pendientes), "Copiando         ", barra)
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        for _ in ex.map(_copiar, pendientes):
            progreso.avanzar()
    progreso.cerrar()


def escribir_reporte(registros: list[Registro], ruta: Path, formato: str, config: dict) -> None:
    if formato == "json":
        ruta.write_text(
            json.dumps({"config": config, "registros": [asdict(r) for r in registros]}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        with ruta.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS)
            w.writeheader()
            w.writerows(asdict(r) for r in registros)


def escanear(origen: Path) -> list[Path]:
    # Se ignoran los archivos "._*" que macOS crea en discos externos.
    return [
        p
        for p in origen.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONES and not p.name.startswith("._")
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Separa fotos por cámara y fecha EXIF (copia, no mueve).")
    p.add_argument("--origen", type=Path, help="carpeta con las fotos (se busca en subcarpetas)")
    p.add_argument("--destino", type=Path, help="carpeta donde se copian las fotos que coinciden")
    p.add_argument(
        "--modelo",
        dest="modelos",
        action="append",
        default=[],
        help='texto a buscar en "Make Model", p. ej. "DMC-LZ7"; se puede repetir o separar por comas',
    )
    p.add_argument("--desde", type=date.fromisoformat, help="fecha mínima AAAA-MM-DD")
    p.add_argument("--hasta", type=date.fromisoformat, help="fecha máxima AAAA-MM-DD")
    p.add_argument(
        "--estructura",
        choices=["plano", "anio", "anio-mes", "anio-semana"],
        default="anio",
    )
    p.add_argument("--formato", choices=["csv", "json"], default="csv", help="formato del reporte")
    p.add_argument("--reporte", type=Path, help="ruta del reporte (por omisión reporte_fotos.csv/.json)")
    p.add_argument(
        "--orden",
        choices=["nombre", "reciente", "antiguo"],
        default="nombre",
        help="orden de proceso: por nombre, del año más reciente al más antiguo, o al revés",
    )
    p.add_argument(
        "--sobrescribir",
        action="store_true",
        help="reemplaza los archivos que ya existan en el destino (no borra nada ni toca el origen)",
    )
    p.add_argument("--hilos", type=int, default=4)
    p.add_argument("--dry-run", action="store_true", help="simula: no copia nada")
    p.add_argument("--sin-barra", action="store_true", help="no mostrar la barra de progreso")
    p.add_argument("--aviso", action="store_true", help="suena la campana de la terminal al terminar")
    p.add_argument(
        "--inventario-camaras",
        action="store_true",
        help="muestra qué cámaras aparecen en el origen y cuántas fotos hay por cada una; no copia nada",
    )
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    verificar_exiftool()
    if not args.origen or not args.origen.is_dir():
        if args.inventario_camaras and args.origen and not args.origen.is_dir():
            sys.exit(f"La carpeta de origen no existe: {args.origen}")
        if not args.origen:
            p.error("Debes indicar --origen")
        sys.exit(f"La carpeta de origen no existe: {args.origen}")

    if args.inventario_camaras:
        inventario = inventario_camaras(args.origen, args.hilos, barra=False)
        for camara, cantidad in inventario:
            print(f"{camara}\t{cantidad}")
        return 0

    if args.destino is None:
        p.error("Debes indicar --destino salvo que uses --inventario-camaras")

    origen, destino = args.origen.resolve(), args.destino.resolve()
    if args.sobrescribir and (destino == origen or origen in destino.parents or destino in origen.parents):
        sys.exit(
            "Con --sobrescribir el destino no puede ser igual, ni estar dentro, ni contener al origen: "
            "podría reemplazar tus fotos originales."
        )
    archivos = escanear(origen)
    log.info("%d imágenes encontradas en %s", len(archivos), origen)

    barra = not args.sin_barra
    metadatos = leer_metadatos(archivos, args.hilos, barra)
    registros = planear(
        archivos,
        metadatos,
        destino,
        args.modelos,
        args.desde,
        args.hasta,
        args.estructura,
        args.orden,
        args.sobrescribir,
    )
    ejecutar(registros, args.dry_run, args.hilos, barra)

    ruta = args.reporte or Path(f"reporte_fotos.{args.formato}")
    config = {k: str(v) for k, v in vars(args).items()}
    escribir_reporte(registros, ruta, args.formato, config)

    resumen: dict[str, int] = {}
    for r in registros:
        resumen[r.estado] = resumen.get(r.estado, 0) + 1
    log.info("Resumen: %s", resumen)
    log.info("Reporte: %s", ruta.resolve())
    if args.aviso:
        sys.stderr.write("\a")
    return 1 if any(r.estado.startswith("error") for r in registros) else 0


if __name__ == "__main__":
    sys.exit(main())
