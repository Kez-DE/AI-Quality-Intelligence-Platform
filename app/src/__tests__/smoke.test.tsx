import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CockpitFilterProvider } from '../components/cockpit/CockpitFilterContext'
import { CockpitView } from '../components/cockpit/CockpitView'
import AppShell from '../components/AppShell'

// Mock react-router dependencies
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
  useRouter: () => ({
    navigate: vi.fn(),
    buildLocation: vi.fn(),
    matchRoutes: vi.fn(),
  }),
  useLocation: () => ({
    pathname: '/',
    search: '',
    hash: '',
  }),
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
  Outlet: () => <div>Outlet</div>,
  useRouterState: () => ({ location: { pathname: '/' } }),
}))

// Mock query
vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
  useMutation: () => ({
    mutate: vi.fn(),
    isLoading: false,
  }),
  useQueryClient: () => ({
    invalidateQueries: vi.fn(),
    setQueryData: vi.fn(),
    getQueryData: vi.fn(),
  }),
}))

describe('Smoke Tests', () => {
  it('renders AppShell without crashing', () => {
    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('renders the cockpit without crashing', () => {
    render(
      <CockpitFilterProvider>
        <CockpitView />
      </CockpitFilterProvider>
    )
    expect(screen.getAllByText(/Feedback hôm nay/i).length).toBeGreaterThan(0)
  })
})
