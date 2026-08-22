import { describe, it, expect } from "vitest";
import { renderMarkdown } from "../src/utils/markdown";

describe("utils/markdown", () => {
  it("strips script tags from inline HTML (XSS 防护)", () => {
    const out = renderMarkdown(
      "hello <script>alert(1)</script><img src=x onerror=alert(1)> world",
    );
    expect(out).not.toContain("<script>");
    expect(out).not.toContain("onerror");
    expect(out).toContain("hello");
  });

  it("renders inline katex math with katex class", () => {
    const out = renderMarkdown("$E=mc^2$");
    expect(out).toContain("katex");
  });

  it("keeps heading ids for TOC scrollspy", () => {
    const out = renderMarkdown("## 核心结论与投资摘要");
    expect(out).toMatch(/<h2 id="[^"]*">/);
  });
});
