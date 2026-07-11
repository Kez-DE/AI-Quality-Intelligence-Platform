import '@testing-library/jest-dom';

const localStorageMock = (function () {
  let store: Record<string, string> = {};
  return {
    getItem(key: string) {
      return store[key] || null;
    },
    setItem(key: string, value: string) {
      store[key] = value.toString();
    },
    clear() {
      store = {};
    },
    removeItem(key: string) {
      delete store[key];
    }
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

import { vi } from 'vitest';

// Global Supabase mock: component tests must never require cloud env vars
// (VITE_SUPABASE_URL/KEY) or open real connections. Chainable stub covers
// the query builder, realtime channels, and auth used in effects.
vi.mock('@/integrations/supabase/client', () => {
  const queryResult = Promise.resolve({ data: [], error: null, count: 0 });
  const builder: Record<string, unknown> = {};
  const chain = () => builder;
  for (const m of ['select', 'insert', 'update', 'upsert', 'delete', 'eq', 'neq', 'in', 'gte', 'lte', 'gt', 'lt', 'or', 'not', 'is', 'order', 'limit', 'range', 'ilike', 'contains']) {
    builder[m] = vi.fn(chain);
  }
  builder.single = vi.fn(() => Promise.resolve({ data: null, error: null }));
  builder.maybeSingle = vi.fn(() => Promise.resolve({ data: null, error: null }));
  builder.then = queryResult.then.bind(queryResult);
  const channel = {
    on: vi.fn(() => channel),
    subscribe: vi.fn(() => channel),
    unsubscribe: vi.fn(),
  };
  return {
    supabase: {
      from: vi.fn(() => builder),
      channel: vi.fn(() => channel),
      removeChannel: vi.fn(),
      rpc: vi.fn(() => Promise.resolve({ data: null, error: null })),
      functions: { invoke: vi.fn(() => Promise.resolve({ data: null, error: null })) },
      auth: {
        getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
        getUser: vi.fn(() => Promise.resolve({ data: { user: null }, error: null })),
        onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
        signOut: vi.fn(() => Promise.resolve({ error: null })),
      },
    },
  };
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
