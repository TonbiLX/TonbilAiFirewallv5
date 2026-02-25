# Coding Conventions

**Analysis Date:** 2026-02-25

## Naming Patterns

**Files:**
- Components: PascalCase (e.g., `DashboardPage.tsx`, `GlassCard.tsx`)
- Services: camelCase with suffix (e.g., `deviceApi.ts`, `dashboardApi.ts`)
- Hooks: camelCase starting with `use` (e.g., `useDashboard.ts`, `useWebSocket.ts`)
- Types/Interfaces: TypeScript files in `src/types/` directory (e.g., `index.ts`, `dashboard-grid.ts`)
- Config files: camelCase (e.g., `widgetRegistry.tsx`)

**Functions:**
- Async functions: No special prefix, but marked `async` keyword (e.g., `fetchDashboardSummary()`, `handleLogin()`)
- Event handlers: camelCase with `handle` or `on` prefix (e.g., `handleSort()`, `onLayoutChange()`)
- Helper functions: camelCase, lowercase start (e.g., `formatBps()`, `getDeviceIcon()`)
- Boolean getters: `is`, `has` prefix (e.g., `isOnline`, `hasQr`)

**Variables:**
- React state: camelCase (e.g., `sortCol`, `sortDir`, `wsData`)
- Constants: UPPER_SNAKE_CASE (e.g., `STORAGE_KEY`, `SCHEMA_VERSION`, `TOKEN_EXPIRE_HOURS`)
- Refs: camelCase with `Ref` suffix (e.g., `wsRef`, `reconnectTimeoutRef`)
- Types from API: snake_case (matching backend) (e.g., `is_online`, `total_queries_24h`, `block_percentage`)

**Types:**
- Interface names: PascalCase (e.g., `GlassCardProps`, `Device`, `DashboardSummary`)
- Union type discriminators: lowercase (e.g., `type PageMode = "loading" | "login" | "setup"`)
- Enum values: match backend naming in snake_case (e.g., `ProfileType.child`, `FirewallAction.accept`)

## Code Style

**Formatting:**
- No explicit formatter configured (ESLint/Prettier not found in root)
- TypeScript: enabled with `strict: false` (allows flexible typing where needed)
- Line width: inferred ~100 characters from existing code
- Indentation: 2 spaces

**Linting:**
- Not detected: No `.eslintrc`, `eslint.config.js`, or linting in package.json
- Type checking: TypeScript compiler with relaxed settings
  - `noUnusedLocals: false` - unused variables allowed
  - `noUnusedParameters: false` - unused parameters allowed
  - `strict: false` - type checking relaxed

**Comments:**
- Turkish language in code comments and documentation
- Agent names in file headers: e.g., `// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---`
- Purpose statement after agent name (single line)
- No JSDoc/TSDoc pattern observed

## Import Organization

**Order:**
1. React and standard library imports
2. External packages (axios, lucide-react, react-grid-layout, recharts)
3. Internal components (relative imports from `./components/...`)
4. Internal hooks (relative imports from `../hooks/...`)
5. Internal services (relative imports from `../services/...`)
6. Type imports

**Path Aliases:**
- Not used; relative paths throughout
- Example: `import { GlassCard } from "../components/common/GlassCard"`
- Pattern: `../` for moving up directories

**Imports with type keyword:**
```typescript
import type { LayoutItem, ResponsiveLayouts } from "react-grid-layout";
import type { DashboardPreferences } from "../types/dashboard-grid";
```

## Error Handling

**Patterns:**

**Frontend:**
- try-catch in async functions
- Error state in component state: `const [error, setError] = useState("")`
- Display user-friendly error messages in UI
- Axios error handling on response status codes:
  ```typescript
  catch (err: any) {
    if (err.response?.status === 401) {
      // Handle 401
    } else if (err.response?.data?.detail) {
      setError(err.response.data.detail);
    } else if (err.code === "ERR_NETWORK") {
      setError("Sunucuya bağlanılamıyor...");
    }
  }
  ```
- 401 responses trigger global redirect to `/login` via axios interceptor in `api.ts`
- WebSocket errors caught and logged: `console.error("WebSocket parse hatasi:", e)`
- Silent failures in hooks (no UI error shown): `catch (err) { console.error(...) }`

**Backend:**
- FastAPI HTTPException for API errors
- Logging module configured per endpoint: `logger = logging.getLogger("tonbilai.auth")`
- Graceful degradation (e.g., in-memory fallback when Redis unavailable)
- Rate limiting returns `429` with detail message

## Logging

**Framework:** Python standard `logging` module

**Patterns:**
- Per-module loggers: `logger = logging.getLogger("tonbilai.{module}")`
- Frontend: console logging only (`console.error()`, `console.log()`)
- No structured logging framework detected
- Example backend usage:
  ```python
  logger = logging.getLogger("tonbilai.auth")
  logger.info("User login successful")
  ```

**When to log:**
- Backend: Authentication events, errors, rate limiting triggers
- Frontend: Console errors for debugging only

## Function Design

**Size:**
- Components: 20-150 lines (split between logic and render)
- Hooks: 10-40 lines (data loading, state management)
- Utility functions: <30 lines

**Parameters:**
- Max 5-7 parameters; use object destructuring for more
- React components: single props object destructured
  ```typescript
  export function GlassCard({
    children,
    className,
    hoverable = false,
    neonColor,
  }: GlassCardProps) { }
  ```
- API functions: no destructuring, single parameters
  ```typescript
  export const setDeviceBandwidthLimit = (id: number, limit_mbps: number | null) =>
  ```

**Return Values:**
- Components: JSX.Element (implicit)
- Hooks: Object with named properties (e.g., `{ data, connected }`, `{ summary, loading }`)
- API functions: Promise<AxiosResponse> (axios client)
- Async backend: return SQLAlchemy objects or Pydantic schemas

## Module Design

**Exports:**
- Named exports preferred: `export function useWebSocket() {}`
- Default export used for page components: `export default function App() {}`
- Type exports: `import type { ... }`

**Barrel Files:**
- Not used in frontend
- Backend: `__init__.py` exports all models:
  ```python
  from app.models.profile import Profile
  __all__ = ["Profile", ...]
  ```

## Component Structure

**Functional Components:**
- Hooks-based (no class components)
- Props interface defined above component
- Destructure props in function signature

**Example pattern:**
```typescript
interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hoverable?: boolean;
  neonColor?: "cyan" | "magenta" | "green" | "amber" | "red";
}

export function GlassCard({
  children,
  className,
  hoverable = false,
  neonColor,
}: GlassCardProps) {
  return <div className={clsx(...)}>...</div>;
}
```

## Conditional Rendering

**Pattern:**
- clsx for conditional classes (not className-merge or other libraries)
```typescript
className={clsx(
  hoverable ? "glass-card-hover" : "glass-card",
  neonColor === "cyan" && "border-neon-cyan/30",
  className
)}
```
- Ternary for JSX: `{condition ? <X /> : <Y />}`
- Logical AND for optional rendering: `{isVisible && <Component />}`

## Constants & Magic Numbers

**Location:**
- Component-level constants: inside component or above
- Shared constants: top of file
- Hook constants: top of file

**Examples:**
```typescript
// In hook
const STORAGE_KEY = "tonbilaios_dashboard_prefs";
const SCHEMA_VERSION = 1;

// In component
const SCAN_COOLDOWN = 30; // seconds
const MAX_LOGIN_ATTEMPTS = 5;
```

## State Management

**No global state management:**
- React Context not used
- Each component/hook manages own state
- Shared data via WebSocket (`useWebSocket` hook)
- API calls in individual hooks

**Pattern:**
```typescript
const [data, setData] = useState<Type | null>(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const load = async () => {
    try {
      const data = await fetchData();
      setData(data);
    } catch (err) {
      console.error("error:", err);
    } finally {
      setLoading(false);
    }
  };
  load();
}, []);
```

## API Integration

**Axios configured in `api.ts`:**
- Base URL: `/api/v1` (Vite proxy handles routing)
- JWT token: Authorization header via request interceptor
- 401 handling: global redirect to `/login`

**Service functions pattern:**
```typescript
export const fetchDevices = (params?: DeviceListParams) =>
  api.get('/devices/', { params });
```

---

*Convention analysis: 2026-02-25*
