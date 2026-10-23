#!/usr/bin/env python3
"""Interfaz gráfica para separar_fotos.py.

Permite elegir carpeta de origen, destino, filtro por modelo y fechas y además
hacer un inventario de cámaras antes de organizar.
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
        self.geometry("820x700")
        self.minsize(760, 620)
        self._aplicar_estilo()
        self._crear_widgets()

    def _aplicar_estilo(self):
        self.configure(bg="#eef2f5")

        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        # Paleta inspirada en cámaras Ricoh: grises fríos, azules sobrios y acentos discretos.
        bg = "#eef2f5"
        panel = "#f9fafb"
        panel_alt = "#edf3f7"
        borde = "#ccd7df"
        texto = "#1f2a37"
        texto_suave = "#56657a"
        primario = "#3e5568"
        primario_oscuro = "#2d3d4d"
        primario_claro = "#dfeaf3"
        secundario = "#dfe7ee"
        seleccionado = "#6c8aa2"
        blanco = "#ffffff"

        estilo.configure("TFrame", background=bg)
        estilo.configure("Card.TFrame", background=panel)
        estilo.configure("TLabel", background=bg, foreground=texto)
        estilo.configure("Header.TLabel", background=bg, foreground=primario_oscuro, font=("Segoe UI", 18, "bold"))
        estilo.configure("Section.TLabel", background=bg, foreground=texto, font=("Segoe UI", 10, "bold"))
        estilo.configure("Muted.TLabel", background=bg, foreground=texto_suave, font=("Segoe UI", 9))

        estilo.configure(
            "TButton",
            padding=(14, 8),
            font=("Segoe UI", 10, "bold"),
            background=secundario,
            foreground=texto,
            relief="flat",
            borderwidth=0,
        )
        estilo.map(
            "TButton",
            background=[("active", primario_claro), ("pressed", primario_claro)],
            foreground=[("active", primario_oscuro), ("pressed", primario_oscuro)],
        )

        estilo.configure(
            "Primary.TButton",
            padding=(16, 9),
            font=("Segoe UI", 10, "bold"),
            background=primario,
            foreground=blanco,
            relief="flat",
            borderwidth=0,
        )
        estilo.map(
            "Primary.TButton",
            background=[("active", primario_oscuro), ("pressed", primario_oscuro)],
            foreground=[("active", blanco), ("pressed", blanco)],
        )

        estilo.configure("TEntry", fieldbackground=blanco, foreground=texto, background=blanco, borderwidth=1)
        estilo.map("TEntry", bordercolor=[("focus", seleccionado)])
        estilo.configure("TCombobox", fieldbackground=blanco, foreground=texto, background=blanco)
        estilo.map("TCombobox", bordercolor=[("focus", seleccionado)])
        estilo.configure("TCheckbutton", background=bg, foreground=texto)
        estilo.configure("TScrollbar", background=secundario, troughcolor=bg, borderwidth=0)
        estilo.configure("TText", background=blanco, foreground=texto)

        for widget in [self]:
            widget.option_add("*Font", ("Segoe UI", 10))
            widget.option_add("*Foreground", texto)
            widget.option_add("*Background", bg)
            widget.option_add("*Button.padding", "8 6")

    def _crear_widgets(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        header = ttk.Frame(frame, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 12), padx=2)

        ttk.Label(header, text="Separar fotos", style="Header.TLabel").pack(anchor="w", padx=12, pady=(12, 8))
        ttk.Label(
            header,
            text="Organiza tu colección por cámara, fecha y estructura de carpetas.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=12, pady=(0, 12))

        card = ttk.Frame(frame, padding=14, style="Card.TFrame")
        card.pack(fill="both", expand=True)

        row = 0
        ttk.Label(card, text="Carpeta origen", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, 4)
        )
        row += 1
        self.origen_var = tk.StringVar()
        self.origen_entry = ttk.Entry(card, textvariable=self.origen_var, width=80)
        self.origen_entry.grid(row=row, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(card, text="Explorar", command=self._elegir_origen).grid(row=row, column=1, sticky="ew")
        ttk.Button(card, text="Inventariar cámaras", command=self._inventariar_camaras).grid(
            row=row, column=2, sticky="ew", padx=(8, 0)
        )

        row += 1
        ttk.Label(card, text="Carpeta destino", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(12, 4)
        )
        row += 1
        self.destino_var = tk.StringVar()
        self.destino_entry = ttk.Entry(card, textvariable=self.destino_var, width=80)
        self.destino_entry.grid(row=row, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(card, text="Explorar", command=self._elegir_destino).grid(row=row, column=1, sticky="ew")

        row += 1
        ttk.Label(card, text="Cámaras detectadas (selección múltiple)", style="Section.TLabel").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(14, 4)
        )
        row += 1
        self.camaras_listbox = tk.Listbox(card, selectmode="extended", height=8, exportselection=False)
        self.camaras_listbox.grid(row=row, column=0, columnspan=3, sticky="nsew")
        self.camaras_listbox.configure(
            bg="#ffffff",
            fg="#111827",
            selectbackground="#5e788d",
            selectforeground="#ffffff",
            highlightbackground="#cbd5e1",
            highlightcolor="#5e788d",
            relief="solid",
            borderwidth=1,
            activestyle="none",
        )
        scroll = ttk.Scrollbar(card, orient="vertical", command=self.camaras_listbox.yview)
        scroll.grid(row=row, column=3, sticky="ns")
        self.camaras_listbox.configure(yscrollcommand=scroll.set)

        row += 1
        filtros = ttk.Frame(card, padding=(0, 10, 0, 0))
        filtros.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        filtros.columnconfigure(0, weight=1)
        filtros.columnconfigure(1, weight=1)
        filtros.columnconfigure(2, weight=1)
        filtros.columnconfigure(3, weight=1)

        ttk.Label(filtros, text="Modelo manual (opcional)").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        self.modelo_var = tk.StringVar()
        ttk.Entry(filtros, textvariable=self.modelo_var, width=24).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(filtros, text="Desde").grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))
        self.desde_var = tk.StringVar()
        ttk.Entry(filtros, textvariable=self.desde_var, width=14).grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(filtros, text="Hasta").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(0, 6))
        self.hasta_var = tk.StringVar()
        ttk.Entry(filtros, textvariable=self.hasta_var, width=14).grid(row=1, column=2, sticky="ew", padx=(0, 10))

        ttk.Label(filtros, text="Estructura").grid(row=0, column=3, sticky="w", pady=(0, 6))
        self.estructura_var = tk.StringVar(value="anio")
        ttk.Combobox(
            filtros,
            textvariable=self.estructura_var,
            values=["anio", "anio-mes", "anio-semana", "plano"],
            state="readonly",
            width=18,
        ).grid(row=1, column=3, sticky="ew")

        row += 1
        ttk.Label(card, text="Formato del reporte", style="Section.TLabel").grid(
            row=row, column=0, sticky="w", pady=(16, 4)
        )
        row += 1
        self.formato_var = tk.StringVar(value="csv")
        ttk.Combobox(
            card,
            textvariable=self.formato_var,
            values=["csv", "json"],
            state="readonly",
            width=12,
        ).grid(row=row, column=0, sticky="w")

        ttk.Label(card, text="Ruta del reporte (opcional)", style="Section.TLabel").grid(
            row=row - 1, column=1, sticky="w", pady=(16, 4)
        )
        self.reporte_var = tk.StringVar()
        self.reporte_entry = ttk.Entry(card, textvariable=self.reporte_var, width=38)
        self.reporte_entry.grid(row=row, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(card, text="Guardar", command=self._elegir_reporte).grid(row=row, column=2, sticky="ew")

        self.dry_run_var = tk.BooleanVar(value=False)
        self.sobrescribir_var = tk.BooleanVar(value=False)
        self.aviso_var = tk.BooleanVar(value=False)

        checks = ttk.Frame(card)
        checks.grid(row=row + 1, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Checkbutton(checks, text="Modo prueba (dry-run)", variable=self.dry_run_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(checks, text="Sobrescribir archivos existentes", variable=self.sobrescribir_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(checks, text="Avisar al terminar", variable=self.aviso_var).pack(side="left")

        self.boton = ttk.Button(card, text="Organizar fotos", style="Primary.TButton", command=self._ejecutar)
        self.boton.grid(row=row + 2, column=0, columnspan=3, sticky="ew", pady=(18, 10))

        self.output = tk.Text(card, height=16, wrap="word")
        self.output.configure(
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=8,
        )
        self.output.grid(row=row + 3, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(row + 3, weight=1)

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

    def _inventariar_camaras(self):
        origen = Path(self.origen_var.get()).expanduser().resolve()
        if not origen.exists() or not origen.is_dir():
            messagebox.showerror("Error", "La carpeta de origen no existe o no es válida.")
            return

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "Buscando cámaras en el disco...\n")
        self.boton.config(state="disabled")
        cmd = [sys.executable, str(SCRIPT), "--origen", str(origen), "--inventario-camaras"]
        hilo = threading.Thread(target=self._ejecutar_inventario, args=(cmd,), daemon=True)
        hilo.start()

    def _ejecutar_inventario(self, cmd):
        try:
            resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            salida = (resultado.stdout or "").strip()
            self.camaras_listbox.delete(0, tk.END)
            if not salida:
                self.output.delete("1.0", tk.END)
                self.output.insert(tk.END, "No se detectaron cámaras con fotos válidas en esa carpeta.\n")
                return
            lineas = [l for l in salida.splitlines() if l.strip()]
            for linea in lineas:
                partes = [p.strip() for p in linea.split("\t") if p.strip()]
                if len(partes) >= 2:
                    camara, cantidad = partes[0], partes[1]
                    self.camaras_listbox.insert(tk.END, f"{camara} ({cantidad})")
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, f"Se detectaron {len(lineas)} cámaras.\nSelecciona una o varias y pulsa 'Organizar fotos'.\n")
        except Exception as exc:  # pragma: no cover - UI only
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, f"Error al inventariar cámaras: {exc}\n")
        finally:
            self.boton.config(state="normal")

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

        camaras = []
        for idx in self.camaras_listbox.curselection():
            item = self.camaras_listbox.get(idx)
            if " (" in item:
                camaras.append(item.rsplit(" (", 1)[0])
        for camara in camaras:
            cmd.extend(["--modelo", camara])

        modelo_manual = self.modelo_var.get().strip()
        if modelo_manual:
            for parte in [p.strip() for p in modelo_manual.split(",") if p.strip()]:
                cmd.extend(["--modelo", parte])

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
