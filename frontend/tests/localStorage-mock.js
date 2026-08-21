// frontend/tests/localStorage-mock.js
// localStorage polyfill for test environments
const mockStorage = Object.create(null);

const localStorageMock = {
  get length() { return Object.keys(mockStorage).length; },
  key(i) { return Object.keys(mockStorage)[i] ?? null; },
  getItem(k) { return mockStorage[k] ?? null; },
  setItem(k, v) { mockStorage[k] = String(v); },
  removeItem(k) { delete mockStorage[k]; },
  clear() { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
};

// Set on global before any test
if (typeof globalThis !== 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
}

export default localStorageMock;
