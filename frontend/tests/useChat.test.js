/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';

// Directly set localStorage before importing api.js
const mockStorage = Object.create(null);
globalThis.localStorage = {
  getItem: (k) => mockStorage[k] ?? null,
  setItem: (k, v) => { mockStorage[k] = String(v); },
  removeItem: (k) => { delete mockStorage[k]; },
  clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
  get length() { return Object.keys(mockStorage).length; },
  key: (i) => Object.keys(mockStorage)[i] ?? null,
};

describe('api.js - thread id management', () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach(k => delete mockStorage[k]);
  });

  it('should have thread id functions', async () => {
    const api = await import('../src/services/api');
    expect(typeof api.getThreadId).toBe('function');
    expect(typeof api.setThreadId).toBe('function');
    expect(typeof api.newThreadId).toBe('function');
  });

  it('should generate valid UUIDs', async () => {
    const { generateUUID } = await import('../src/services/api');
    const id = generateUUID();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(10);
  });

  it('should manage thread id lifecycle', async () => {
    const { getThreadId, setThreadId, newThreadId } = await import('../src/services/api');
    
    const id1 = getThreadId();
    expect(id1).toBeTruthy();
    
    setThreadId('test-id-123');
    expect(getThreadId()).toBe('test-id-123');
    
    const newId = newThreadId();
    expect(newId).toBeTruthy();
    expect(newId).not.toBe('test-id-123');
  });
});
