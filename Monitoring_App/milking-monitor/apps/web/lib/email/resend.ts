import { Resend } from "resend";
import { verificationEmailHtml as brandedVerificationEmailHtml, verificationEmailText } from "./template";

let client: Resend | null = null;

function getClient(): Resend | null {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) return null;
  if (!client) client = new Resend(apiKey);
  return client;
}

function fromAddress(): string {
  const email = process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev";
  const name = process.env.RESEND_FROM_NAME || "Milking Monitor";
  return `${name} <${email}>`;
}

export function buildVerificationUrl(origin: string, email: string, token: string): string {
  const url = new URL("/verify-email", origin);
  url.searchParams.set("email", email);
  url.searchParams.set("token", token);
  return url.toString();
}

export function verificationEmailHtml(name: string, verifyUrl: string): string {
  let logo = "/logo12.png";
  try {
    logo = `${new URL(verifyUrl).origin}/logo12.png`;
  } catch {
    // keep relative fallback
  }
  return brandedVerificationEmailHtml({ name, verifyUrl, logoUrl: logo });
}

export async function sendVerificationEmail(input: {
  to: string;
  name: string;
  verifyUrl: string;
}): Promise<{ sent: boolean; error?: string }> {
  const resend = getClient();
  if (!resend) {
    console.error("[email] RESEND_API_KEY is not set — verification email not sent");
    return { sent: false, error: "Email service is not configured" };
  }

  try {
    const { error } = await resend.emails.send({
      from: fromAddress(),
      to: input.to,
      subject: "Verify your Milking Monitor account",
      text: verificationEmailText({ name: input.name, verifyUrl: input.verifyUrl }),
      html: verificationEmailHtml(input.name, input.verifyUrl),
    });
    if (error) {
      console.error("[email] Resend send failed", error);
      return { sent: false, error: error.message };
    }
    return { sent: true };
  } catch (err) {
    console.error("[email] Resend send threw", err);
    return { sent: false, error: err instanceof Error ? err.message : "Unknown email error" };
  }
}
