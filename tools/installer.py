import tkinter as tk
from tkinter import messagebox
import os
import sys
import shutil
import subprocess
import re
import webbrowser

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def java_version_ok():
    """Verifica si la versión de Java es 17 o superior."""
    try:
        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        output = result.stdout + result.stderr
        match = re.search(r'version\s+"?(\d+)', output)
        if match:
            return int(match.group(1)) >= 17
        return False
    except FileNotFoundError:
        return False

def instalar_config():
    appdata = os.getenv('APPDATA')
    if not appdata:
        messagebox.showerror("Error", "No se encontró la carpeta APPDATA.")
        return
    destino_config = os.path.join(appdata, '.minecraft', 'config')

    src_toml = resource_path("mine_and_slash-client.toml")
    src_default = resource_path("defaultoptions")

    if not os.path.exists(src_toml) or not os.path.exists(src_default):
        messagebox.showerror("Error", "Faltan archivos de configuración en el instalador.")
        return

    if not messagebox.askyesno("Confirmar", "¿Instalar configuración y mods?\nSe sobrescribirá todo lo anterior."):
        return

    try:
        for nombre in ['mod', 'defaultoptions', 'mine_and_slash-client.toml']:
            ruta = os.path.join(destino_config, nombre)
            if os.path.exists(ruta):
                if os.path.isdir(ruta):
                    shutil.rmtree(ruta)
                else:
                    os.remove(ruta)

        shutil.copy2(src_toml, destino_config)
        shutil.copytree(src_default, os.path.join(destino_config, 'defaultoptions'))
        os.makedirs(os.path.join(destino_config, 'defaultoptions', 'extra'), exist_ok=True)

        messagebox.showinfo("Éxito", "Configuración y mods instalados correctamente.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo instalar la configuración:\n{e}")

def instalar_forge():
    if not java_version_ok():
        if messagebox.askyesno(
            "Java 17 requerido",
            "Se necesita Java 17 o superior para instalar Forge.\n\n"
            "¿Quieres ir a la página de descarga?\n"
            "(Recomendado: Adoptium)"
        ):
            webbrowser.open("https://adoptium.net/download/")
        return

    forge_jar = resource_path("forge-1.20.1-47.4.20-installer.jar")
    if not os.path.exists(forge_jar):
        messagebox.showerror("Error", "No se encontró el instalador de Forge.")
        return

    if not messagebox.askyesno("Instalar Forge", "¿Ejecutar el instalador de Forge 1.20.1?\n(Requiere Java 17)"):
        return

    try:
        subprocess.run(
            ["java", "-jar", forge_jar, "--installClient"],
            check=True
        )
        messagebox.showinfo("Éxito", "Forge se ha instalado correctamente.")
    except subprocess.CalledProcessError:
        messagebox.showerror(
            "Error",
            "Falló la instalación de Forge.\n"
            "Verifica que tienes Java 17 o superior y que tienes permisos de escritura."
        )

# ---------- Interfaz ----------
ventana = tk.Tk()
ventana.title("Instalador Modpack")
ventana.geometry("450x200")
ventana.resizable(False, False)

tk.Label(ventana, text="Instalador de configuración y Forge",
         font=("Arial", 12, "bold")).pack(pady=10)

btn_mods = tk.Button(
    ventana,
    text="Instalar Mods y Configuración",
    command=instalar_config,
    bg="#4CAF50", fg="white",
    font=("Arial", 11, "bold"),
    width=25
)
btn_mods.pack(pady=8)

btn_forge = tk.Button(
    ventana,
    text="Instalar Forge (si aún no lo tienes)",
    command=instalar_forge,
    bg="#2196F3", fg="white",
    font=("Arial", 10),
    width=25
)
btn_forge.pack(pady=5)

tk.Label(ventana, text="Puedes instalar la configuración aunque no uses Forge.",
         font=("Arial", 8), fg="gray").pack(pady=5)

ventana.mainloop()