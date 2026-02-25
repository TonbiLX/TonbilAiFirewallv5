# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Status:** Not detected

- No test runner configured (Jest, Vitest not in `package.json`)
- No test files found in codebase (`*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`)
- No test config files (`jest.config.ts`, `vitest.config.ts`)
- No assertion library in dependencies

**Run Commands:**
- Not applicable; no test infrastructure present

## Test File Organization

**Current state:**
- No test files in repository
- Source structure is test-ready (services, hooks, components separated)

**Recommended structure for future testing:**
```
frontend/src/
├── __tests__/
│   ├── services/
│   │   ├── api.test.ts
│   │   └── deviceApi.test.ts
│   ├── hooks/
│   │   ├── useDashboard.test.ts
│   │   └── useWebSocket.test.ts
│   └── components/
│       ├── common/
│       │   └── GlassCard.test.tsx
│       └── dashboard/
│           └── DashboardGrid.test.tsx
```

Or co-located pattern:
```
frontend/src/
├── services/
│   ├── api.ts
│   └── api.test.ts
├── hooks/
│   ├── useWebSocket.ts
│   └── useWebSocket.test.ts
```

## Test Structure

**Current testing approach: Manual/Integration testing only**

Based on existing code patterns, tests should follow these conventions:

**For hooks:**
```typescript
// Pattern inferred from hook structure
describe('useWebSocket', () => {
  it('should connect to WebSocket on mount', () => {
    // Arrange: mock WebSocket
    // Act: render hook
    // Assert: connection established
  });

  it('should auto-reconnect after disconnect', () => {
    // Verify setTimeout called with 3000ms
  });

  it('should parse incoming data correctly', () => {
    // Send test JSON message
    // Assert state updated
  });
});
```

**For API services:**
```typescript
describe('deviceApi', () => {
  it('should call GET /devices/ with params', () => {
    const params = { sort_by: 'hostname' };
    await fetchDevices(params);
    // Assert api.get called with correct URL and params
  });

  it('should construct correct device update endpoint', () => {
    await updateDevice(5, { hostname: 'test' });
    // Assert api.patch(`/devices/5`, data)
  });
});
```

**For components:**
```typescript
describe('GlassCard', () => {
  it('should render children', () => {
    const { getByText } = render(
      <GlassCard>Test Content</GlassCard>
    );
    expect(getByText('Test Content')).toBeInTheDocument();
  });

  it('should apply neonColor className', () => {
    const { container } = render(
      <GlassCard neonColor="cyan">Content</GlassCard>
    );
    expect(container.querySelector('.border-neon-cyan\\/30')).toBeInTheDocument();
  });

  it('should apply hoverable class when prop true', () => {
    const { container } = render(
      <GlassCard hoverable>Content</GlassCard>
    );
    expect(container.querySelector('.glass-card-hover')).toBeInTheDocument();
  });
});
```

## Mocking

**Framework:** None implemented

**Recommended patterns for future tests:**

**Axios mocking:**
```typescript
import axios from 'axios';
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

beforeEach(() => {
  mockedAxios.get.mockResolvedValue({ data: mockData });
});

afterEach(() => {
  jest.clearAllMocks();
});
```

**WebSocket mocking:**
```typescript
// Global WebSocket mock
global.WebSocket = jest.fn();
const mockWebSocket = {
  onopen: jest.fn(),
  onmessage: jest.fn(),
  onclose: jest.fn(),
  onerror: jest.fn(),
  close: jest.fn(),
  send: jest.fn(),
};
(global.WebSocket as jest.Mock).mockReturnValue(mockWebSocket);
```

**localStorage mocking:**
```typescript
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
global.localStorage = localStorageMock as any;
```

**What to Mock:**
- External API calls (axios requests)
- WebSocket connections
- Browser APIs (localStorage, window.location)
- Timers (setTimeout, setInterval)
- React Router hooks (useNavigate)

**What NOT to Mock:**
- Internal utility functions
- Component rendering
- React hooks behavior (unless necessary for isolation)
- localStorage for integration tests

## Fixtures and Factories

**Test data:**
Not implemented. Recommended pattern based on types:

```typescript
// fixtures/deviceFixtures.ts
import type { Device } from '@/types';

export const createMockDevice = (overrides?: Partial<Device>): Device => ({
  id: 1,
  mac_address: '00:11:22:33:44:55',
  ip_address: '192.168.1.100',
  hostname: 'test-device',
  manufacturer: 'Apple',
  profile_id: null,
  is_blocked: false,
  is_online: true,
  first_seen: new Date().toISOString(),
  last_seen: new Date().toISOString(),
  total_online_seconds: 3600,
  last_online_start: new Date().toISOString(),
  detected_os: 'iOS',
  device_type: 'phone',
  bandwidth_limit_mbps: null,
  risk_score: 0,
  risk_level: 'safe',
  last_risk_assessment: null,
  ...overrides,
});

export const createMockDashboardSummary = (): DashboardSummary => ({
  devices: { total: 10, online: 8, blocked: 0 },
  dns: {
    total_queries_24h: 50000,
    blocked_queries_24h: 500,
    block_percentage: 1.0,
    active_blocklists: 5,
    total_blocked_domains: 100000,
  },
  top_clients: [],
  top_queried_domains: [],
  top_blocked_domains: [],
});
```

**Location:**
- `frontend/src/__tests__/fixtures/`
- Separate file per domain (deviceFixtures, dnsFixtures, etc.)

## Coverage

**Requirements:** Not enforced

**View Coverage:** Not implemented

**Recommended setup:**
```bash
npm test -- --coverage
```

**Coverage goals (recommended):**
- Services: 80%+ (critical API interaction)
- Hooks: 75%+ (state management)
- Components: 60%+ (UI testing harder, lower bar acceptable)
- Utilities: 90%+

## Test Types

**Unit Tests:**
- Scope: Individual functions, hooks, small components
- Approach: Mock external dependencies, test pure logic
- Examples:
  - `useDashboardLayout()` localStorage persistence
  - `formatBps()` number formatting
  - `GlassCard` className logic

**Integration Tests:**
- Scope: Hook + component interaction, API + state flow
- Approach: Minimal mocking, test real interactions
- Examples:
  - `useDashboard()` hook fetching and rendering
  - DevicesPage listing, sorting, filtering
  - Login form submission and redirect flow

**E2E Tests:**
- Framework: Not used
- Recommendation: Playwright or Cypress for critical flows
- Scope: Login, dashboard load, device management operations

## Common Patterns

**Async Testing:**
```typescript
// Pattern for async hooks (jest/vitest)
import { renderHook, waitFor } from '@testing-library/react';

it('should load data on mount', async () => {
  const { result } = renderHook(() => useDashboard());

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.summary).toBeDefined();
});
```

**Error Testing:**
```typescript
it('should handle API errors gracefully', async () => {
  mockedAxios.get.mockRejectedValue(new Error('Network error'));

  const { result } = renderHook(() => useDashboard());

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.summary).toBeNull();
});
```

**State transitions:**
```typescript
it('should transition through loading states', async () => {
  const { result, rerender } = renderHook(() => useState(false));

  expect(result.current[0]).toBe(false);

  act(() => {
    result.current[1](true);
  });

  expect(result.current[0]).toBe(true);
});
```

## Backend Testing

**Python testing:** No test infrastructure detected

**Recommended setup:**
```python
# backend/tests/
├── conftest.py           # Pytest fixtures
├── test_auth.py          # Auth endpoint tests
├── test_devices.py       # Device CRUD tests
├── test_dns.py           # DNS filtering tests
└── integration/
    └── test_end_to_end.py
```

**Backend test patterns:**
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_list_devices_requires_auth(client):
    response = client.get('/api/v1/devices/')
    assert response.status_code == 401

@pytest.fixture
def auth_token():
    # Fixture to create valid JWT token
    return create_test_token(user_id=1)

def test_list_devices_authenticated(client, auth_token):
    response = client.get(
        '/api/v1/devices/',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Async SQLAlchemy testing:**
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()
```

---

*Testing analysis: 2026-02-25*
