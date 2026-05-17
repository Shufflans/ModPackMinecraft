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
import re   

GITHUB_USER = "Shufflans"
GITHUB_REPO = "ModPackMinecraft"
GITHUB_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

MC_DIR_DEFAULT = os.path.join(os.getenv('APPDATA'), '.minecraft')
MC_DIR = MC_DIR_DEFAULT

VERSION_ACTUAL = "v1.0.2"   
REPO_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"


FORGE_VERSION_DIR = "1.20.1-forge-47.4.20"         
FORGE_INSTALLER_URL = f"{RAW_BASE}/tools/forge-1.20.1-47.4.20-installer.jar"


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
                return tuple(int(x) for x in v.lstrip('v').split('.'))
            if version_a_tupla(tag_remoto) > version_a_tupla(VERSION_ACTUAL):
                return url_descarga
            return None
    except Exception:
        return None

def actualizar_exe(url_descarga):
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
    inicio = os.getenv('APPDATA')
    carpeta = filedialog.askdirectory(
        title="Selecciona la carpeta .minecraft",
        initialdir=inicio
    )
    if carpeta:
        dir_var.set(carpeta)
        actualizar_destinos(carpeta)
        verificar_forge()  

def actualizar_destinos(carpeta_base):
    global MC_DIR, ELEMENTOS
    MC_DIR = carpeta_base
    ELEMENTOS[0]["destino"] = os.path.join(MC_DIR, "config", "mine_and_slash-client.toml")
    ELEMENTOS[1]["destino"] = os.path.join(MC_DIR, "config", "defaultoptions")
    ELEMENTOS[2]["destino"] = os.path.join(MC_DIR, "mods")

def java_version_ok():
    """Verifica que Java 17 o superior esté disponible."""
    try:
        result = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, check=False
        )
        output = result.stdout + result.stderr
        match = re.search(r'version\s+"?(\d+)', output)
        if match:
            return int(match.group(1)) >= 17
    except FileNotFoundError:
        pass
    return False

def forge_instalado():
    """Devuelve True si la carpeta de la versión de Forge existe."""
    version_dir = os.path.join(MC_DIR, "versions", FORGE_VERSION_DIR)
    return os.path.isdir(version_dir)

def verificar_forge():
    """Actualiza el botón y la etiqueta según si Forge está presente."""
    if forge_instalado():
        btn_forge.pack_forget()
        lbl_forge_estado.config(text="✅ Forge ya está instalado", fg="green")
    else:
        lbl_forge_estado.config(text="Forge no detectado", fg="red")
        btn_forge.pack(pady=2)

def instalar_forge():
    """Descarga y ejecuta el instalador de Forge."""
    if not java_version_ok():
        if messagebox.askyesno(
            "Java 17 requerido",
            "Se necesita Java 17 o superior.\n¿Abrir página de descarga?"
        ):
            import webbrowser
            webbrowser.open("https://adoptium.net/download/")
        return

    ruta_temp = os.path.join(os.environ['TEMP'], "forge-installer.jar")
    lbl_estado.config(text="Descargando instalador de Forge...")
    ventana.update()
    try:
        urllib.request.urlretrieve(FORGE_INSTALLER_URL, ruta_temp)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo descargar el instalador de Forge:\n{e}")
        return

    lbl_estado.config(text="Instalando Forge (puede tardar un momento)...")
    ventana.update()
    try:
        subprocess.run(
            ["java", "-jar", ruta_temp, "--installClient", "--installDir", MC_DIR],
            check=True
        )
        messagebox.showinfo("Éxito", "Forge se ha instalado correctamente.")
        verificar_forge()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Falló la instalación de Forge:\n{e}")
    finally:
        lbl_estado.config(text="")
        if os.path.exists(ruta_temp):
            os.remove(ruta_temp)

ventana = tk.Tk()
ventana.title("Sincronizador de Modpack")
ventana.geometry("600x320")  
ventana.resizable(False, False)

tk.Label(ventana, text="Sincronizador de mods y configuración",
         font=("Arial", 12, "bold")).pack(pady=10)

frame_dir = tk.Frame(ventana)
frame_dir.pack(pady=5, padx=10, fill='x')
tk.Label(frame_dir, text="Carpeta Minecraft:").pack(anchor='w')

combo_frame = tk.Frame(frame_dir)
combo_frame.pack(fill='x', pady=2)

dir_var = tk.StringVar(value=MC_DIR)
combo = ttk.Combobox(combo_frame, textvariable=dir_var, width=50)
combo.pack(side=tk.LEFT, expand=True, fill='x')
combo['values'] = [MC_DIR_DEFAULT]

btn_examinar = tk.Button(combo_frame, text="Examinar", command=seleccionar_carpeta, width=10)
btn_examinar.pack(side=tk.LEFT, padx=5)

def on_dir_change(event):
    actualizar_destinos(dir_var.get())
    verificar_forge()
combo.bind('<<ComboboxSelected>>', on_dir_change)

btn_sinc = tk.Button(ventana, text="Sincronizar ahora",
                     command=lambda: threading.Thread(target=instalar).start(),
                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=20)
btn_sinc.pack(pady=10)

barra = ttk.Progressbar(ventana, mode='determinate', length=400)
barra.pack(pady=5)

lbl_estado = tk.Label(ventana, text="", fg="blue")
lbl_estado.pack()

frame_forge = tk.Frame(ventana)
frame_forge.pack(pady=5)

lbl_forge_estado = tk.Label(frame_forge, text="", font=("Arial", 9))
lbl_forge_estado.pack()

btn_forge = tk.Button(frame_forge, text="Instalar Forge",
                      command=lambda: threading.Thread(target=instalar_forge).start(),
                      bg="#2196F3", fg="white", font=("Arial", 9, "bold"), width=15)
verificar_forge()

if getattr(sys, 'frozen', False):
    url_update = buscar_actualizacion()
    if url_update:
        ventana.after(500, lambda: actualizar_exe(url_update))

ventana.mainloop()