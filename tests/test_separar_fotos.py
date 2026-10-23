"""Pruebas sin ExifTool real: se usa un 'exiftool' falso que lee los metadatos
de un archivo .meta.json junto a cada foto.  Ejecutar: python -m unittest -v"""
import csv
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import separar_fotos as sf  # noqa: E402

FALSO = '''#!/usr/bin/env python3
import sys, json, os
if "-ver" in sys.argv:
    print("12.0"); sys.exit(0)
out = []
for linea in sys.stdin.read().splitlines():
    meta = linea + ".meta.json"
    if os.path.exists(meta):
        d = json.load(open(meta)); d["SourceFile"] = linea; out.append(d)
print(json.dumps(out))
'''


class PruebasSeparar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        self.origen, self.destino = raiz / "origen", raiz / "destino"
        self.origen.mkdir()
        bin_ = raiz / "bin"
        bin_.mkdir()
        falso = bin_ / "exiftool"
        falso.write_text(FALSO)
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        self.path_original = os.environ["PATH"]
        os.environ["PATH"] = f"{bin_}{os.pathsep}{self.path_original}"
        self.raiz = raiz

    def tearDown(self):
        os.environ["PATH"] = self.path_original
        self.tmp.cleanup()

    def foto(self, ruta, make="Panasonic", model="DMC-LZ7", fecha="2007:05:01 10:00:00", contenido=b"x"):
        p = self.origen / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenido)
        meta = {"Make": make, "Model": model}
        if fecha:
            meta["DateTimeOriginal"] = fecha
        Path(str(p) + ".meta.json").write_text(json.dumps(meta))
        return p

    def correr(self, *extra):
        rep = self.raiz / "rep.csv"
        codigo = sf.main(["--origen", str(self.origen), "--destino", str(self.destino),
                          "--reporte", str(rep), *extra])
        with rep.open(encoding="utf-8") as f:
            return codigo, list(csv.DictReader(f))

    def test_filtra_por_camara_con_make_y_model(self):
        self.foto("a.jpg")
        self.foto("b.jpg", make="Canon", model="IXUS")
        _, filas = self.correr("--modelo", "DMC-LZ7")
        estados = {Path(f["archivo_origen"]).name: f["estado"] for f in filas}
        self.assertEqual(estados, {"a.jpg": "copiado", "b.jpg": "omitido_camara"})
        self.assertTrue((self.destino / "2007" / "a.jpg").exists())

    def test_rango_de_fechas(self):
        self.foto("viejo.jpg", fecha="2006:01:01 00:00:00")
        self.foto("nuevo.jpg", fecha="2009:06:01 00:00:00")
        _, filas = self.correr("--desde", "2007-01-01", "--hasta", "2008-12-31")
        self.assertEqual({f["estado"] for f in filas}, {"omitido_fecha"})

    def test_nombres_repetidos_no_se_sobrescriben(self):
        self.foto("c1/IMG_1.jpg", contenido=b"uno")
        self.foto("c2/IMG_1.jpg", contenido=b"dos")
        self.correr()
        copias = sorted((self.destino / "2007").glob("IMG_1*.jpg"))
        self.assertEqual(len(copias), 2)
        self.assertEqual({c.read_bytes() for c in copias}, {b"uno", b"dos"})

    def test_dry_run_no_copia(self):
        self.foto("a.jpg")
        _, filas = self.correr("--dry-run")
        self.assertEqual(filas[0]["estado"], "simulado")
        self.assertFalse(self.destino.exists())

    def test_segunda_corrida_no_duplica(self):
        self.foto("a.jpg")
        self.correr()
        _, filas = self.correr()
        self.assertEqual(filas[0]["estado"], "omitido_existente")
        self.assertEqual(len(list((self.destino / "2007").iterdir())), 1)

    def test_sin_exif_usa_fecha_del_archivo_y_lo_dice(self):
        self.foto("sin_fecha.jpg", fecha=None)
        _, filas = self.correr()
        self.assertEqual(filas[0]["fuente_fecha"], "archivo")

    def test_archivos_de_macos_se_ignoran(self):
        self.foto("a.jpg")
        self.foto("._a.jpg")
        _, filas = self.correr()
        self.assertEqual(len(filas), 1)

    def test_error_de_lectura_devuelve_codigo_1(self):
        p = self.origen / "sin_meta.jpg"
        p.write_bytes(b"x")
        codigo, filas = self.correr()
        self.assertEqual(filas[0]["estado"], "error_lectura")
        self.assertEqual(codigo, 1)

    def test_orden_reciente_va_del_anio_mas_nuevo_al_mas_viejo(self):
        self.foto("a.jpg", fecha="2006:03:01 10:00:00")
        self.foto("b.jpg", fecha="2010:03:01 10:00:00")
        self.foto("c.jpg", fecha="2008:03:01 10:00:00")
        _, filas = self.correr("--orden", "reciente")
        anios = [f["fecha"][:4] for f in filas]
        self.assertEqual(anios, ["2010", "2008", "2006"])

    def test_sobrescribir_reemplaza_en_destino_sin_crear_sufijos(self):
        self.foto("a.jpg", contenido=b"nuevo")
        viejo = self.destino / "2007" / "a.jpg"
        viejo.parent.mkdir(parents=True)
        viejo.write_bytes(b"viejo")
        _, filas = self.correr("--sobrescribir")
        self.assertEqual(filas[0]["estado"], "sobrescrito")
        self.assertEqual(viejo.read_bytes(), b"nuevo")
        self.assertEqual(len(list((self.destino / "2007").iterdir())), 1)

    def test_sin_sobrescribir_no_toca_lo_existente(self):
        self.foto("a.jpg", contenido=b"nuevo")
        viejo = self.destino / "2007" / "a.jpg"
        viejo.parent.mkdir(parents=True)
        viejo.write_bytes(b"viejo")
        self.correr()
        self.assertEqual(viejo.read_bytes(), b"viejo")

    def test_sobrescribir_rechaza_destino_dentro_del_origen(self):
        self.foto("a.jpg")
        self.destino = self.origen / "salida"
        with self.assertRaises(SystemExit):
            self.correr("--sobrescribir")
        self.assertEqual((self.origen / "a.jpg").read_bytes(), b"x")

    def test_nombres_repetidos_con_sobrescribir_siguen_sin_pisarse(self):
        self.foto("c1/IMG_1.jpg", contenido=b"uno")
        self.foto("c2/IMG_1.jpg", contenido=b"dos")
        self.correr("--sobrescribir")
        copias = sorted((self.destino / "2007").glob("IMG_1*.jpg"))
        self.assertEqual({c.read_bytes() for c in copias}, {b"uno", b"dos"})


if __name__ == "__main__":
    unittest.main()
