import { describe, expect, it } from "vitest";
import { buildVerificationUrl, verificationEmailHtml } from "../email/resend";
import { verificationEmailHtml as brandedHtml } from "../email/template";

describe("email verification helpers", () => {
  it("builds a verify URL with email and token params", () => {
    const url = buildVerificationUrl("http://localhost:3000", "Nora@Farm.com", "abc123");
    expect(url.startsWith("http://localhost:3000/verify-email?")).toBe(true);
    expect(url).toContain(`email=${encodeURIComponent("Nora@Farm.com")}`);
    expect(url).toContain("token=abc123");
  });

  it("escapes the name in the HTML body", () => {
    const html = verificationEmailHtml('<b>"x"&', "http://x/verify-email?token=t");
    expect(html).toContain("&lt;b&gt;&quot;x&quot;&amp;");
    expect(html).toContain("http://x/verify-email?token=t");
    expect(html).not.toContain('<b>"x"');
  });

  it("includes the company logo and brand header", () => {
    const html = brandedHtml({ name: "Nora", verifyUrl: "https://farm.example/verify-email?token=t", logoUrl: "https://farm.example/logo12.png" });
    expect(html).toContain('src="https://farm.example/logo12.png"');
    expect(html).toContain('alt="Milking Monitor"');
    expect(html).toContain("Milking Monitor");
  });
});
