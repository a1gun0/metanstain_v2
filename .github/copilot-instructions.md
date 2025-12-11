# Copilot Instructions - metanstain v2

## Project Architecture

**metanstain** is a Python DFIR launcher that orchestrates forensic command-line tools (exiftool, file, strings, xxd, binwalk, bulk_extractor, pdfinfo, identify) through a unified interface.

### Core Design Principles

1. **No external dependencies** - Uses only Python standard library (subprocess, json, argparse, os, shutil)
2. **Safety-first execution** - Never uses `shell=True`; filters dangerous argument patterns (`;&|$(${sudo`) to prevent injection
3. **Graceful degradation** - Auto-installs missing tools via `apt-get` on Debian-based systems; continues batch processing on individual file failures
4. **Modular tool support** - Each tool defined in `TOOLS` dict with metadata (cmd, package, help_args, ejemplos)

### Key Data Flow

```
User Input (CLI args) 
  → Parser (argparse)
  → Path Resolution (positional, --dir, --list)
  → Per-file Processing (safety checks → run_tool_on_file → detect_file_type)
  → Output (text or JSON with metadata)
```

## Critical Code Patterns

### Tool Registration Pattern
All tools are registered in the `TOOLS` dict at top of file. Adding a tool requires:
- `cmd`: executable name
- `package`: apt package name
- `help_args`: flags to retrieve help (use -h or --help depending on tool)
- `descripcion` & `ejemplos`: user-facing documentation

See `exiftool`, `binwalk` entries as examples.

### Path Resolution Strategy
`resolve_paths_from_args()` unifies three input methods:
- Positional args: `metanstain.py -t file archivo1.bin archivo2.bin`
- Directory: `-d /path/` (non-recursive, files only)
- List file: `-L paths.txt` (one path per line, ignores `#` comments)

Deduplicates paths, validates existence, separates valid paths from missing ones.

### Safety Filtering
`filter_dangerous_args()` checks every argument against `BANNED_ARGUMENT_PATTERNS`. This happens **before** tool execution. Never bypass this check; if a new escape vector is discovered, add it to the list.

### Tool Execution & Error Handling
`run_tool_on_file()` returns a structured dict with:
- Tool output (`stdout`, `stderr`)
- Execution state (`exito` boolean, `error` message)
- File type detection (`tipo` dict with extension & file description)
- Arguments applied (`args` list)

Batch operations continue on per-file failure; failures logged in JSON output.

## Developer Workflows

### Quick Syntax Check
```bash
python -m compileall metanstain.py
```

### Add a New Tool
1. Add entry to `TOOLS` dict (see exiftool as template)
2. Verify `help_args` match the tool's actual help invocation
3. Test: `python metanstain.py --tool-help` should display it
4. Test batch: `python metanstain.py -t <tool_name> -d test_files/`

### Output Modes
- **Text**: Default; prints results to stdout or file with `-o`
- **JSON**: `-j` flag; includes metadata, args applied, and file type detection
- **Tool help**: `--tool-help` shows full help for all registered tools

### Testing Considerations
- Tools may not be installed; script attempts auto-install via apt
- Some tools (bulk_extractor) may hang; consider timeout logic if expanding
- JSON output must preserve encoding (`ensure_ascii=False`) for Spanish documentation

## Project Conventions

- **Spanish documentation**: Help text, error messages, tool descriptions are in neutral Spanish
- **No external dependencies**: Maintain stdlib-only approach; avoid adding pip packages
- **File type detection**: Calls `file -b` command when available; gracefully degrades to extension-only detection
- **Batch processing semantics**: Process all files independently; one failure doesn't stop the batch
- **Error transparency**: Return both stdout and stderr; distinguish tool errors from infrastructure errors

## Integration Points

- **subprocess module**: All tool execution goes through `subprocess.run()` with `capture_output=True`
- **apt-get dependency**: Auto-install logic in `ensure_tool_installed()`; only works on Debian-based systems
- **JSON serialization**: Use `json.dumps(..., ensure_ascii=False)` for proper Spanish character handling

## Reference Files
- `metanstain.py` - Single monolithic script; all logic in functions or top-level dicts
- `README.md` - User-facing documentation in Spanish; reference for CLI examples and safety notes
