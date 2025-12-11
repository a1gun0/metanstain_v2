# metanstain v2
A diferencia de metanstain v1 que estaba diseñado para un usuario neofito o a nivel fundacional, el v2 esta pensado para agilizar el trabajo de el forence, en este caso, yo.
lo que me interesaba lograr era poder tener un solo script que me permita correr diferentes herramientas forences en los archivos de una carpeta (no recursivamente) de forma de poder obtener un .json con los metadatos ordenados de cada archivo dentro del directorio.

metanstain v2 es un lanzador DFIR en Python que orquesta utilidades de línea de comandos como `exiftool`, `file`, `strings`, `xxd`, `binwalk`, `bulk_extractor`, `pdfinfo` e `identify`. El script verifica si cada herramienta está instalada, intenta instalarla con `apt` si falta, filtra argumentos peligrosos y permite ejecutar análisis por lote sin detenerse ante fallos individuales.

Cabe destacar que se le pueden pasar los mismos parametros que a las herramientas en las que esta basado luego de elegir la herramienta.
a futuro quizas reemplace los nombres de las  herramientas por un numero o letra, quizas en la v3.

## Requisitos
- Python 3.8 o superior disponible en el sistema.
- Acceso a `apt-get` para instalar herramientas que falten (entornos Debian/Kali/Ubuntu). Si no hay `apt`, instala manualmente las dependencias anteriores.
- Permisos suficientes para ejecutar las herramientas forenses mencionadas.

## Instalación
1. Clona o descarga este repositorio.
2. Opcional: crea y activa un entorno virtual de Python.
3. No requiere dependencias externas de Python (usa solo la biblioteca estándar).
4. Asegura que el script sea ejecutable:
   ```bash
   chmod +x metanstain.py
   ```

## Uso básico
El parámetro principal es la herramienta a invocar:
```bash
python metanstain.py -h

python metanstain.py -t <herramienta> [opciones_de_metanstain] -- [args_de_herramienta]
```

Opciones clave de metanstain:
- `-t, --tool`: nombre de la herramienta (exiftool, file, strings, xxd, binwalk, bulk_extractor, pdfinfo, identify).
- `paths` posicionales: uno o varios archivos.
- `-d, --dir <ruta>`: procesa todos los archivos regulares del directorio indicado (no recursivo).
- `-L, --list <archivo>`: usa un archivo de texto con rutas (una por línea, ignora vacías o que empiezan con `#`).
- `-o, --output <archivo>`: guarda la salida textual o JSON en un archivo.
- `-j, --json`: devuelve resultados estructurados en JSON (incluye ruta, herramienta, argumentos, salidas y errores).
- `--tool-help`: muestra la ayuda completa de cada herramienta y ejemplos sin ejecutar análisis.

Los argumentos nativos de la herramienta se pasan tras los parámetros de metanstain y son reutilizados para cada archivo. Ejemplo:
```bash
python metanstain.py -t xxd -c 32 archivo1.bin archivo2.bin
python metanstain.py -t exiftool -gps:all -n foto.jpg
```

## Ejemplos comunes
- Varios archivos posicionales:
  ```bash
  python metanstain.py -t file muestra1.bin muestra2.bin
  ```
- Directorio completo (no recursivo):
  ```bash
  python metanstain.py -t binwalk -d /ruta/firmware/
  ```
- Lista de rutas desde archivo y salida JSON a disco:
  ```bash
  python metanstain.py -t strings -L rutas.txt -j -o resultados.json
  ```
- Ayuda resumida y completa de herramientas:
  ```bash
  python metanstain.py -h
  python metanstain.py --tool-help
  ```

## Notas de seguridad y ejecución
- El script nunca usa `shell=True` y filtra argumentos con caracteres peligrosos como `;`, `&&`, `|`, `` ` ``, `$(`, `${` o `sudo`. Si se detectan, se marca el archivo con error y el lote continúa.
- Cada archivo se procesa de forma independiente; si una ejecución falla, se registra en la salida (incluido JSON) pero no detiene el resto.
- En modo JSON, los resultados incluyen los argumentos aplicados a la herramienta y el tipo de archivo detectado (extensión básica).

## Resolución de problemas
- Si `-h` o `--tool-help` parecen tardar, el script limita el tiempo al obtener la ayuda de cada herramienta para evitar bloqueos.
- Si falta una herramienta y no hay `apt`, instala manualmente desde tu distribución y vuelve a ejecutar.

## Desarrollo y pruebas
- Comprueba la sintaxis rápidamente con:
  ```bash
  python -m compileall metanstain.py
  ```
- Las ayudas y ejemplos se generan en español neutro para mantener coherencia en la salida.
