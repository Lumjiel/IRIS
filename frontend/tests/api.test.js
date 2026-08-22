/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("api.js - streamChat", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("should call fetch with correct URL", async () => {
    const { streamChat } = await import("../src/services/api");

    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type": "done"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: undefined }),
      cancel: vi.fn(),
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: { getReader: () => mockReader },
    });

    const onData = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await streamChat(
      "test",
      "hybrid",
      onData,
      onDone,
      onError,
      new AbortController().signal,
    );

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(onDone).toHaveBeenCalled();
  });

  it("should handle fetch error", async () => {
    const { streamChat } = await import("../src/services/api");

    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const onError = vi.fn();

    await streamChat(
      "test",
      "hybrid",
      vi.fn(),
      vi.fn(),
      onError,
      new AbortController().signal,
    );

    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("should parse multiple SSE events correctly", async () => {
    const { streamChat } = await import("../src/services/api");

    const chunks = [
      'data: {"step": "intent", "data": {"intent": "research"}}\n\n',
      'data: {"step": "planner", "status": "running"}\n\n',
      'data: {"data": {"token": "研"}}\n\n',
      'data: {"data": {"token": "报"}}\n\n',
      'data: {"type": "done", "data": {}}\n\n',
    ];

    const mockReader = {
      read: vi.fn(),
      cancel: vi.fn(),
    };

    let callIndex = 0;
    mockReader.read.mockImplementation(() => {
      if (callIndex < chunks.length) {
        return Promise.resolve({
          done: false,
          value: new TextEncoder().encode(chunks[callIndex++]),
        });
      }
      return Promise.resolve({ done: true, value: undefined });
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: { getReader: () => mockReader },
    });

    const events = [];
    const onData = (data) => events.push(data);

    await streamChat(
      "分析贵州茅台",
      "hybrid",
      onData,
      vi.fn(),
      vi.fn(),
      new AbortController().signal,
    );

    expect(events.length).toBeGreaterThanOrEqual(4);
    expect(events[0].step).toBe("intent");
    expect(events[events.length - 1].type).toBe("done");
  });

  it("should handle HTTP error status", async () => {
    const { streamChat } = await import("../src/services/api");

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const onError = vi.fn();

    await streamChat(
      "test",
      "hybrid",
      vi.fn(),
      vi.fn(),
      onError,
      new AbortController().signal,
    );

    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });
});
