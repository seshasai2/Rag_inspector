'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

export type ThemeMode = 'dark' | 'light'

type ThemeContextValue = {
  theme: ThemeMode
  setTheme: (mode: ThemeMode) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)
const STORAGE_KEY = 'raginspector-theme'

function applyThemeClass(mode: ThemeMode) {
  const root = document.documentElement
  root.classList.remove('dark', 'light')
  root.classList.add(mode)
  root.style.colorScheme = mode
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('dark')
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as ThemeMode | null
    const initial: ThemeMode = stored === 'light' || stored === 'dark' ? stored : 'dark'
    applyThemeClass(initial)
    setThemeState(initial)
    setReady(true)
  }, [])

  const setTheme = useCallback((mode: ThemeMode) => {
    applyThemeClass(mode)
    window.localStorage.setItem(STORAGE_KEY, mode)
    setThemeState(mode)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }, [setTheme, theme])

  // Avoid flashing wrong theme before hydration read.
  if (!ready) {
    return <ThemeContext.Provider value={{ theme: 'dark', setTheme, toggleTheme }}>{children}</ThemeContext.Provider>
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
