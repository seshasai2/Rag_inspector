import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeProvider, useTheme } from '@/components/theme-provider'
import { ThemeToggle } from '@/components/theme-toggle'

function ThemeLabel() {
  const { theme } = useTheme()
  return <span data-testid="theme">{theme}</span>
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.className = ''
  })

  afterEach(() => {
    window.localStorage.clear()
  })

  it('defaults to dark and toggles to light', () => {
    render(
      <ThemeProvider>
        <ThemeLabel />
        <ThemeToggle />
      </ThemeProvider>,
    )
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    fireEvent.click(screen.getByRole('button', { name: /switch to light/i }))
    expect(screen.getByTestId('theme').textContent).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(window.localStorage.getItem('raginspector-theme')).toBe('light')
  })

  it('restores stored light theme', () => {
    window.localStorage.setItem('raginspector-theme', 'light')
    render(
      <ThemeProvider>
        <ThemeLabel />
      </ThemeProvider>,
    )
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })
})
