import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import QualityCockpit from '../components/QualityCockpit'
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

  it('renders QualityCockpit without crashing', () => {
    render(<QualityCockpit />)
    expect(screen.getAllByText(/AI Quality Intelligence/i).length).toBeGreaterThan(0)
  })
})
