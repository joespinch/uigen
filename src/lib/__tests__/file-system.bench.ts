import { bench, describe } from "vitest";
import { VirtualFileSystem } from "@/lib/file-system";

// ─── Fixtures ────────────────────────────────────────────────────────────────

function buildLargeContent(lines: number): string {
  return Array.from(
    { length: lines },
    (_, i) => `const variable${i} = "value_${i}"; // comment ${i}`
  ).join("\n");
}

function buildDeepFileMap(depth: number, filesPerDir: number): Record<string, string> {
  const data: Record<string, string> = {};
  const segments = Array.from({ length: depth }, (_, i) => `dir${i}`);

  for (let d = 1; d <= depth; d++) {
    const dir = "/" + segments.slice(0, d).join("/");
    for (let f = 0; f < filesPerDir; f++) {
      data[`${dir}/file${f}.ts`] = `export const x${f} = ${f};`;
    }
  }
  return data;
}

// ─── replaceInFile ────────────────────────────────────────────────────────────

describe("replaceInFile", () => {
  const small = buildLargeContent(100);
  const medium = buildLargeContent(500);
  const large = buildLargeContent(2000);

  bench("archivo pequeño (100 líneas, ~30 reemplazos)", () => {
    const fs = new VirtualFileSystem();
    fs.createFile("/test.ts", small);
    fs.replaceInFile("/test.ts", "const", "let");
  });

  bench("archivo mediano (500 líneas, ~150 reemplazos)", () => {
    const fs = new VirtualFileSystem();
    fs.createFile("/test.ts", medium);
    fs.replaceInFile("/test.ts", "const", "let");
  });

  bench("archivo grande (2000 líneas, ~600 reemplazos)", () => {
    const fs = new VirtualFileSystem();
    fs.createFile("/test.ts", large);
    fs.replaceInFile("/test.ts", "const", "let");
  });

  bench("reemplazo con string no encontrado (worst-case includes)", () => {
    const fs = new VirtualFileSystem();
    fs.createFile("/test.ts", large);
    fs.replaceInFile("/test.ts", "NOTFOUND_TOKEN_XYZ", "replacement");
  });
});

// ─── createFile (deep nesting) ────────────────────────────────────────────────

describe("createFile", () => {
  bench("ruta plana — 50 archivos en raíz", () => {
    const fs = new VirtualFileSystem();
    for (let i = 0; i < 50; i++) {
      fs.createFile(`/file${i}.ts`, `export const x = ${i};`);
    }
  });

  bench("rutas anidadas — 50 archivos en 5 dirs distintos", () => {
    const fs = new VirtualFileSystem();
    for (let d = 0; d < 5; d++) {
      for (let f = 0; f < 10; f++) {
        fs.createFile(`/dir${d}/sub/file${f}.ts`, `export const x = ${f};`);
      }
    }
  });

  bench("rutas muy anidadas — 1 archivo con 8 niveles de profundidad", () => {
    const fs = new VirtualFileSystem();
    for (let i = 0; i < 20; i++) {
      fs.createFile(`/a/b/c/d/e/f/g/h/file${i}.ts`, "export const x = 1;");
    }
  });
});

// ─── deserialize ─────────────────────────────────────────────────────────────

describe("deserialize (from flat map)", () => {
  const small = buildDeepFileMap(3, 3);   // 9 files
  const medium = buildDeepFileMap(5, 5);  // 25 files
  const large = buildDeepFileMap(8, 8);   // 64 files

  bench("9 archivos en 3 directorios anidados", () => {
    const fs = new VirtualFileSystem();
    fs.deserialize(small);
  });

  bench("25 archivos en 5 directorios anidados", () => {
    const fs = new VirtualFileSystem();
    fs.deserialize(medium);
  });

  bench("64 archivos en 8 directorios anidados", () => {
    const fs = new VirtualFileSystem();
    fs.deserialize(large);
  });
});

// ─── deserializeFromNodes ────────────────────────────────────────────────────

describe("deserializeFromNodes", () => {
  function buildNodeMap(depth: number, filesPerDir: number) {
    const nodes: Record<string, { type: "file" | "directory"; name: string; path: string; content?: string }> = {
      "/": { type: "directory", name: "/", path: "/" },
    };
    const segments = Array.from({ length: depth }, (_, i) => `dir${i}`);

    for (let d = 1; d <= depth; d++) {
      const dir = "/" + segments.slice(0, d).join("/");
      nodes[dir] = { type: "directory", name: segments[d - 1], path: dir };
      for (let f = 0; f < filesPerDir; f++) {
        const p = `${dir}/file${f}.ts`;
        nodes[p] = { type: "file", name: `file${f}.ts`, path: p, content: `export const x${f} = ${f};` };
      }
    }
    return nodes;
  }

  const small = buildNodeMap(3, 3);
  const medium = buildNodeMap(5, 5);
  const large = buildNodeMap(8, 8);

  bench("9 archivos en 3 directorios", () => {
    const fs = new VirtualFileSystem();
    fs.deserializeFromNodes(small);
  });

  bench("25 archivos en 5 directorios", () => {
    const fs = new VirtualFileSystem();
    fs.deserializeFromNodes(medium);
  });

  bench("64 archivos en 8 directorios", () => {
    const fs = new VirtualFileSystem();
    fs.deserializeFromNodes(large);
  });
});

// ─── serialize ───────────────────────────────────────────────────────────────

describe("serialize", () => {
  bench("10 archivos", () => {
    const fs = new VirtualFileSystem();
    for (let i = 0; i < 10; i++) fs.createFile(`/file${i}.ts`, `export const x = ${i};`);
    fs.serialize();
  });

  bench("100 archivos en estructura plana", () => {
    const fs = new VirtualFileSystem();
    for (let i = 0; i < 100; i++) fs.createFile(`/file${i}.ts`, `export const x = ${i};`);
    fs.serialize();
  });

  bench("50 archivos anidados (3 niveles)", () => {
    const fs = new VirtualFileSystem();
    const data = buildDeepFileMap(3, 5);
    fs.deserialize(data);
    fs.serialize();
  });
});
