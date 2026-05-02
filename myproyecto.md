# uigen — Documentación del proyecto

> Generado automáticamente el 2026-05-01 14:14 por `generar_doc.py`

---

## Resumen

| Campo | Valor |
|-------|-------|
| Nombre | `uigen` |
| Versión | `0.1.0` |
| Archivos documentados | 69 |
| Raíz del proyecto | `C:\config\claude\proyectos\uigen` |

---

## Comandos principales

```bash
npm run dev             # Inicia Next.js con Turbopack en `localhost:3000`.
npm run dev:daemon      # next dev --turbopack > logs.txt 2>&1 & echo 'Server started, writing logs to logs.txt'
npm run build           # Compila la aplicación para producción.
npm run start           # Ejecuta el servidor de producción.
npm run lint            # Ejecuta ESLint sobre el proyecto.
npm run test            # Ejecuta la suite de tests con Vitest (entorno jsdom).
npm run setup           # Setup inicial: instala dependencias, genera el cliente Prisma y aplica migraciones.
npm run db:reset        # Resetea la base de datos SQLite y re-aplica todas las migraciones.
```

---

### Tests individuales

```bash
# Por archivo
npx vitest run src/components/chat/__tests__/ChatInterface.test.tsx
npx vitest run src/components/chat/__tests__/MarkdownRenderer.test.tsx
npx vitest run src/components/chat/__tests__/MessageInput.test.tsx
npx vitest run src/components/chat/__tests__/MessageList.test.tsx
npx vitest run src/components/editor/__tests__/file-tree.test.tsx
npx vitest run src/lib/__tests__/file-system.test.ts
npx vitest run src/lib/contexts/__tests__/chat-context.test.tsx
npx vitest run src/lib/contexts/__tests__/file-system-context.test.tsx
npx vitest run src/lib/transform/__tests__/jsx-transformer.test.ts

# Por directorio
npx vitest run src/components/chat/__tests__
npx vitest run src/components/editor/__tests__
npx vitest run src/lib/__tests__
npx vitest run src/lib/contexts/__tests__
npx vitest run src/lib/transform/__tests__
```

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic. Si está ausente, se usa `MockLanguageModel` con respuestas de ejemplo. |
| `JWT_SECRET` | Secreto para firmar tokens JWT. Default: `"development-secret-key"`. |
| `NODE_ENV` | Entorno de ejecución (`development` / `production`). Activa cookies `secure` en producción. |

---

## Arquitectura

### Flujo de una generación

1. El usuario escribe en `ChatInterface` → `ChatProvider` (AI SDK `useChat`) gestiona el estado.
2. `POST /api/chat/route.ts` recibe los mensajes junto con el estado serializado del `VirtualFileSystem`.
3. `getLanguageModel()` elige entre el proveedor Anthropic o `MockLanguageModel` según `ANTHROPIC_API_KEY`.
4. `streamText()` (Vercel AI SDK) invoca al modelo con el system prompt y las tools: `str_replace_editor`, `file_manager`.
5. Cada tool-call actualiza el `FileSystemContext` en memoria (sin escritura a disco).
6. `PreviewFrame` transpila el JSX resultante con Babel standalone y lo renderiza en un `<iframe>` aislado.
7. Límites configurados: `maxSteps: 4` / `maxTokens: 10000`.

---

## Autenticación

- **Algoritmo JWT**: `HS256`
- **Expiración del token**: `7d`
- **Cookie**: `auth-token` (HttpOnly, SameSite=lax)
- **Bcrypt rounds**: `10`

### Archivos relacionados con autenticación

| Archivo | Rol | Palabras clave detectadas |
|---------|-----|--------------------------|
| `src/actions/index.ts` | Server Actions: `signUp` (hash bcrypt), `signIn` (comparación bcrypt), `signOut` (borra cookie). | `bcrypt, createsession, getsession, password, session, signin` |
| `src/app/api/chat/route.ts` | Verifica sesión antes de persistir el proyecto; rechaza guardado si no hay autenticación. | `getsession, session` |
| `src/components/auth/AuthDialog.tsx` | Dialog modal que muestra `SignInForm` o `SignUpForm` según el estado de la UI. | `signin, signup` |
| `src/components/auth/SignInForm.tsx` | Formulario de inicio de sesión (email + password). | `password, signin` |
| `src/components/auth/SignUpForm.tsx` | Formulario de registro de usuario (email + password). | `password, signup` |
| `src/hooks/use-auth.ts` | Hook React que envuelve las Server Actions y gestiona el estado de auth en el cliente. | `password, signin, signup` |
| `src/lib/anon-work-tracker.ts` | Detecta trabajo no guardado de usuarios anónimos con `sessionStorage` y activa el prompt de login. | `session` |
| `src/lib/auth.ts` | Núcleo de auth: crea/verifica/destruye la sesión JWT con `jose`. Cookie HttpOnly `auth-token`, 7 días. | `auth-token, cookie, createsession, getsession, jwt, jwt_secret` |
| `src/middleware.ts` | Middleware de Next.js: intercepta rutas protegidas y rechaza requests sin sesión válida. | `session, verifysession` |
| `CLAUDE.md` | Referencia auth (bcrypt, cookie, jwt, jwt_secret). | `bcrypt, cookie, jwt, jwt_secret, password, session` |
| `node-compat.cjs` | Referencia auth (session). | `session` |
| `package.json` | Referencia auth (bcrypt). | `bcrypt` |
| `prisma/migrations/20250619172131_init/migration.sql` | Referencia auth (password). | `password` |
| `prisma/schema.prisma` | Referencia auth (password). | `password` |
| `src/actions/create-project.ts` | Referencia auth (getsession, session). | `getsession, session` |
| `src/actions/get-project.ts` | Referencia auth (getsession, session). | `getsession, session` |
| `src/actions/get-projects.ts` | Referencia auth (getsession, session). | `getsession, session` |
| `src/components/HeaderActions.tsx` | Referencia auth (signin, signout, signup). | `signin, signout, signup` |

---

### Capas clave

| Archivo | Responsabilidad |
|---------|----------------|
| `src/app/api/chat/route.ts` | Endpoint principal del chat: recibe mensajes, inyecta system prompt y tools, devuelve stream SSE. |
| `src/lib/file-system.ts` | VirtualFileSystem en memoria (sin escritura a disco); serializable a JSON para persistencia en DB. |
| `src/lib/transform/jsx-transformer.ts` | Transpila JSX con Babel standalone y genera el import map para el iframe de preview. |
| `src/lib/provider.ts` | Selecciona entre `AnthropicProvider` y `MockLanguageModel` según si existe `ANTHROPIC_API_KEY`. |
| `src/lib/auth.ts` | Autenticación con JWT (`jose`). Crea/verifica sesiones en cookie HttpOnly de 7 días. |
| `src/lib/contexts/chat-context.tsx` | Contexto React que envuelve el hook `useChat` del AI SDK para la interfaz de chat. |
| `src/lib/contexts/file-system-context.tsx` | Contexto React que expone el estado del VirtualFileSystem a todos los componentes. |
| `src/actions/index.ts` | Server Actions de Next.js: auth (signUp/signIn/signOut) y CRUD de proyectos via Prisma. |
| `src/lib/prompts/generation.tsx` | System prompt enviado a Claude con instrucciones de generación de componentes React. |
| `src/lib/tools/str-replace.ts` | Tool `str_replace_editor`: crear, ver y editar archivos dentro del VirtualFileSystem. |
| `src/lib/tools/file-manager.ts` | Tool `file_manager`: renombrar y eliminar archivos en el VirtualFileSystem. |
| `src/components/preview/PreviewFrame.tsx` | Iframe de preview: transpila JSX on-demand y renderiza el componente generado. |
| `src/lib/anon-work-tracker.ts` | Rastrea trabajo no guardado en `sessionStorage` para usuarios no autenticados. |
| `src/middleware.ts` | Middleware de Next.js: protege rutas y refresca la cookie de sesión. |
| `prisma/schema.prisma` | Schema Prisma: define modelos `User` y `Project` sobre SQLite. |

---

### Base de datos (Prisma + SQLITE)

**User**
  - `id`: String
  - `email`: String
  - `password`: String
  - `createdAt`: DateTime
  - `updatedAt`: DateTime
  - `projects`: Project[]

**Project**
  - `id`: String
  - `name`: String
  - `userId`: String?
  - `messages`: String
  - `data`: String

---

## Dependencias

### Producción
`@ai-sdk/anthropic`, `@babel/standalone`, `@monaco-editor/react`, `@prisma/client`, `@radix-ui/react-dialog`, `@radix-ui/react-label`, `@radix-ui/react-popover`, `@radix-ui/react-scroll-area`, `@radix-ui/react-separator`, `@radix-ui/react-slot`, `@radix-ui/react-tabs`, `@tailwindcss/typography`, `ai`, `bcrypt`, `class-variance-authority`, `clsx`, `cmdk`, `jose`, `lucide-react`, `next`, `react`, `react-dom`, `react-markdown`, `react-resizable-panels`, `server-only`, `tailwind-merge`

### Desarrollo
`@tailwindcss/postcss`, `@testing-library/dom`, `@testing-library/react`, `@testing-library/user-event`, `@types/babel__standalone`, `@types/bcrypt`, `@types/node`, `@types/react`, `@types/react-dom`, `@vitejs/plugin-react`, `eslint`, `eslint-config-next`, `jsdom`, `prisma`, `tailwindcss`, `tw-animate-css`, `typescript`, `vite-tsconfig-paths`, `vitest`

---

## Estructura de archivos

```
├── .claude/
│   └── settings.local.json
├── .eslintrc.json
├── CLAUDE.md
├── components.json
├── next-env.d.ts
├── next.config.ts
├── node-compat.cjs
├── package.json
├── prisma/
│   ├── migrations/
│   │   ├── 20250619172131_init/
│   │   │   └── migration.sql
│   │   ├── 20250619174023_optional_userid/
│   │   │   └── migration.sql
│   │   └── 20250619174322_remove_filesystem_add_data_to_project/
│   │       └── migration.sql
│   └── schema.prisma
├── README.md
├── src/
│   ├── actions/
│   │   ├── create-project.ts
│   │   ├── get-project.ts
│   │   ├── get-projects.ts
│   │   └── index.ts
│   ├── app/
│   │   ├── [projectId]/
│   │   │   └── page.tsx
│   │   ├── api/
│   │   │   └── chat/
│   │   │       └── route.ts
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── main-content.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthDialog.tsx
│   │   │   ├── SignInForm.tsx
│   │   │   └── SignUpForm.tsx
│   │   ├── chat/
│   │   │   ├── __tests__/
│   │   │   │   ├── ChatInterface.test.tsx
│   │   │   │   ├── MarkdownRenderer.test.tsx
│   │   │   │   ├── MessageInput.test.tsx
│   │   │   │   └── MessageList.test.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MarkdownRenderer.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── MessageList.tsx
│   │   ├── editor/
│   │   │   ├── __tests__/
│   │   │   │   └── file-tree.test.tsx
│   │   │   ├── CodeEditor.tsx
│   │   │   └── FileTree.tsx
│   │   ├── HeaderActions.tsx
│   │   ├── preview/
│   │   │   └── PreviewFrame.tsx
│   │   └── ui/
│   │       ├── button.tsx
│   │       ├── command.tsx
│   │       ├── dialog.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       ├── popover.tsx
│   │       ├── resizable.tsx
│   │       ├── scroll-area.tsx
│   │       ├── separator.tsx
│   │       └── tabs.tsx
│   ├── hooks/
│   │   └── use-auth.ts
│   ├── lib/
│   │   ├── __tests__/
│   │   │   └── file-system.test.ts
│   │   ├── anon-work-tracker.ts
│   │   ├── auth.ts
│   │   ├── contexts/
│   │   │   ├── __tests__/
│   │   │   │   ├── chat-context.test.tsx
│   │   │   │   └── file-system-context.test.tsx
│   │   │   ├── chat-context.tsx
│   │   │   └── file-system-context.tsx
│   │   ├── file-system.ts
│   │   ├── prisma.ts
│   │   ├── prompts/
│   │   │   └── generation.tsx
│   │   ├── provider.ts
│   │   ├── tools/
│   │   │   ├── file-manager.ts
│   │   │   └── str-replace.ts
│   │   ├── transform/
│   │   │   ├── __tests__/
│   │   │   │   └── jsx-transformer.test.ts
│   │   │   └── jsx-transformer.ts
│   │   └── utils.ts
│   └── middleware.ts
├── tsconfig.json
└── vitest.config.mts
```

---

### Esquemas de datos

#### Prisma.User

Fuente: `prisma/schema.prisma`

Tipo: Persistencia

- `id: String`
- `email: String`
- `password: String`
- `createdAt: DateTime`
- `updatedAt: DateTime`
- `projects: Project[]`

#### Prisma.Project

Fuente: `prisma/schema.prisma`

Tipo: Persistencia

- `id: String`
- `name: String`
- `userId: String?`
- `messages: String`
- `data: String`

#### ChatRequestBody

Fuente: `src/app/api/chat/route.ts`

Tipo: API Request

- `messages: any[]`
- `files: Record<string, FileNode>`
- `projectId?: string`

#### CreateProjectInput

Fuente: `src/actions/create-project.ts`

Tipo: Server Action Input

- `name: string`
- `messages: any[]`
- `data: Record<string, any>`

#### FileNode

Fuente: `src/lib/file-system.ts`

Tipo: Dominio / Estado

- `type: 'file' | 'directory'`
- `name: string`
- `path: string`
- `content?: string`
- `children?: Map<string, FileNode>`

#### SerializedFileSystem

Fuente: `src/lib/file-system.ts`

Tipo: Contrato serializado

- `Record<string, FileNode>`
- `En directorios serializados se omite children (para evitar problemas de JSON)`
- `En archivos serializados se incluye content`

#### ProjectView

Fuente: `src/actions/get-project.ts`

Tipo: Server Action Output

- `id: string`
- `name: string`
- `messages: any[] (JSON.parse)`
- `data: object (JSON.parse)`
- `createdAt: Date`
- `updatedAt: Date`

---
