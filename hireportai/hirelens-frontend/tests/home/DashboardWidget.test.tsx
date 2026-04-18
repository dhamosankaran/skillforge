import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { DashboardWidget } from '@/components/home/DashboardWidget'

function renderWidget(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('DashboardWidget', () => {
  it('renders a skeleton in the loading state', () => {
    const { container } = renderWidget(
      <DashboardWidget
        title="X"
        testid="x"
        persona="career_climber"
        state="loading"
      />,
    )
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders children + title in the data state', () => {
    renderWidget(
      <DashboardWidget
        title="My Title"
        testid="x"
        persona="career_climber"
        state="data"
      >
        <span>Body content</span>
      </DashboardWidget>,
    )
    expect(screen.getByTestId('widget-x')).toBeInTheDocument()
    expect(screen.getByText('My Title')).toBeInTheDocument()
    expect(screen.getByText('Body content')).toBeInTheDocument()
  })

  it('renders emptyMessage in the empty state', () => {
    renderWidget(
      <DashboardWidget
        title="X"
        testid="x"
        persona="career_climber"
        state="empty"
        emptyMessage="Nothing yet"
      />,
    )
    expect(screen.getByText('Nothing yet')).toBeInTheDocument()
  })

  it('renders errorMessage + "Try again" and calls onRetry when clicked', async () => {
    const onRetry = vi.fn()
    const user = userEvent.setup()
    renderWidget(
      <DashboardWidget
        title="X"
        testid="x"
        persona="career_climber"
        state="error"
        errorMessage="Oops"
        onRetry={onRetry}
      />,
    )
    expect(screen.getByText('Oops')).toBeInTheDocument()
    const btn = screen.getByRole('button', { name: /try again/i })
    await user.click(btn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders action with href as a Link', () => {
    renderWidget(
      <DashboardWidget
        title="X"
        testid="x"
        persona="career_climber"
        state="data"
        action={{ label: 'Go', href: '/learn/daily' }}
      >
        <span>body</span>
      </DashboardWidget>,
    )
    const link = screen.getByRole('link', { name: 'Go' })
    expect(link).toHaveAttribute('href', '/learn/daily')
  })

  it('renders action with onClick as a button; clicking calls it', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()
    renderWidget(
      <DashboardWidget
        title="X"
        testid="x"
        persona="career_climber"
        state="data"
        action={{ label: 'Do', onClick }}
      >
        <span>body</span>
      </DashboardWidget>,
    )
    await user.click(screen.getByRole('button', { name: 'Do' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
