import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import requests
import shutil
import threading
import hashlib
import time
import urllib.request
import subprocess
import re
import json
import sys

# ---------------- CONFIG ----------------
GITHUB_USER = "Shufflans"
GITHUB_REPO = "ModPackMinecraft"
GITHUB_BRANCH = "main"

RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

MC_DIR_DEFAULT = os.path.join(os.getenv('APPDATA'), '.minecraft')
MC_DIR = MC_DIR_DEFAULT

VERSION_ACTUAL = "v1.0.2"

REPO_API_URL = (
    f"https://api.github.com/repos/"
    f"{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
)

FORGE_VERSION = "1.20.1-forge-47.4.20"

FORGE_INSTALLER_URL = (
    f"{RAW_BASE}/tools/forge-1.20.1-47.4.20-installer.jar"
)

ELEMENTOS = [
    {
        "origen": "config/mine_and_slash-client.toml",
        "destino": os.path.join(MC_DIR, "config", "mine_and_slash-client.toml"),
        "tipo": "archivo"
    },
    {
        "origen": "config/defaultoptions",
        "destino": os.path.join(MC_DIR, "config", "defaultoptions"),
        "tipo": "carpeta"
    },
    {
        "origen": "mods",
        "destino": os.path.join(MC_DIR, "mods"),
        "tipo": "mods"
    }
]

# ---------------- UTILIDADES ----------------

def git_blob_sha1(filepath):
    with open(filepath, 'rb') as f:
        contenido = f.read()

    encabezado = f"blob {len(contenido)}\0".encode('utf-8')

    sha = hashlib.sha1()
    sha.update(encabezado)
    sha.update(contenido)

    return sha.hexdigest()

def descargar_archivo(url, destino):
    for intento in range(3):
        try:
            resp = requests.get(url, stream=True, timeout=15)
            resp.raise_for_status()

            os.makedirs(os.path.dirname(destino), exist_ok=True)

            with open(destino, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True

        except requests.exceptions.RequestException as e:
            if intento == 2:
                raise e

            time.sleep(1)

def obtener_arbol_github(carpeta):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"

    resp = requests.get(url)
    resp.raise_for_status()

    data = resp.json()

    archivos = {}

    prefijo = carpeta + "/"

    extensiones_validas = [
        '.jar',
        '.disabled',
        '.litemod',
        '.zip',
        '.jar.jar'
    ]

    for item in data['tree']:
        if item['type'] == 'blob' and item['path'].startswith(prefijo):

            rel_path = item['path'][len(prefijo):]

            if carpeta == "mods":
                if any(rel_path.endswith(ext) for ext in extensiones_validas):
                    archivos[rel_path] = item['sha']
            else:
                archivos[rel_path] = item['sha']

    return archivos

# ---------------- SINCRONIZACIÓN ----------------

def sincronizar_carpeta(origen, destino_local):

    archivos_remotos = obtener_arbol_github(origen)

    os.makedirs(destino_local, exist_ok=True)

    descargas = []

    for rel_path, remote_sha in archivos_remotos.items():

        local_path = os.path.join(destino_local, rel_path)

        if not os.path.exists(local_path):
            descargas.append(rel_path)

        else:
            if git_blob_sha1(local_path) != remote_sha:
                descargas.append(rel_path)

    total = len(descargas)

    for i, rel_path in enumerate(descargas, 1):

        url = f"{RAW_BASE}/{origen}/{rel_path}"

        dest = os.path.join(destino_local, rel_path)

        descargar_archivo(url, dest)

        barra['value'] = (i / total) * 100 if total > 0 else 100

        lbl_estado.config(
            text=f"Descargando {rel_path} ({i}/{total})"
        )

        ventana.update_idletasks()

def instalar():

    btn_sinc['state'] = 'disabled'

    barra['value'] = 0

    lbl_estado.config(text="Sincronizando...")

    ventana.update()

    try:

        for elem in ELEMENTOS:

            if elem['tipo'] == 'archivo':

                url = f"{RAW_BASE}/{elem['origen']}"

                descargar_archivo(url, elem['destino'])

            else:

                sincronizar_carpeta(
                    elem['origen'],
                    elem['destino']
                )

        barra['value'] = 100

        lbl_estado.config(text="Instalación completada")

        messagebox.showinfo(
            "Éxito",
            "Mods sincronizados correctamente."
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

        lbl_estado.config(text="Error")

    finally:

        btn_sinc['state'] = 'normal'

# ---------------- FORGE ----------------

def forge_instalado():

    version_dir = os.path.join(
        MC_DIR,
        "versions",
        FORGE_VERSION
    )

    return os.path.isdir(version_dir)

def java_instalado():

    try:

        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout + result.stderr

        match = re.search(r'"(\d+)', output)

        if match:
            return int(match.group(1)) >= 17

    except:
        pass

    return False

def verificar_forge():

    if forge_instalado():

        lbl_forge.config(
            text="✅ Forge ya instalado",
            fg="green"
        )

        btn_forge.pack_forget()

    else:

        lbl_forge.config(
            text="❌ Forge no instalado",
            fg="red"
        )

        btn_forge.pack(pady=5)

def instalar_forge():

    if not java_instalado():

        messagebox.showerror(
            "Java requerido",
            "Necesitas Java 17 o superior."
        )

        return

    try:

        ruta_temp = os.path.join(
            os.environ['TEMP'],
            "forge-installer.jar"
        )

        # ---------------- DESCARGA ----------------

        barra['value'] = 0

        lbl_estado.config(
            text="Descargando Forge..."
        )

        ventana.update()

        urllib.request.urlretrieve(
            FORGE_INSTALLER_URL,
            ruta_temp
        )

        barra['value'] = 20

        # ---------------- INSTALACIÓN ----------------

        lbl_estado.config(
            text="Instalando Forge... puede tardar 1-2 minutos"
        )

        ventana.update()

        # Animación falsa de progreso
        for i in range(25, 90, 5):

            barra['value'] = i

            ventana.update_idletasks()

            time.sleep(0.2)

        # Ocultar CMD negro
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        resultado = subprocess.run(
            [
                "java",
                "-jar",
                ruta_temp,
                "--installClient"
            ],
            capture_output=True,
            text=True,
            cwd=MC_DIR,
            startupinfo=startupinfo
        )

        # ---------------- ERROR ----------------

        if resultado.returncode != 0:

            barra['value'] = 0

            error_completo = (
                f"STDOUT:\n{resultado.stdout}\n\n"
                f"STDERR:\n{resultado.stderr}"
            )

            print(error_completo)

            messagebox.showerror(
                "Error Forge",
                error_completo[:1500]
            )

            lbl_estado.config(
                text="Error instalando Forge"
            )

            return

        # ---------------- ÉXITO ----------------

        barra['value'] = 100

        lbl_estado.config(
            text="Forge instalado correctamente"
        )

        messagebox.showinfo(
            "Éxito",
            "Forge instalado correctamente."
        )

        verificar_forge()

        # Borrar installer temporal
        if os.path.exists(ruta_temp):

            os.remove(ruta_temp)

    except Exception as e:

        barra['value'] = 0

        lbl_estado.config(
            text="Error instalando Forge"
        )

        messagebox.showerror(
            "Error",
            str(e)
        )
        
def buscar_actualizacion():

    try:

        with urllib.request.urlopen(REPO_API_URL) as resp:

            data = json.loads(resp.read().decode())

            tag_remoto = data['tag_name']

            url_descarga = None

            for asset in data['assets']:

                if asset['name'].endswith('.exe'):

                    url_descarga = asset['browser_download_url']

                    break

            if not url_descarga:
                return None

            def version_a_tupla(v):

                return tuple(
                    int(x)
                    for x in v.lstrip('v').split('.')
                )

            if version_a_tupla(tag_remoto) > version_a_tupla(VERSION_ACTUAL):

                return url_descarga

            return None

    except:
        return None

def actualizar_exe(url_descarga):

    if not messagebox.askyesno(
        "Actualización disponible",
        "Hay una nueva versión del launcher.\n¿Actualizar ahora?"
    ):
        return

    ruta_actual = sys.executable

    ruta_nuevo = ruta_actual.replace(
        ".exe",
        "_new.exe"
    )

    ruta_bat = ruta_actual.replace(
        ".exe",
        "_updater.bat"
    )

    try:

        lbl_estado.config(
            text="Descargando actualización..."
        )

        ventana.update()

        urllib.request.urlretrieve(
            url_descarga,
            ruta_nuevo
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            f"No se pudo descargar:\n{e}"
        )

        return

    bat = f'''@echo off

timeout /t 5 /nobreak >nul

taskkill /f /im "{os.path.basename(ruta_actual)}" >nul 2>&1

timeout /t 3 /nobreak >nul

del /f /q "{ruta_actual}"

timeout /t 2 /nobreak >nul

move /y "{ruta_nuevo}" "{ruta_actual}"

timeout /t 5 /nobreak >nul

start "" "{ruta_actual}"

del "%~f0"
'''


    try:

        with open(ruta_bat, 'w', encoding='utf-8') as f:

            f.write(bat)

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

        return

    subprocess.Popen(
        ['cmd', '/c', ruta_bat],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    ventana.destroy()

    os._exit(0)

# ---------------- CARPETA ----------------

def seleccionar_carpeta():

    carpeta = filedialog.askdirectory(
        initialdir=os.getenv('APPDATA')
    )

    if carpeta:

        dir_var.set(carpeta)

        actualizar_destinos(carpeta)

        verificar_forge()

def actualizar_destinos(carpeta_base):

    global MC_DIR

    MC_DIR = carpeta_base

    ELEMENTOS[0]["destino"] = os.path.join(
        MC_DIR,
        "config",
        "mine_and_slash-client.toml"
    )

    ELEMENTOS[1]["destino"] = os.path.join(
        MC_DIR,
        "config",
        "defaultoptions"
    )

    ELEMENTOS[2]["destino"] = os.path.join(
        MC_DIR,
        "mods"
    )

# ---------------- UI ----------------

ventana = tk.Tk()

ventana.title("Launcher Modpack")

ventana.geometry("600x320")

ventana.resizable(False, False)

tk.Label(
    ventana,
    text="Launcher Modpack",
    font=("Arial", 14, "bold")
).pack(pady=10)

frame_dir = tk.Frame(ventana)

frame_dir.pack(fill='x', padx=10)

tk.Label(
    frame_dir,
    text="Carpeta Minecraft:"
).pack(anchor='w')

combo_frame = tk.Frame(frame_dir)

combo_frame.pack(fill='x')

dir_var = tk.StringVar(value=MC_DIR)

combo = ttk.Combobox(
    combo_frame,
    textvariable=dir_var,
    width=55
)

combo.pack(side=tk.LEFT, expand=True, fill='x')

combo['values'] = [MC_DIR_DEFAULT]

btn_examinar = tk.Button(
    combo_frame,
    text="Examinar",
    command=seleccionar_carpeta
)

btn_examinar.pack(side=tk.LEFT, padx=5)

btn_sinc = tk.Button(
    ventana,
    text="Sincronizar Mods",
    command=lambda: threading.Thread(target=instalar).start(),
    bg="#4CAF50",
    fg="white",
    font=("Arial", 10, "bold"),
    width=22
)

btn_sinc.pack(pady=10)

barra = ttk.Progressbar(
    ventana,
    mode='determinate',
    length=450
)

barra.pack(pady=5)

lbl_estado = tk.Label(
    ventana,
    text=""
)

lbl_estado.pack()

frame_forge = tk.Frame(ventana)

frame_forge.pack(pady=10)

lbl_forge = tk.Label(
    frame_forge,
    text="",
    font=("Arial", 10, "bold")
)

lbl_forge.pack()

btn_forge = tk.Button(
    frame_forge,
    text="Instalar Forge",
    command=lambda: threading.Thread(target=instalar_forge).start(),
    bg="#2196F3",
    fg="white",
    font=("Arial", 10, "bold"),
    width=20
)

verificar_forge()

ventana.mainloop()