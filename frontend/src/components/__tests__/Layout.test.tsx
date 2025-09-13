import { render, screen } from '@testing-library/react'
import { Layout } from '../layout/Layout'

// Mock the store
jest.mock('../../lib/store', () => ({
  useAppStore: () => ({
    theme: 'light',
    sidebarOpen: true,
    setTheme: jest.fn(),
    meetings: [],
  }),
}))

// Mock services
jest.mock('../../lib/settings-service', () => ({
  settingsService: {
    getSettings: jest.fn(() => ({})),
  },
}))

jest.mock('../../lib/storage', () => ({
  storageManager: {
    initializeDefaultTemplates: jest.fn(() => Promise.resolve()),
  },
}))

jest.mock('../../lib/pwa-service', () => ({
  pwaService: {
    initialize: jest.fn(() => Promise.resolve()),
  },
}))

jest.mock('../../lib/performance-service', () => ({
  performanceService: {
    initialize: jest.fn(() => Promise.resolve()),
    enableLazyLoading: jest.fn(),
    preloadCriticalResources: jest.fn(),
  },
}))

// Mock components that might have complex dependencies
jest.mock('../offline/OfflineIndicator', () => ({
  OfflineIndicator: () => <div data-testid="offline-indicator">Offline Indicator</div>,
}))

jest.mock('../pwa/InstallPrompt', () => ({
  InstallPrompt: () => <div data-testid="install-prompt">Install Prompt</div>,
}))

describe('Layout Component', () => {
  it('renders children correctly', () => {
    render(
      <Layout>
        <div data-testid="test-child">Test Content</div>
      </Layout>
    )

    expect(screen.getByTestId('test-child')).toBeInTheDocument()
  })

  it('renders offline indicator', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    )

    expect(screen.getByTestId('offline-indicator')).toBeInTheDocument()
  })

  it('renders install prompt', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    )

    expect(screen.getByTestId('install-prompt')).toBeInTheDocument()
  })
})