import { describe, it, expect } from "vitest";
import { sanitizeInput } from "../security/sanitize";

describe("sanitizeInput", () => {
  it("trims whitespace", () => {
    expect(sanitizeInput("  hello  ")).toBe("hello");
  });

  it("escapes HTML ampersand", () => {
    expect(sanitizeInput("a&b")).toBe("a&amp;b");
  });

  it("escapes HTML less-than", () => {
    expect(sanitizeInput("a<b")).toBe("a&lt;b");
  });

  it("escapes HTML greater-than", () => {
    expect(sanitizeInput("a>b")).toBe("a&gt;b");
  });

  it("escapes double quotes", () => {
    expect(sanitizeInput('a"b')).toBe("a&quot;b");
  });

  it("escapes single quotes", () => {
    expect(sanitizeInput("a'b")).toBe("a&#x27;b");
  });

  it("escapes multiple special characters", () => {
    expect(sanitizeInput('<script>alert("xss")</script>')).toBe(
      "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
    );
  });

  it("returns empty string for empty input", () => {
    expect(sanitizeInput("")).toBe("");
  });

  it("handles normal text without changes", () => {
    expect(sanitizeInput("Hello World 123")).toBe("Hello World 123");
  });
});
