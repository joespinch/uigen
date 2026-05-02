#!/usr/bin/env python3
"""
generar_doc.py
Lee todo el código fuente del proyecto y genera myproyecto.md
con la estructura y análisis que haría Claude Code.
"""

import os
import json
from pathlib import Path
from datetime import datetime

# ── Configuración ────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

# Extensiones de código a incluir
CODE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mts", ".cjs",
    ".css", ".sql", ".prisma", ".json", ".md",
}

# Archivos/carpetas que NO se leen
EXCLUDE_DIRS = {
    "node_modules", ".next", ".git", "dist", "build",
    "src/generated",           # generado por Prisma
    ".turbo", ".cache",
}

EXCLUDE_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "myproyecto.md",           # no incluirse a sí mismo
}

# Tamaño máximo de archivo a incluir íntegro (bytes)
MAX_FILE_SIZE = 60_000

# ── Helpers ──────────────────────────────────────────────────────────────────

def is_excluded(path: Path) -> bool:
    """Devuelve True si la ruta debe ignorarse."""
    # Directorios excluidos (comprueba cada segmento del path relativo)
    rel = path.relative_to(ROOT)
    parts = rel.parts
    for excl in EXCLUDE_DIRS:
        excl_parts = Path(excl).parts
        # ¿Algún prefijo de 'parts' coincide con excl_parts?
        if parts[: len(excl_parts)] == excl_parts:
            return True
    if path.name in EXCLUDE_FILES:
        return True
    return False


def collect_files() -> list[Path]:
    """Recorre el proyecto y devuelve los archivos relevantes ordenados."""
    result = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue
        if path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        result.append(path)
    return result


def language_for(path: Path) -> str:
    """Devuelve el identificador de lenguaje para el bloque de código."""
    mapping = {
        ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
        ".jsx": "jsx", ".mts": "typescript", ".cjs": "javascript",
        ".css": "css", ".sql": "sql", ".prisma": "prisma",
        ".json": "json", ".md": "markdown",
    }
    return mapping.get(path.suffix.lower(), "text")


def read_file_safe(path: Path) -> str:
    """Lee el archivo; si es demasiado grande lo trunca."""
    try:
        size = path.stat().st_size
        text = path.read_text(encoding="utf-8", errors="replace")
        if size > MAX_FILE_SIZE:
            lines = text.splitlines()
            preview = "\n".join(lines[:120])
            return f"{preview}\n\n… ⚠️  archivo truncado ({size:,} bytes totales)"
        return text
    except Exception as exc:
        return f"[Error al leer: {exc}]"


def build_tree(files: list[Path]) -> str:
    """Genera un árbol de directorios estilo ASCII."""
    dirs: dict = {}
    for f in files:
        rel = f.relative_to(ROOT)
        node = dirs
        for part in rel.parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[rel.parts[-1]] = None

    lines: list[str] = []

    def render(node: dict, prefix: str = "") -> None:
        items = list(node.items())
        for i, (name, child) in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if child is not None:
                extension = "    " if i == len(items) - 1 else "│   "
                render(child, prefix + extension)

    render(dirs)
    return "\n".join(lines)


def parse_package_json() -> dict:
    """Lee package.json y devuelve datos relevantes."""
    pj = ROOT / "package.json"
    if not pj.exists():
        return {}
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
        return {
            "name": data.get("name", ""),
            "version": data.get("version", ""),
            "scripts": data.get("scripts", {}),
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {}),
        }
    except Exception:
        return {}


def find_test_files() -> list[Path]:
    """Encuentra todos los archivos de test en el proyecto."""
    test_files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue
        rel = str(path.relative_to(ROOT).as_posix())
        if "__tests__" in rel and path.suffix in {".ts", ".tsx"}:
            test_files.append(path)
    return test_files


def scan_env_vars(files: list[Path]) -> dict[str, str]:
    """
    Escanea los archivos en busca de process.env.VAR y devuelve
    un dict {VAR: descripcion_deducida}.
    """
    import re
    pattern = re.compile(r'process\.env\.([A-Z_][A-Z0-9_]*)')
    found: dict[str, list[str]] = {}

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in pattern.finditer(text):
            var = match.group(1)
            # Captura contexto de línea para deducir descripción
            start = max(0, match.start() - 120)
            end = min(len(text), match.end() + 120)
            ctx = text[start:end].replace("\n", " ").strip()
            found.setdefault(var, []).append(ctx)

    # Descripciones deducidas heurísticamente
    descriptions: dict[str, str] = {}
    hints = {
        "ANTHROPIC_API_KEY": "Clave de API de Anthropic. Si está ausente, se usa `MockLanguageModel` con respuestas de ejemplo.",
        "JWT_SECRET": "Secreto para firmar tokens JWT. Default: `\"development-secret-key\"`.",
        "NODE_ENV": "Entorno de ejecución (`development` / `production`). Activa cookies `secure` en producción.",
        "DATABASE_URL": "URL de conexión a la base de datos (SQLite por defecto).",
    }
    for var in sorted(found.keys()):
        descriptions[var] = hints.get(var, f"Variable de entorno usada en: `{found[var][0][:80]}…`")
    return descriptions


def parse_prisma_schema() -> dict:
    """Extrae modelos y datasource del schema de Prisma."""
    schema_path = ROOT / "prisma" / "schema.prisma"
    if not schema_path.exists():
        return {}
    import re
    text = schema_path.read_text(encoding="utf-8")

    # Datasource provider
    ds_match = re.search(r'datasource\s+\w+\s*\{[^}]*provider\s*=\s*"([^"]+)"', text, re.S)
    provider = ds_match.group(1) if ds_match else "desconocido"

    # Modelos y sus campos
    models = {}
    for m in re.finditer(r'model\s+(\w+)\s*\{([^}]+)\}', text, re.S):
        model_name = m.group(1)
        fields_raw = m.group(2).strip().splitlines()
        fields = []
        for line in fields_raw:
            line = line.strip()
            if line and not line.startswith("//") and not line.startswith("@@"):
                parts = line.split()
                if len(parts) >= 2:
                    fields.append({"name": parts[0], "type": parts[1]})
        models[model_name] = fields
    return {"provider": provider, "models": models}


def detect_key_layers(files: list[Path]) -> list[dict]:
    """
    Detecta las capas clave del proyecto mirando rutas y contenido mínimo.
    Devuelve lista de {ruta, descripcion}.
    """
    import re
    layers = []

    # Mapa ruta-relativa → descripción deducida
    candidates = {
        "src/app/api/chat/route.ts": "Endpoint principal del chat: recibe mensajes, inyecta system prompt y tools, devuelve stream SSE.",
        "src/lib/file-system.ts": "VirtualFileSystem en memoria (sin escritura a disco); serializable a JSON para persistencia en DB.",
        "src/lib/transform/jsx-transformer.ts": "Transpila JSX con Babel standalone y genera el import map para el iframe de preview.",
        "src/lib/provider.ts": "Selecciona entre `AnthropicProvider` y `MockLanguageModel` según si existe `ANTHROPIC_API_KEY`.",
        "src/lib/auth.ts": "Autenticación con JWT (`jose`). Crea/verifica sesiones en cookie HttpOnly de 7 días.",
        "src/lib/contexts/chat-context.tsx": "Contexto React que envuelve el hook `useChat` del AI SDK para la interfaz de chat.",
        "src/lib/contexts/file-system-context.tsx": "Contexto React que expone el estado del VirtualFileSystem a todos los componentes.",
        "src/actions/index.ts": "Server Actions de Next.js: auth (signUp/signIn/signOut) y CRUD de proyectos via Prisma.",
        "src/lib/prompts/generation.tsx": "System prompt enviado a Claude con instrucciones de generación de componentes React.",
        "src/lib/tools/str-replace.ts": "Tool `str_replace_editor`: crear, ver y editar archivos dentro del VirtualFileSystem.",
        "src/lib/tools/file-manager.ts": "Tool `file_manager`: renombrar y eliminar archivos en el VirtualFileSystem.",
        "src/components/preview/PreviewFrame.tsx": "Iframe de preview: transpila JSX on-demand y renderiza el componente generado.",
        "src/lib/anon-work-tracker.ts": "Rastrea trabajo no guardado en `sessionStorage` para usuarios no autenticados.",
        "src/middleware.ts": "Middleware de Next.js: protege rutas y refresca la cookie de sesión.",
        "prisma/schema.prisma": "Schema Prisma: define modelos `User` y `Project` sobre SQLite.",
    }

    existing_rels = {f.relative_to(ROOT).as_posix() for f in files}
    for rel, desc in candidates.items():
        if rel in existing_rels:
            layers.append({"path": rel, "desc": desc})

    return layers


def detect_auth_section(files: list[Path]) -> dict:
    """
    Escanea el proyecto buscando palabras clave de autenticación
    y devuelve archivos clasificados + detalles técnicos deducidos.
    """
    import re

    AUTH_KEYWORDS = {
        "jwt", "jwtverify", "signjwt", "cookie", "session",
        "signin", "signup", "signout", "bcrypt", "hashpassword",
        "comparepassword", "password", "auth-token", "getsession",
        "createsession", "verifysession", "jwt_secret",
    }

    ROLE_HINTS: dict[str, str] = {
        "src/lib/auth.ts":                     "Núcleo de auth: crea/verifica/destruye la sesión JWT con `jose`. Cookie HttpOnly `auth-token`, 7 días.",
        "src/middleware.ts":                    "Middleware de Next.js: intercepta rutas protegidas y rechaza requests sin sesión válida.",
        "src/actions/index.ts":                 "Server Actions: `signUp` (hash bcrypt), `signIn` (comparación bcrypt), `signOut` (borra cookie).",
        "src/hooks/use-auth.ts":                "Hook React que envuelve las Server Actions y gestiona el estado de auth en el cliente.",
        "src/components/auth/AuthDialog.tsx":   "Dialog modal que muestra `SignInForm` o `SignUpForm` según el estado de la UI.",
        "src/components/auth/SignInForm.tsx":    "Formulario de inicio de sesión (email + password).",
        "src/components/auth/SignUpForm.tsx":    "Formulario de registro de usuario (email + password).",
        "src/lib/anon-work-tracker.ts":         "Detecta trabajo no guardado de usuarios anónimos con `sessionStorage` y activa el prompt de login.",
        "src/app/api/chat/route.ts":            "Verifica sesión antes de persistir el proyecto; rechaza guardado si no hay autenticación.",
    }

    matched: list[dict] = []
    already_added: set[str] = set()

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
        hits = [kw for kw in AUTH_KEYWORDS if kw in text]
        if not hits:
            continue
        role = ROLE_HINTS.get(rel, f"Referencia auth ({', '.join(sorted(hits)[:4])}).")
        if rel not in already_added:
            matched.append({"path": rel, "keywords": sorted(hits)[:6], "role": role})
            already_added.add(rel)

    matched.sort(key=lambda x: (x["path"] not in ROLE_HINTS, x["path"]))

    # Deducir detalles técnicos leyendo auth.ts y actions/index.ts
    tech: dict[str, str] = {}
    auth_file = ROOT / "src/lib/auth.ts"
    if auth_file.exists():
        src = auth_file.read_text(encoding="utf-8", errors="replace")
        algo = re.search(r'alg:\s*["\']([^"\']+)["\']', src)
        exp = re.search(r'setExpirationTime\(["\']([^"\']+)["\']\)', src)
        cookie = re.search(r'COOKIE_NAME\s*=\s*["\']([^"\']+)["\']', src)
        tech["algorithm"] = algo.group(1) if algo else "HS256"
        tech["expiry"] = exp.group(1) if exp else "7d"
        tech["cookie"] = cookie.group(1) if cookie else "auth-token"

    actions_file = ROOT / "src/actions/index.ts"
    if actions_file.exists():
        src = actions_file.read_text(encoding="utf-8", errors="replace")
        rounds = re.search(r'bcrypt\.hash\(\w+,\s*(\d+)\)', src)
        tech["bcrypt_rounds"] = rounds.group(1) if rounds else "10"

    return {"files": matched, "tech": tech}


def detect_main_flows(files: list[Path]) -> list[str]:
    """
    Deduce el flujo principal leyendo el endpoint de chat.
    Devuelve pasos como lista de strings.
    """
    import re
    route = ROOT / "src/app/api/chat/route.ts"
    if not route.exists():
        return []

    text = route.read_text(encoding="utf-8", errors="replace")

    steps = []

    # Detectar herramientas registradas
    tools = re.findall(r'(\w+):\s*build\w+Tool\(', text)
    tools_str = ", ".join(f"`{t}`" for t in tools) if tools else "`str_replace_editor`, `file_manager`"

    # Detectar maxSteps y maxTokens
    max_steps = re.search(r'maxSteps.*?(\d+)', text)
    max_tokens = re.search(r'maxTokens.*?([\d_]+)', text)

    steps = [
        "El usuario escribe en `ChatInterface` → `ChatProvider` (AI SDK `useChat`) gestiona el estado.",
        f"`POST /api/chat/route.ts` recibe los mensajes junto con el estado serializado del `VirtualFileSystem`.",
        f"`getLanguageModel()` elige entre el proveedor Anthropic o `MockLanguageModel` según `ANTHROPIC_API_KEY`.",
        f"`streamText()` (Vercel AI SDK) invoca al modelo con el system prompt y las tools: {tools_str}.",
        "Cada tool-call actualiza el `FileSystemContext` en memoria (sin escritura a disco).",
        "`PreviewFrame` transpila el JSX resultante con Babel standalone y lo renderiza en un `<iframe>` aislado.",
    ]

    if max_steps:
        steps.append(f"Límites configurados: `maxSteps: {max_steps.group(1).replace('_','')}` / `maxTokens: {max_tokens.group(1).replace('_','') if max_tokens else '?'}`.")

    return steps


def detect_data_schemas(files: list[Path], prisma_info: dict) -> list[dict]:
    """
    Construye un mapeo de esquemas de datos usados por la aplicación.
    Prioriza contratos explícitos en TypeScript y modelos de Prisma.
    """
    schemas: list[dict] = []
    existing = {f.relative_to(ROOT).as_posix() for f in files}

    # 1) Modelos persistidos (Prisma)
    for model_name, fields in prisma_info.get("models", {}).items():
        field_list = [f"{f['name']}: {f['type']}" for f in fields]
        schemas.append(
            {
                "name": f"Prisma.{model_name}",
                "source": "prisma/schema.prisma",
                "kind": "Persistencia",
                "fields": field_list,
            }
        )

    # 2) Payload de API de chat
    if "src/app/api/chat/route.ts" in existing:
        schemas.append(
            {
                "name": "ChatRequestBody",
                "source": "src/app/api/chat/route.ts",
                "kind": "API Request",
                "fields": [
                    "messages: any[]",
                    "files: Record<string, FileNode>",
                    "projectId?: string",
                ],
            }
        )

    # 3) Input de creación de proyecto
    if "src/actions/create-project.ts" in existing:
        schemas.append(
            {
                "name": "CreateProjectInput",
                "source": "src/actions/create-project.ts",
                "kind": "Server Action Input",
                "fields": [
                    "name: string",
                    "messages: any[]",
                    "data: Record<string, any>",
                ],
            }
        )

    # 4) Estructura serializada del Virtual File System
    if "src/lib/file-system.ts" in existing:
        schemas.append(
            {
                "name": "FileNode",
                "source": "src/lib/file-system.ts",
                "kind": "Dominio / Estado",
                "fields": [
                    "type: 'file' | 'directory'",
                    "name: string",
                    "path: string",
                    "content?: string",
                    "children?: Map<string, FileNode>",
                ],
            }
        )
        schemas.append(
            {
                "name": "SerializedFileSystem",
                "source": "src/lib/file-system.ts",
                "kind": "Contrato serializado",
                "fields": [
                    "Record<string, FileNode>",
                    "En directorios serializados se omite children (para evitar problemas de JSON)",
                    "En archivos serializados se incluye content",
                ],
            }
        )

    # 5) Shape de proyecto retornado al cliente
    if "src/actions/get-project.ts" in existing:
        schemas.append(
            {
                "name": "ProjectView",
                "source": "src/actions/get-project.ts",
                "kind": "Server Action Output",
                "fields": [
                    "id: string",
                    "name: string",
                    "messages: any[] (JSON.parse)",
                    "data: object (JSON.parse)",
                    "createdAt: Date",
                    "updatedAt: Date",
                ],
            }
        )

    return schemas


# ── Generador principal ──────────────────────────────────────────────────────

def generate(output_path: Path) -> None:
    print("🔍 Recopilando archivos…")
    files = collect_files()
    print(f"   {len(files)} archivos encontrados.")

    pj = parse_package_json()
    tree = build_tree(files)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    test_files = find_test_files()
    env_vars = scan_env_vars(files)
    prisma_info = parse_prisma_schema()
    layers = detect_key_layers(files)
    flow_steps = detect_main_flows(files)
    auth_info = detect_auth_section(files)
    data_schemas = detect_data_schemas(files, prisma_info)

    sections: list[str] = []

    # ── Portada ──────────────────────────────────────────────────────────────
    sections.append(f"""# {pj.get('name', ROOT.name)} — Documentación del proyecto

> Generado automáticamente el {now} por `generar_doc.py`

---
""")

    # ── Resumen ──────────────────────────────────────────────────────────────
    sections.append(f"""## Resumen

| Campo | Valor |
|-------|-------|
| Nombre | `{pj.get('name', '')}` |
| Versión | `{pj.get('version', '')}` |
| Archivos documentados | {len(files)} |
| Raíz del proyecto | `{ROOT}` |

---
""")

    # ── Comandos principales ──────────────────────────────────────────────────
    if pj.get("scripts"):
        scripts = pj["scripts"]
        # Descripciones deducidas del contenido real de cada script
        script_descs = {
            "dev":     "Inicia Next.js con Turbopack en `localhost:3000`.",
            "build":   "Compila la aplicación para producción.",
            "start":   "Ejecuta el servidor de producción.",
            "lint":    "Ejecuta ESLint sobre el proyecto.",
            "test":    "Ejecuta la suite de tests con Vitest (entorno jsdom).",
            "setup":   "Setup inicial: instala dependencias, genera el cliente Prisma y aplica migraciones.",
            "db:reset":"Resetea la base de datos SQLite y re-aplica todas las migraciones.",
        }
        cmd_lines = []
        for k, v in scripts.items():
            desc = script_descs.get(k, v)
            cmd_lines.append(f"npm run {k:<15} # {desc}")
        cmd_block = "\n".join(cmd_lines)
        sections.append(f"""## Comandos principales

```bash
{cmd_block}
```

---
""")

    # ── Tests individuales ────────────────────────────────────────────────────
    if test_files:
        test_lines = []
        test_dirs: set[str] = set()
        for tf in test_files:
            rel = tf.relative_to(ROOT).as_posix()
            parent = str(tf.parent.relative_to(ROOT).as_posix())
            test_dirs.add(parent)
            test_lines.append(f"npx vitest run {rel}")

        # También añadir comandos por directorio
        dir_lines = [f"npx vitest run {d}" for d in sorted(test_dirs)]

        sections.append(f"""### Tests individuales

```bash
# Por archivo
{chr(10).join(sorted(test_lines))}

# Por directorio
{chr(10).join(dir_lines)}
```

---
""")

    # ── Variables de entorno ──────────────────────────────────────────────────
    if env_vars:
        env_rows = "\n".join(
            f"| `{var}` | {desc} |"
            for var, desc in env_vars.items()
        )
        sections.append(f"""## Variables de entorno

| Variable | Descripción |
|----------|-------------|
{env_rows}

---
""")

    # ── Arquitectura ─────────────────────────────────────────────────────────
    if flow_steps:
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(flow_steps))
        sections.append(f"""## Arquitectura

### Flujo de una generación

{steps_md}

---
""")

    # ── Autenticación ─────────────────────────────────────────────────────────
    auth_files = auth_info.get("files", [])
    tech = auth_info.get("tech", {})
    if auth_files:
        tech_lines = []
        if tech.get("algorithm"):
            tech_lines.append(f"- **Algoritmo JWT**: `{tech['algorithm']}`")
        if tech.get("expiry"):
            tech_lines.append(f"- **Expiración del token**: `{tech['expiry']}`")
        if tech.get("cookie"):
            tech_lines.append(f"- **Cookie**: `{tech['cookie']}` (HttpOnly, SameSite=lax)")
        if tech.get("bcrypt_rounds"):
            tech_lines.append(f"- **Bcrypt rounds**: `{tech['bcrypt_rounds']}`")
        tech_block = "\n".join(tech_lines)

        auth_rows = "\n".join(
            f"| `{f['path']}` | {f['role']} | `{', '.join(f['keywords'])}` |"
            for f in auth_files
        )
        sections.append(f"""## Autenticación

{tech_block}

### Archivos relacionados con autenticación

| Archivo | Rol | Palabras clave detectadas |
|---------|-----|--------------------------|
{auth_rows}

---
""")

    # ── Capas clave ───────────────────────────────────────────────────────────
    if layers:
        layer_rows = "\n".join(
            f"| `{l['path']}` | {l['desc']} |"
            for l in layers
        )
        sections.append(f"""### Capas clave

| Archivo | Responsabilidad |
|---------|----------------|
{layer_rows}

---
""")

    # ── Base de datos ─────────────────────────────────────────────────────────
    if prisma_info.get("models"):
        models_md = []
        for model_name, fields in prisma_info["models"].items():
            field_lines = "\n".join(
                f"  - `{f['name']}`: {f['type']}" for f in fields
            )
            models_md.append(f"**{model_name}**\n{field_lines}")
        models_block = "\n\n".join(models_md)
        sections.append(f"""### Base de datos (Prisma + {prisma_info['provider'].upper()})

{models_block}

---
""")

    # ── Dependencias ─────────────────────────────────────────────────────────
    if pj.get("dependencies") or pj.get("devDependencies"):
        deps = ", ".join(f"`{d}`" for d in pj.get("dependencies", {}).keys())
        dev_deps = ", ".join(f"`{d}`" for d in pj.get("devDependencies", {}).keys())
        sections.append(f"""## Dependencias

### Producción
{deps}

### Desarrollo
{dev_deps}

---
""")

    # ── Árbol de archivos ────────────────────────────────────────────────────
    sections.append(f"""## Estructura de archivos

```
{tree}
```

---
""")

    # ── Esquemas de datos (al final) ─────────────────────────────────────────
    if data_schemas:
        blocks = []
        for schema in data_schemas:
            field_lines = "\n".join(f"- `{field}`" for field in schema["fields"])
            blocks.append(
                f"""#### {schema['name']}

Fuente: `{schema['source']}`

Tipo: {schema['kind']}

{field_lines}
"""
            )

        sections.append(
            "### Esquemas de datos\n\n"
            + "\n".join(blocks)
            + "\n---\n"
        )



    # ── Escribir archivo ─────────────────────────────────────────────────────
    full_doc = "\n".join(sections)
    output_path.write_text(full_doc, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"✅ Archivo generado: {output_path}  ({size_kb:.1f} KB)")


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    output = ROOT / "myproyecto.md"
    generate(output)
