import { render, RenderOptions } from '@testing-library/react'
import { ReactElement } from 'react'

// Mock store provider for testing
const MockStoreProvider = ({ children }: { children: React.ReactNode }) => {
  return <div data-testid="mock-store-provider">{children}</div>
}

// Custom render function with providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  return render(ui, {
    wrapper: MockStoreProvider,
    ...options,
  })
}

// Re-export everything
export * from '@testing-library/react'
export { customRender as render }

// Mock data factories
export const createMockMeeting = (overrides = {}) => ({
  id: '1',
  title: 'Test Meeting',
  date: '2024-01-01',
  duration: 3600,
  status: 'completed' as const,
  participants: ['user1'],
  audioUrl: 'test-audio.mp3',
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
})

export const createMockNote = (overrides = {}) => ({
  id: '1',
  meetingId: 'meeting1',
  content: 'Test note content',
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
})

export const createMockTemplate = (overrides = {}) => ({
  id: '1',
  name: 'Test Template',
  description: 'Test template description',
  sections: [
    { id: '1', title: 'Section 1', type: 'text' as const, content: 'Content 1' }
  ],
  isDefault: false,
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
})

export const createMockConversation = (overrides = {}) => ({
  id: '1',
  meetingId: 'meeting1',
  messages: [],
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
})

// Helper functions for async testing
export const waitForLoadingToFinish = () => 
  new Promise(resolve => setTimeout(resolve, 0))

// Mock performance observer
export const mockPerformanceObserver = () => {
  global.PerformanceObserver = jest.fn().mockImplementation((callback) => ({
    observe: jest.fn(),
    disconnect: jest.fn(),
  })) as any
}

// Mock intersection observer
export const mockIntersectionObserver = () => {
  global.IntersectionObserver = jest.fn().mockImplementation((callback) => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
  })) as any
}