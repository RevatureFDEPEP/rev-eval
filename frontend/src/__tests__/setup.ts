import '@testing-library/jest-dom'

// Node 22+ ships an experimental `localStorage` global that shadows jsdom's
// and is undefined unless Node is started with --localstorage-file. Install a
// deterministic in-memory implementation so tests behave the same on every
// Node version (CI runs Node 20, local machines may run newer).
const store = new Map<string, string>()
const memoryLocalStorage: Storage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => {
    store.set(key, String(value))
  },
  removeItem: (key: string) => {
    store.delete(key)
  },
  clear: () => {
    store.clear()
  },
  key: (index: number) => [...store.keys()][index] ?? null,
  get length() {
    return store.size
  },
}

Object.defineProperty(globalThis, 'localStorage', {
  value: memoryLocalStorage,
  configurable: true,
  writable: true,
})
