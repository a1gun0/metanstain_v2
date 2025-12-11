import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

TOOLS: Dict[str, Dict[str, object]] = {
    "exiftool": {
        "cmd": "exiftool",
        "package": "exiftool",
        "descripcion": "Lectura de metadatos de archivos.",
        "help_args": ["-h"],
        "ejemplos": [
            "metanstain.py -t exiftool -gps:all -n foto.jpg",
            "metanstain.py -t exiftool -a -u documento.pdf",
        ],
    },
    "file": {
        "cmd": "file",
        "package": "file",
        "descripcion": "Identificación rápida de tipo de archivo.",
        "help_args": ["--help"],
        "ejemplos": ["metanstain.py -t file muestra.bin"],
    },
    "strings": {
        "cmd": "strings",
        "package": "binutils",
        "descripcion": "Extrae cadenas imprimibles.",
        "help_args": ["--help"],
        "ejemplos": ["metanstain.py -t strings -n 8 malware.bin"],
    },
    "xxd": {
        "cmd": "xxd",
        "package": "xxd",
        "descripcion": "Volcado hexadecimal.",
        "help_args": ["--help"],
        "ejemplos": [
            "metanstain.py -t xxd -c 32 -p muestra.bin",
            "metanstain.py -t xxd -g 4 archivo.bin",
        ],
    },
    "binwalk": {
        "cmd": "binwalk",
        "package": "binwalk",
        "descripcion": "Análisis de firmware y binarios.",
        "help_args": ["--help"],
        "ejemplos": ["metanstain.py -t binwalk -e firmware.bin"],
    },
    "bulk_extractor": {
        "cmd": "bulk_extractor",
        "package": "bulk-extractor",
        "descripcion": "Extracción masiva de artefactos forenses.",
        "help_args": ["--help"],
        "ejemplos": ["metanstain.py -t bulk_extractor imagen.dd"],
    },
    "pdfinfo": {
        "cmd": "pdfinfo",
        "package": "poppler-utils",
        "descripcion": "Información de documentos PDF.",
        "help_args": ["-h"],
        "ejemplos": ["metanstain.py -t pdfinfo reporte.pdf"],
    },
    "identify": {
        "cmd": "identify",
        "package": "imagemagick",
        "descripcion": "Identifica imágenes (ImageMagick).",
        "help_args": ["--help"],
        "ejemplos": ["metanstain.py -t identify foto.png"],
    },
}

BANNED_ARGUMENT_PATTERNS = [";", "&&", "|", "`", "$(", "${", "sudo"]


def filter_dangerous_args(args: List[str]) -> Tuple[bool, Optional[str]]:
    for arg in args:
        for pattern in BANNED_ARGUMENT_PATTERNS:
            if pattern in arg:
                return False, f"Argumento no permitido: {arg}"
    return True, None


def ensure_tool_installed(tool_key: str) -> bool:
    info = TOOLS.get(tool_key)
    if not info:
        return False
    cmd = str(info["cmd"])
    if shutil.which(cmd):
        return True
    package = str(info.get("package", cmd))
    print(f"Herramienta '{cmd}' no encontrada. Intentando instalar {package} con apt...")
    try:
        install_result = subprocess.run(
            ["apt-get", "update"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if install_result.returncode != 0:
            print("No se pudo actualizar el índice de paquetes con apt.")
            return False
        result = subprocess.run(
            ["apt-get", "install", "-y", package],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0 and shutil.which(cmd):
            print(f"Herramienta '{cmd}' instalada correctamente.")
            return True
        print(f"No se pudo instalar '{cmd}'. Salida: {result.stderr}")
        return False
    except FileNotFoundError:
        print("apt-get no está disponible en este entorno.")
        return False


def normalize_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def resolve_paths_from_args(
    positional_paths: Optional[List[str]], dir_path: Optional[str], list_file: Optional[str]
) -> Tuple[List[str], List[str]]:
    paths: List[str] = []
    missing: List[str] = []

    def add_path(path_item: str):
        normalized = normalize_path(path_item)
        if os.path.exists(normalized):
            if os.path.isfile(normalized):
                paths.append(normalized)
            else:
                missing.append(normalized)
        else:
            missing.append(normalized)

    if positional_paths:
        for path in positional_paths:
            add_path(path)

    if dir_path:
        normalized_dir = normalize_path(dir_path)
        if os.path.isdir(normalized_dir):
            for entry in os.listdir(normalized_dir):
                candidate = os.path.join(normalized_dir, entry)
                if os.path.isfile(candidate):
                    paths.append(os.path.abspath(candidate))
        else:
            missing.append(normalized_dir)

    if list_file:
        normalized_list = normalize_path(list_file)
        if os.path.isfile(normalized_list):
            with open(normalized_list, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    cleaned = line.strip()
                    if not cleaned or cleaned.startswith("#"):
                        continue
                    add_path(cleaned)
        else:
            missing.append(normalized_list)

    # Eliminar duplicados preservando el orden
    unique_paths = []
    seen = set()
    for path in paths:
        if path not in seen:
            unique_paths.append(path)
            seen.add(path)

    return unique_paths, missing


def detect_file_type(path: str) -> Dict[str, Optional[str]]:
    extension = os.path.splitext(path)[1].lower().lstrip(".") or None
    description = None
    if shutil.which("file") and os.path.isfile(path):
        try:
            proc = subprocess.run(
                ["file", "-b", path],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.stdout:
                description = proc.stdout.strip()
        except Exception:
            description = None
    return {"extension": extension, "descripcion": description}


def run_tool_on_file(tool_key: str, file_path: str, tool_args: List[str]) -> Dict[str, object]:
    info = TOOLS.get(tool_key)
    cmd = str(info["cmd"]) if info else tool_key
    result: Dict[str, object] = {
        "archivo": file_path,
        "herramienta": tool_key,
        "args": tool_args,
        "stdout": "",
        "stderr": "",
        "exito": False,
        "error": None,
        "tipo": detect_file_type(file_path),
    }

    if not os.path.isfile(file_path):
        result["error"] = "Ruta no encontrada o no es un archivo regular"
        return result

    command = [cmd] + tool_args + [file_path]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        if proc.returncode == 0:
            result["exito"] = True
        else:
            result["error"] = f"La herramienta devolvió un código distinto de cero ({proc.returncode})."
    except FileNotFoundError:
        result["error"] = "La herramienta seleccionada no está disponible en el sistema."
    except Exception as exc:  # pragma: no cover - salvaguarda
        result["error"] = f"Error al ejecutar la herramienta: {exc}"
    return result


 main
    info = TOOLS.get(tool_key)
    if not info:
        return "Herramienta no definida."
    cmd = str(info["cmd"])
    help_args = info.get("help_args") or ["--help"]
    try:
        proc = subprocess.run(
            [cmd] + list(help_args),
            capture_output=True,
            text=True,
            check=False,
 main
        )
        output = proc.stdout or proc.stderr
        if not output:
            return "Ayuda no disponible."
        lines = output.splitlines()
        if limit:
            return "\n".join(lines[:limit])
        return output
    except FileNotFoundError:
        return "La herramienta no está instalada o no se encontró en PATH."
main
    except Exception as exc:
        return f"No se pudo obtener la ayuda: {exc}"


def print_tools_list_summary(limit: int = 12) -> None:
    print("\nHerramientas disponibles (resumen):")
    for name, info in TOOLS.items():
        print(f"- {name}: {info.get('descripcion', 'Sin descripción')}")
        help_text = get_tool_help_output(name, limit=limit)
        indented = "\n".join(f"  {line}" for line in help_text.splitlines())
        print(indented)


def show_full_tools_help() -> None:
    for name, info in TOOLS.items():
        print(f"=== {name} ===")
        print(info.get("descripcion", ""))
        print(get_tool_help_output(name))
        ejemplos = info.get("ejemplos", [])
        if ejemplos:
            print("Ejemplos de uso:")
            for ejemplo in ejemplos:
                print(f"  {ejemplo}")
        print()


def build_json_results(results: List[Dict[str, object]]) -> str:
    return json.dumps(results, ensure_ascii=False, indent=2)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lanzador DFIR para herramientas comunes.",
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", help="Rutas de archivos a procesar.")
    parser.add_argument("-t", "--tool", help="Herramienta a utilizar.")
    parser.add_argument("-o", "--output", help="Archivo donde guardar la salida.")
    parser.add_argument("-j", "--json", action="store_true", help="Salida en formato JSON.")
    parser.add_argument("-d", "--dir", dest="dir", help="Procesar todos los archivos de un directorio.")
    parser.add_argument(
        "-L",
        "--list",
        dest="list_file",
        help="Archivo con rutas, una por línea (soporta comentarios con #).",
    )
    parser.add_argument("--tool-help", action="store_true", help="Mostrar ayuda completa de todas las herramientas.")
    parser.add_argument("-h", "--help", action="store_true", help="Mostrar esta ayuda y resumen de herramientas.")
    return parser


def handle_help_and_exit(parser: argparse.ArgumentParser) -> None:
    print(parser.format_help())
    print_tools_list_summary()
    sys.exit(0)


def main(argv: Optional[List[str]] = None) -> None:
 main
                    "herramienta": args.tool,
                    "args": unknown_args,
                    "stdout": "",
                    "stderr": "",
                    "exito": False,
 main

if __name__ == "__main__":
    main()
