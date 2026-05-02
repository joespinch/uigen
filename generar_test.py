import os
import re

SRC_DIR = "src"
TEST_DIR_NAME = "tests"
TEST_SUFFIX = ".test"

def to_camel_case(s):
    # Convierte "anon-work-tracker" a "anonWorkTracker"
    parts = re.split(r"[-_]", s)
    return parts[0] + "".join(word.capitalize() for word in parts[1:])

TEMPLATE_HOOK = '''import {{ describe, it, expect }} from "vitest";
import {{ renderHook }} from "@testing-library/react";
{import_line}

describe("{module_name}", () => {{
  it("debería ejecutarse sin errores", () => {{
    const {{ result }} = renderHook(() => {hook_name}());
    expect(result).toBeDefined();
  }});

  it("debería cubrir casos límite", () => {{
    // TODO: Implementar casos límite del hook
    expect(true).toBe(true);
  }});

  it("debería cubrir estados de error", () => {{
    // TODO: Implementar estados de error del hook
    expect(true).toBe(true);
  }});
}});
'''

TEMPLATE_TSX = '''import {{ describe, it, expect }} from "vitest";
import React from "react";
import {{ render }} from "@testing-library/react";
{import_line}

describe("{module_name}", () => {{
  it("debería renderizar sin errores", () => {{
    // TODO: Ajusta el nombre del componente si es necesario
    const {{ container }} = render(<{component_name} />);
    expect(container).toBeTruthy();
  }});

  it("debería cubrir casos límite", () => {{
    // TODO: Implementar casos límite
    expect(true).toBe(true);
  }});

  it("debería cubrir estados de error", () => {{
    // TODO: Implementar estados de error
    expect(true).toBe(true);
  }});
}});
'''

TEMPLATE_TS = '''import {{ describe, it, expect }} from "vitest";
{import_line}

describe("{module_name}", () => {{
  it("debería cubrir el caso exitoso", () => {{
    // TODO: Llama a la función/clase principal y verifica el resultado
    expect(true).toBe(true);
  }});

  it("debería cubrir casos límite", () => {{
    // TODO: Implementar casos límite
    expect(true).toBe(true);
  }});

  it("debería cubrir estados de error", () => {{
    // TODO: Implementar estados de error
    expect(true).toBe(true);
  }});
}});
'''

def is_test_file(filename):
    return TEST_SUFFIX in filename

def get_test_filename(src_path):
    base, ext = os.path.splitext(os.path.basename(src_path))
    test_ext = ".test.tsx" if ext == ".tsx" else ".test.ts"
    return base + test_ext

def get_import_line(src_path, is_hook=False, is_tsx=False):
    rel_path = src_path.replace("\\", "/").replace("src/", "@/").rsplit(".", 1)[0]
    base = os.path.splitext(os.path.basename(src_path))[0]
    camel = to_camel_case(base)
    if is_hook or is_tsx:
        return f'import {camel} from "{rel_path}";'
    else:
        return f'import * as {camel} from "{rel_path}";'

def is_hook(filename):
    return filename.startswith("use") and (filename.endswith(".ts") or filename.endswith(".tsx"))

def main():
    for root, dirs, files in os.walk(SRC_DIR):
        if TEST_DIR_NAME in root or "__tests__" in root:
            continue
        for file in files:
            if file.endswith((".ts", ".tsx")) and not is_test_file(file):
                src_path = os.path.join(root, file)
                test_dir = os.path.join(root, TEST_DIR_NAME)
                os.makedirs(test_dir, exist_ok=True)
                test_filename = get_test_filename(src_path)
                test_path = os.path.join(test_dir, test_filename)
                if not os.path.exists(test_path):
                    module_name = os.path.splitext(file)[0]
                    camel = to_camel_case(module_name)
                    if is_hook(file):
                        import_line = get_import_line(src_path, is_hook=True)
                        content = TEMPLATE_HOOK.format(
                            import_line=import_line,
                            module_name=module_name,
                            hook_name=camel
                        )
                    elif src_path.endswith(".tsx"):
                        import_line = get_import_line(src_path, is_tsx=True)
                        content = TEMPLATE_TSX.format(
                            import_line=import_line,
                            module_name=module_name,
                            component_name=camel
                        )
                    else:
                        import_line = get_import_line(src_path)
                        content = TEMPLATE_TS.format(
                            import_line=import_line,
                            module_name=module_name
                        )
                    with open(test_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Esqueleto creado: {test_path}")

if __name__ == "__main__":
    main()