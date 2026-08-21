// api.test.js - 使用 bun:test 语法
import { describe, it, expect, beforeEach } from 'bun:test';
import { jest } from 'bun:test';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('api.js - streamChat', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should call fetch with correct URL', async () => {
    const { streamChat } = await import('../src/services/api');
    
    const mockReader = {
      read: jest.fn()
        .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"type": "done"}\n\n') })
        .mockResolvedValueOnce({ done: true, value: undefined }),
      cancel: jest.fn(),
    };
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: { getReader: () => mockReader },
    });
    
    const onData = jest.fn();
    const onDone = jest.fn();
    const onError = jest.fn();
    
    await streamChat('test', 'hybrid', onData, onDone, onError, new AbortController().signal);
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/chat/stream'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(onDone).toHaveBeenCalled();
  });

  it('should handle fetch error', async () => {
    const { streamChat } = await import('../src/services/api');
    
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    
    const onError = jest.fn();
    
    await streamChat('test', 'hybrid', jest.fn(), jest.fn(), onError, new AbortController().signal);
    
    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });
});
