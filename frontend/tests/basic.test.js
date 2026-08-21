/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';

describe('IRIS Frontend - Basic functionality', () => {
  it('should have fetch available', () => {
    expect(typeof fetch).toBe('function');
  });

  it('should parse SSE data format correctly', () => {
    const sseLine = 'data: {"type": "writer", "data": {"token": "Hello"}}\n\n';
    
    const jsonStr = sseLine.replace(/^data: /, '').trim();
    const parsed = JSON.parse(jsonStr);
    
    expect(parsed.type).toBe('writer');
    expect(parsed.data.token).toBe('Hello');
  });

  it('should accumulate streaming tokens', () => {
    const tokens = ['Hello', ' ', 'World'];
    let accumulated = '';
    
    for (const token of tokens) {
      accumulated += token;
    }
    
    expect(accumulated).toBe('Hello World');
  });

  it('should detect done event', () => {
    const sseLine = 'data: {"type": "done", "data": {}}\n\n';
    const jsonStr = sseLine.replace(/^data: /, '').trim();
    const parsed = JSON.parse(jsonStr);
    
    expect(parsed.type).toBe('done');
  });

  it('should parse multiple SSE events', () => {
    const events = [
      { type: 'planner', data: { status: 'planning' } },
      { type: 'researcher', data: { status: 'searching' } },
      { type: 'writer', data: { token: 'Hello' } },
      { type: 'writer', data: { token: ' World' } },
      { type: 'reviewer', data: { status: 'reviewing' } },
      { type: 'done', data: {} },
    ];
    
    let report = '';
    for (const event of events) {
      if (event.type === 'writer') {
        report += event.data.token;
      }
    }
    
    expect(report).toBe('Hello World');
  });
});
