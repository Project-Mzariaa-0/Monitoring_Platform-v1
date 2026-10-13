import { buildVerificationUrl as buildUrl } from "./resend";
import { sendVerificationEmail as sendViaResend } from "./resend";
import { isSmtpConfigured, sendSmtpVerificationEmail } from "./smtp";

export const buildVerificationUrl = buildUrl;

export type VerificationMail = { to: string; name: string; verifyUrl: string };

/**
 * Sends the verification email via the configured provider.
 * EMAIL_PROVIDER=smtp (default) uses Gmail/SMTP — no domain needed.
 * EMAIL_PROVIDER=resend uses the Resend API (needs a verified domain for real recipients).
 */
export async function sendVerificationEmail(input: VerificationMail): Promise<{ sent: boolean; error?: string }> {
  const provider = (process.env.EMAIL_PROVIDER || "smtp").toLowerCase();
  if (provider === "resend") {
    return sendViaResend(input);
  }
  if (isSmtpConfigured()) {
    return sendSmtpVerificationEmail(input);
  }
  // Fall back to Resend if SMTP is not configured but a Resend key exists.
  if (process.env.RESEND_API_KEY) {
    return sendViaResend(input);
  }
  console.error("[email] No email provider configured (set SMTP_USER + SMTP_PASS or RESEND_API_KEY)");
  return { sent: false, error: "Email service is not configured" };
}
