import tkinter as tk
from tkinter import messagebox, ttk
import os
import requests
import shutil
import threading
import hashlib
import time

# ---------- CONFIGURACIÓN ----------
GITHUB_USER = "Shufflans"
GITHUB_REPO = "ModPackMinecraft"
GITHUB_BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
MC_DIR = os.path.join(os.getenv('APPDATA'), '.minecraft')

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
# -----------------------------------

def git_blob_sha1(filepath):
    """Calcula el hash SHA1 del archivo local como un blob de Git."""
    with open(filepath, 'rb') as f:
        contenido = f.read()
    # Encabezado que Git agrega internamente a los blobs
    encabezado = f"blob {len(contenido)}\0".encode('utf-8')
    sha = hashlib.sha1()
    sha.update(encabezado)
    sha.update(contenido)
    return sha.hexdigest()

def descargar_archivo(url, destino):
    """Descarga un archivo con timeout y reintentos"""
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
    """
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if 'tree' not in data:
        return {}

    archivos = {}
    prefijo = carpeta + "/"
    for item in data['tree']:
        if item['type'] == 'blob' and item['path'].startswith(prefijo):
            rel_path = item['path'][len(prefijo):]  # ruta dentro de la carpeta
            archivos[rel_path] = item['sha']
    return archivos

def obtener_arbol_github(carpeta):
    """
    Devuelve un diccionario {ruta_relativa: sha_blob} de todos los archivos
    dentro de la carpeta especificada, usando el árbol Git recursivo.
    Solo incluye archivos con extensiones válidas para mods.
    """
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if 'tree' not in data:
        return {}

    archivos = {}
    prefijo = carpeta + "/"
    extensiones_validas = ['.jar', '.disabled', '.litemod', '.zip', '.jar.jar']  # añade más si necesitas
    for item in data['tree']:
        if item['type'] == 'blob' and item['path'].startswith(prefijo):
            rel_path = item['path'][len(prefijo):]  # ruta dentro de la carpeta
            # Filtro: solo si termina en una extensión válida
            if any(rel_path.endswith(ext) for ext in extensiones_validas):
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
    """
    Sincroniza defaultoptions: descarga solo archivos nuevos o modificados
    y elimina los que sobran.
    """
    archivos_remotos = obtener_arbol_github(origen)
    os.makedirs(destino_local, exist_ok=True)

    # 1. Eliminar archivos locales que ya no están en el remoto
    for archivo_local in os.listdir(destino_local):
        if archivo_local not in archivos_remotos:
            ruta_local = os.path.join(destino_local, archivo_local)
            if os.path.isfile(ruta_local):
                os.remove(ruta_local)
            elif os.path.isdir(ruta_local):
                shutil.rmtree(ruta_local)

    # 2. Descargar archivos nuevos o con hash diferente
    descargas = []
    for rel_path, remote_sha in archivos_remotos.items():
        local_path = os.path.join(destino_local, rel_path)
        if not os.path.exists(local_path):
            descargas.append(rel_path)
        else:
            local_sha = git_blob_sha1(local_path)  # 👈 ¡Cambio clave!
            if local_sha != remote_sha:
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
    """
    Sincroniza mods: descarga solo los mods nuevos o modificados
    y elimina los que ya no aparecen en el repositorio.
    """
    archivos_remotos = obtener_arbol_github(origen)
    os.makedirs(destino_local, exist_ok=True)

    # 1. Eliminar archivos locales que ya no están en el remoto
    for archivo_local in os.listdir(destino_local):
        if archivo_local not in archivos_remotos:
            ruta_local = os.path.join(destino_local, archivo_local)
            if os.path.isfile(ruta_local):
                os.remove(ruta_local)
            elif os.path.isdir(ruta_local):
                shutil.rmtree(ruta_local)

    # 2. Descargar archivos nuevos o con hash diferente
    descargas = []
    for rel_path, remote_sha in archivos_remotos.items():
        local_path = os.path.join(destino_local, rel_path)
        if not os.path.exists(local_path):
            descargas.append(rel_path)
        else:
            local_sha = git_blob_sha1(local_path)  # 👈 ¡Cambio clave!
            if local_sha != remote_sha:
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
    btn['state'] = 'disabled'
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
        btn['state'] = 'normal'

# ---------- Interfaz ----------
ventana = tk.Tk()
ventana.title("Sincronizador de Modpack")
ventana.geometry("500x200")
ventana.resizable(False, False)

tk.Label(ventana, text="Sincronizador de mods y configuración",
         font=("Arial", 12, "bold")).pack(pady=10)

btn = tk.Button(ventana, text="Sincronizar ahora",
                command=lambda: threading.Thread(target=instalar).start(),
                bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=20)
btn.pack(pady=10)

barra = ttk.Progressbar(ventana, mode='determinate', length=400)
barra.pack(pady=5)

lbl_estado = tk.Label(ventana, text="", fg="blue")
lbl_estado.pack()

ventana.mainloop()