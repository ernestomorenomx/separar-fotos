#!/usr/bin/env python3
"""Interfaz gráfica para separar_fotos.py.

Permite elegir carpeta de origen, destino, filtro por modelo y fechas sin
necesitar recordar todas las opciones de la línea de comandos.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "separar_fotos.py"


class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Separar fotos")
        self.geometry("760x620")
        self.minsize(700, 520)

        self._crear_widgets()

    def _crear_widgets(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Carpeta origen", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.origen_var = tk.StringVar()
        self.origen_entry = ttk.Entry(frame, textvariable=self.origen_var, width=80)
        self.origen_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Explorar", command=self._elegir_origen).grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Carpeta destino", font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, sticky="w", pady=(12, 4)
        )
        self.destino_var = tk.StringVar()
        self.destino_entry = ttk.Entry(frame, textvariable=self.destino_var, width=80)
        self.destino_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Explorar", command=self._elegir_destino).grid(row=3, column=1, sticky="ew")

        opts = ttk.Frame(frame)
        opts.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        opts.columnconfigure(0, weight=1)
        opts.columnconfigure(1, weight=1)
        opts.columnconfigure(2, weight=1)
        opts.columnconfigure(3, weight=1)

        ttk.Label(opts, text="Modelo").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        self.modelo_var = tk.StringVar()
        ttk.Entry(opts, textvariable=self.modelo_var, width=18).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(opts, text="Desde").grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))
        self.desde_var = tk.StringVar()
        ttk.Entry(opts, textvariable=self.desde_var, width=14).grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(opts, text="Hasta").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(0, 6))
        self.hasta_var = tk.StringVar()
        ttk.Entry(opts, textvariable=self.hasta_var, width=14).grid(row=1, column=2, sticky="ew", padx=(0, 10))

        ttk.Label(opts, text="Estructura").grid(row=0, column=3, sticky="w", pady=(0, 6))
        self.estructura_var = tk.StringVar(value="anio")
        ttk.Combobox(
            opts,
            textvariable=self.estructura_var,
            values=["anio", "anio-mes", "plano"],
            state="readonly",
            width=16,
        ).grid(row=1, column=3, sticky="ew")

        ttk.Label(frame, text="Formato del reporte", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, sticky="w", pady=(16, 4)
        )
        self.formato_var = tk.StringVar(value="csv")
        ttk.Combobox(
            frame,
            textvariable=self.formato_var,
            values=["csv", "json"],
            state="readonly",
            width=12,
        ).grid(row=6, column=0, sticky="w")

        ttk.Label(frame, text="Ruta del reporte (opcional)", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=1, sticky="w", pady=(16, 4)
        )
        self.reporte_var = tk.StringVar()
        self.reporte_entry = ttk.Entry(frame, textvariable=self.reporte_var, width=38)
        self.reporte_entry.grid(row=6, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Guardar", command=self._elegir_reporte).grid(row=6, column=2, sticky="ew")

        self.dry_run_var = tk.BooleanVar(value=False)
        self.sobrescribir_var = tk.BooleanVar(value=False)
        self.aviso_var = tk.BooleanVar(value=False)

        checks = ttk.Frame(frame)
        checks.grid(row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Checkbutton(checks, text="Modo prueba (dry-run)", variable=self.dry_run_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(checks, text="Sobrescribir archivos existentes", variable=self.sobrescribir_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(checks, text="Avisar al terminar", variable=self.aviso_var).pack(side="left")

        self.boton = ttk.Button(frame, text="Organizar fotos", command=self._ejecutar)
        self.boton.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(18, 10))

        self.output = tk.Text(frame, height=16, wrap="word")
        self.output.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(9, weight=1)

        self._cargar_valores_por_defecto()

    def _cargar_valores_por_defecto(self):
        self.origen_var.set(str(Path.home()))
        self.destino_var.set(str(Path.home() / "organizadas"))
        self.reporte_var.set(str(ROOT / "reporte_fotos.csv"))

    def _elegir_origen(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta de origen")
        if carpeta:
            self.origen_var.set(carpeta)

    def _elegir_destino(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta de destino")
        if carpeta:
            self.destino_var.set(carpeta)

    def _elegir_reporte(self):
        archivo = filedialog.asksaveasfilename(
            title="Ruta del reporte",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("JSON", "*.json")],
        )
        if archivo:
            self.reporte_var.set(archivo)

    def _ejecutar(self):
        origen = Path(self.origen_var.get()).expanduser().resolve()
        destino = Path(self.destino_var.get()).expanduser().resolve()

        if not origen.exists() or not origen.is_dir():
            messagebox.showerror("Error", "La carpeta de origen no existe o no es válida.")
            return

        if not destino.exists():
            try:
                destino.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("Error", f"No se pudo crear la carpeta destino: {exc}")
                return

        if origen == destino or destino in origen.parents or origen in destino.parents:
            messagebox.showerror(
                "Error",
                "El destino no puede ser igual, ni estar dentro, ni contener a la carpeta de origen.",
            )
            return

        cmd = [
            sys.executable,
            str(SCRIPT),
            "--origen",
            str(origen),
            "--destino",
            str(destino),
            "--estructura",
            self.estructura_var.get(),
            "--formato",
            self.formato_var.get(),
        ]

        modelo = self.modelo_var.get().strip()
        if modelo:
            cmd.extend(["--modelo", modelo])

        desde = self.desde_var.get().strip()
        if desde:
            cmd.extend(["--desde", desde])

        hasta = self.hasta_var.get().strip()
        if hasta:
            cmd.extend(["--hasta", hasta])

        reporte = self.reporte_var.get().strip()
        if reporte:
            cmd.extend(["--reporte", reporte])

        if self.dry_run_var.get():
            cmd.append("--dry-run")

        if self.sobrescribir_var.get():
            cmd.append("--sobrescribir")

        if self.aviso_var.get():
            cmd.append("--aviso")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "Ejecutando...\n")
        self.boton.config(state="disabled")

        hilo = threading.Thread(target=self._ejecutar_comando, args=(cmd,), daemon=True)
        hilo.start()

    def _ejecutar_comando(self, cmd):
        try:
            resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            salida = (resultado.stdout or "") + (resultado.stderr or "")
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, salida or "Proceso terminado.\n")
            if resultado.returncode != 0:
                self.output.insert(tk.END, f"\nCódigo de salida: {resultado.returncode}\n")
            else:
                self.output.insert(tk.END, "\nProceso terminado correctamente.\n")
        except Exception as exc:  # pragma: no cover - UI only
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, f"Error al ejecutar: {exc}\n")
        finally:
            self.boton.config(state="normal")


if __name__ == "__main__":
    app = VentanaPrincipal()
    app.mainloop()
