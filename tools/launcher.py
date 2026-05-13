import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import os
import sys
import requests
import shutil
import threading
import hashlib
import time
import json
import urllib.request
import subprocess

# ---------- CONFIGURACIÓN ----------
GITHUB_USER = "Shufflans"
GITHUB_REPO = "ModPackMinecraft"
GITHUB_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

# ----- NUEVO: Carpeta por defecto (se puede cambiar desde la interfaz) -----
MC_DIR_DEFAULT = os.path.join(os.getenv('APPDATA'), '.minecraft')
MC_DIR = MC_DIR_DEFAULT
# -------------------------------------------------------------------------

ELEMENTOS = [
    {
        "origen": "config/mine_and_slash-client.toml",
        "destino": os.path.join(MC_DIR, "config", "mine_and_slash-client.toml"),
        "tipo": "archivo"
    },
    {
        "origen": "config/defaultoptions",
        "destino": os.path.join(MC_DIR, "config", "defaultoptions"),
        "tipo": "carpeta_completa"
    },
    {
        "origen": "mods",
        "destino": os.path.join(MC_DIR, "mods"),
        "tipo": "sincronizar_mods"
    }
]

# ----- NUEVO: Versión para auto‑update (debe coincidir con el tag del Release) -----
VERSION_ACTUAL = "v1.0.0"
REPO_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
# -----------------------------------------------------------------------------------

# -----------------------------------
# Funciones de sincronización (SE MANTIENEN IGUAL, solo unifico obtener_arbol_github)
# -----------------------------------
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
            resp = requests.get(url, stream=True, timeout=10)
            resp.raise_for_status()
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            if intento == 2:
                raise e
            time.sleep(0.5)

def obtener_arbol_github(carpeta):
    """
    Devuelve un diccionario {ruta_relativa: sha_blob} de todos los archivos
    dentro de la carpeta especificada, usando el árbol Git recursivo.
    Para la carpeta 'mods' solo incluye extensiones válidas.
    """
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if 'tree' not in data:
        return {}

    archivos = {}
    prefijo = carpeta + "/"
    extensiones_validas = ['.jar', '.disabled', '.litemod', '.zip', '.jar.jar']

    for item in data['tree']:
        if item['type'] == 'blob' and item['path'].startswith(prefijo):
            rel_path = item['path'][len(prefijo):]
            # Si es la carpeta mods, filtrar por extensión; si es config, aceptar todo
            if carpeta == "mods":
                if any(rel_path.endswith(ext) for ext in extensiones_validas):
                    archivos[rel_path] = item['sha']
            else:
                archivos[rel_path] = item['sha']
    return archivos

def vaciar_carpeta(ruta):
    if os.path.exists(ruta):
        for elemento in os.listdir(ruta):
            elemento_path = os.path.join(ruta, elemento)
            if os.path.isfile(elemento_path):
                os.remove(elemento_path)
            elif os.path.isdir(elemento_path):
                shutil.rmtree(elemento_path)

def sincronizar_carpeta_completa(origen, destino_local):
    archivos_remotos = obtener_arbol_github(origen)
    os.makedirs(destino_local, exist_ok=True)

    for archivo_local in os.listdir(destino_local):
        if archivo_local not in archivos_remotos:
            ruta_local = os.path.join(destino_local, archivo_local)
            if os.path.isfile(ruta_local):
                os.remove(ruta_local)
            elif os.path.isdir(ruta_local):
                shutil.rmtree(ruta_local)

    descargas = []
    for rel_path, remote_sha in archivos_remotos.items():
        local_path = os.path.join(destino_local, rel_path)
        if not os.path.exists(local_path):
            descargas.append(rel_path)
        else:
            if git_blob_sha1(local_path) != remote_sha:
                descargas.append(rel_path)

    total = len(descargas)
    if total > 0:
        for i, rel_path in enumerate(descargas, 1):
            url = f"{RAW_BASE}/{origen}/{rel_path}"
            dest = os.path.join(destino_local, rel_path)
            descargar_archivo(url, dest)
            barra['value'] = (i / total) * 100
            lbl_estado.config(text=f"Descargando defaultoptions {i}/{total}")
            ventana.update_idletasks()
    else:
        lbl_estado.config(text="defaultoptions ya está actualizada")

def sincronizar_mods(origen, destino_local):
    archivos_remotos = obtener_arbol_github(origen)
    os.makedirs(destino_local, exist_ok=True)

    for archivo_local in os.listdir(destino_local):
        if archivo_local not in archivos_remotos:
            ruta_local = os.path.join(destino_local, archivo_local)
            if os.path.isfile(ruta_local):
                os.remove(ruta_local)
            elif os.path.isdir(ruta_local):
                shutil.rmtree(ruta_local)

    descargas = []
    for rel_path, remote_sha in archivos_remotos.items():
        local_path = os.path.join(destino_local, rel_path)
        if not os.path.exists(local_path):
            descargas.append(rel_path)
        else:
            if git_blob_sha1(local_path) != remote_sha:
                descargas.append(rel_path)

    total = len(descargas)
    if total > 0:
        for i, rel_path in enumerate(descargas, 1):
            url = f"{RAW_BASE}/{origen}/{rel_path}"
            dest = os.path.join(destino_local, rel_path)
            descargar_archivo(url, dest)
            barra['value'] = (i / total) * 100
            lbl_estado.config(text=f"Descargando mod {i}/{total}: {rel_path}")
            ventana.update_idletasks()
    else:
        lbl_estado.config(text="Mods ya están actualizados")

def instalar():
    btn_sinc['state'] = 'disabled'
    barra['value'] = 0
    lbl_estado.config(text="Conectando e instalando...")
    ventana.update()

    try:
        for elem in ELEMENTOS:
            lbl_estado.config(text=f"Procesando {elem['origen']}...")
            ventana.update()

            if elem['tipo'] == 'archivo':
                url = f"{RAW_BASE}/{elem['origen']}"
                descargar_archivo(url, elem['destino'])

            elif elem['tipo'] == 'carpeta_completa':
                sincronizar_carpeta_completa(elem['origen'], elem['destino'])

            elif elem['tipo'] == 'sincronizar_mods':
                sincronizar_mods(elem['origen'], elem['destino'])

        lbl_estado.config(text="Instalación completada")
        barra['value'] = 100
        messagebox.showinfo("Éxito", "Mods y configuración sincronizados correctamente.")

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error de red", f"No se pudo conectar con GitHub:\n{e}")
        lbl_estado.config(text="Error de conexión")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema:\n{e}")
        lbl_estado.config(text="Error")
    finally:
        btn_sinc['state'] = 'normal'

# ----- NUEVO: Funciones de auto‑update y selector de carpeta -----
def buscar_actualizacion():
    """Devuelve url_descarga si hay un release más nuevo que VERSION_ACTUAL."""
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

            # Comparar versiones ignorando la 'v' inicial
            def version_a_tupla(v):
                return tuple(int(x) for x in v.lstrip('v').split('.'))
            if version_a_tupla(tag_remoto) > version_a_tupla(VERSION_ACTUAL):
                return url_descarga
            return None
    except Exception:
        return None

def actualizar_exe(url_descarga):
    """Descarga el nuevo .exe, crea un .bat para reemplazarse y cierra."""
    if not messagebox.askyesno("Actualización disponible",
                               "Hay una nueva versión del launcher.\n¿Quieres actualizar ahora?"):
        return

    ruta_actual = sys.executable
    ruta_nuevo = ruta_actual + ".nuevo"
    ruta_bat = ruta_actual + ".bat"

    try:
        lbl_estado.config(text="Descargando nueva versión...")
        ventana.update()
        urllib.request.urlretrieve(url_descarga, ruta_nuevo)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo descargar la actualización:\n{e}")
        return

    try:
        with open(ruta_bat, 'w') as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak >nul
del /f /q "{ruta_actual}"
move /y "{ruta_nuevo}" "{ruta_actual}"
start "" "{ruta_actual}"
del /f /q "{ruta_bat}"
""")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo preparar el instalador:\n{e}")
        return

    subprocess.Popen(f'cmd /c "{ruta_bat}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit()

def seleccionar_carpeta():
    """Abre diálogo para elegir carpeta, empezando en %APPDATA%."""
    inicio = os.getenv('APPDATA')  # Siempre abre en Roaming
    carpeta = filedialog.askdirectory(
        title="Selecciona la carpeta .minecraft",
        initialdir=inicio
    )
    if carpeta:
        dir_var.set(carpeta)
        actualizar_destinos(carpeta)

def actualizar_destinos(carpeta_base):
    """Reconstruye ELEMENTOS con la nueva carpeta base."""
    global MC_DIR, ELEMENTOS
    MC_DIR = carpeta_base
    ELEMENTOS[0]["destino"] = os.path.join(MC_DIR, "config", "mine_and_slash-client.toml")
    ELEMENTOS[1]["destino"] = os.path.join(MC_DIR, "config", "defaultoptions")
    ELEMENTOS[2]["destino"] = os.path.join(MC_DIR, "mods")
# ----------------------------------------------------------------

# ---------- Interfaz ----------
ventana = tk.Tk()
ventana.title("Sincronizador de Modpack")
ventana.geometry("600x250")
ventana.resizable(False, False)

tk.Label(ventana, text="Sincronizador de mods y configuración",
         font=("Arial", 12, "bold")).pack(pady=10)

# --- Nuevo: Selector de carpeta ---
frame_dir = tk.Frame(ventana)
frame_dir.pack(pady=5, padx=10, fill='x')

tk.Label(frame_dir, text="Carpeta Minecraft:").pack(anchor='w')

combo_frame = tk.Frame(frame_dir)
combo_frame.pack(fill='x', pady=2)

dir_var = tk.StringVar(value=MC_DIR)
combo = ttk.Combobox(combo_frame, textvariable=dir_var, width=50)
combo.pack(side=tk.LEFT, expand=True, fill='x')
# Inicialmente solo mostramos la ruta por defecto
combo['values'] = [MC_DIR_DEFAULT]

btn_examinar = tk.Button(combo_frame, text="Examinar", command=seleccionar_carpeta, width=10)
btn_examinar.pack(side=tk.LEFT, padx=5)

# Al cambiar el texto del Combobox (por ejemplo, después de usar Examinar),
# actualizamos las rutas de destino
def on_dir_change(event):
    actualizar_destinos(dir_var.get())
combo.bind('<<ComboboxSelected>>', on_dir_change)
# También podemos forzar la actualización si el usuario escribe manualmente (opcional)
# combo.bind('<Return>', on_dir_change)
# ------------------------------------

btn_sinc = tk.Button(ventana, text="Sincronizar ahora",
                     command=lambda: threading.Thread(target=instalar).start(),
                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=20)
btn_sinc.pack(pady=10)

barra = ttk.Progressbar(ventana, mode='determinate', length=400)
barra.pack(pady=5)

lbl_estado = tk.Label(ventana, text="", fg="blue")
lbl_estado.pack()

# ----- Verificar actualización SOLO si estamos en un .exe compilado -----
if getattr(sys, 'frozen', False):
    url_update = buscar_actualizacion()
    if url_update:
        ventana.after(500, lambda: actualizar_exe(url_update))

ventana.mainloop()