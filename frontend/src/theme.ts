import { useSyncExternalStore } from 'react'

export const THEME_STORAGE_KEY = 'variance.studio.theme'
export type StudioTheme = 'brown' | 'purple' | 'charcoal'
const themeColors: Record<StudioTheme, string> = { brown: '#130f0c', purple: '#090611', charcoal: '#101214' }
const listeners = new Set<() => void>()
let activeTheme: StudioTheme = 'brown'
let saved = true
let initialized = false

function validTheme(value: string | null): StudioTheme {
  return value === 'purple' || value === 'charcoal' ? value : 'brown'
}

function applyTheme(theme: StudioTheme) {
  activeTheme = theme
  document.documentElement.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themeColors[theme])
}

function notify() { listeners.forEach(listener => listener()) }

export function initializeTheme() {
  if (initialized) return
  initialized = true
  try { applyTheme(validTheme(localStorage.getItem(THEME_STORAGE_KEY))) }
  catch { saved = false; applyTheme('brown') }
  window.addEventListener('storage', event => {
    if (event.key !== THEME_STORAGE_KEY && event.key !== null) return
    try { if (event.storageArea !== localStorage) return }
    catch { return }
    applyTheme(validTheme(event.newValue))
    saved = true
    notify()
  })
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function setStudioTheme(theme: StudioTheme) {
  applyTheme(theme)
  try { localStorage.setItem(THEME_STORAGE_KEY, theme); saved = true }
  catch { saved = false }
  notify()
}

export function useStudioTheme() {
  const theme = useSyncExternalStore(subscribe, () => activeTheme)
  const persisted = useSyncExternalStore(subscribe, () => saved)
  return { theme, persisted, setTheme: setStudioTheme }
}
