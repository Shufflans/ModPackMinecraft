import os
import hashlib
import json

# Carpetas que quieres sincronizar
SYNC_FOLDERS = ['mods', 'config']

def sha1_digest(filepath):
    """Calcula el hash SHA1 del archivo"""
    h = hashlib.sha1()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def generar_manifest(base_path, version):
    manifest = {"version": version, "files": []}
    for folder in SYNC_FOLDERS:
        full_folder = os.path.join(base_path, folder)
        for root, _, files in os.walk(full_folder):
            for file in files:
                file_path = os.path.join(root, file)
                # Ruta relativa desde base_path
                rel_path = os.path.relpath(file_path, base_path).replace('\\', '/')
                hash_val = sha1_digest(file_path)
                manifest["files"].append({"path": rel_path, "hash": hash_val})
    # Guardar
    with open(os.path.join(base_path, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifiesto v{version} generado con {len(manifest['files'])} archivos.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        version = input("Introduce el número de versión (ej. 1.0.0): ").strip()
    else:
        version = sys.argv[1]
    base = os.path.abspath(os.path.dirname(__file__))
    generar_manifest(base, version)