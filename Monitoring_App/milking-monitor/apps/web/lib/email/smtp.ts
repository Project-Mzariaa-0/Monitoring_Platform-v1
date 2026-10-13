import nodemailer from "nodemailer";
import type { Transporter } from "nodemailer";
import { verificationEmailHtml, verificationEmailText } from "./template";

let transporter: Transporter | null = null;

function smtpConfig() {
  return {
    host: process.env.SMTP_HOST || "smtp.gmail.com",
    port: Number(process.env.SMTP_PORT || 587),
    secure: (process.env.SMTP_SECURE || "false").toLowerCase() === "true",
    user: process.env.SMTP_USER || "",
    pass: process.env.SMTP_PASS || "",
  };
}

export function isSmtpConfigured(): boolean {
  const { user, pass } = smtpConfig();
  return Boolean(user && pass);
}

function getTransporter(): Transporter | null {
  if (!isSmtpConfigured()) return null;
  if (!transporter) {
    const { host, port, secure, user, pass } = smtpConfig();
    transporter = nodemailer.createTransport({ host, port, secure, auth: { user, pass } });
  }
  return transporter;
}

function fromAddress(): string {
  const email =
    process.env.EMAIL_FROM || process.env.RESEND_FROM_EMAIL || process.env.SMTP_USER || "noreply@localhost";
  const name = process.env.EMAIL_FROM_NAME || process.env.RESEND_FROM_NAME || "Milking Monitor";
  return `${name} <${email}>`;
}

function logoUrlFor(verifyUrl: string): string {
  try {
    return `${new URL(verifyUrl).origin}/logo12.png`;
  } catch {
    return "/logo12.png";
  }
}

export async function sendSmtpVerificationEmail(input: {
  to: string;
  name: string;
  verifyUrl: string;
}): Promise<{ sent: boolean; error?: string }> {
  const tx = getTransporter();
  if (!tx) {
    console.error("[email] SMTP is not configured (set SMTP_USER + SMTP_PASS) — verification email not sent");
    return { sent: false, error: "Email service is not configured" };
  }

  try {
    await tx.sendMail({
      from: fromAddress(),
      to: input.to,
      subject: "Verify your Milking Monitor account",
      text: verificationEmailText({ name: input.name, verifyUrl: input.verifyUrl }),
      html: verificationEmailHtml({ name: input.name, verifyUrl: input.verifyUrl, logoUrl: logoUrlFor(input.verifyUrl) }),
    });
    return { sent: true };
  } catch (err) {
    console.error("[email] SMTP send failed", err);
    return { sent: false, error: err instanceof Error ? err.message : "Unknown email error" };
  }
}
