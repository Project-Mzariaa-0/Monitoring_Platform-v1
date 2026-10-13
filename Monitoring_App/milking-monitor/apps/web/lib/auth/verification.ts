import { and, eq } from "drizzle-orm";
import { randomBytes } from "crypto";
import { db } from "../db/client";
import { users, verificationTokens } from "../db/schema";

export const VERIFICATION_TTL_MS = 24 * 60 * 60 * 1000;

export async function createEmailVerificationToken(email: string): Promise<string> {
  const normalized = email.trim().toLowerCase();
  await db.delete(verificationTokens).where(eq(verificationTokens.identifier, normalized));

  const token = randomBytes(48).toString("hex");
  await db.insert(verificationTokens).values({
    identifier: normalized,
    token,
    expires: new Date(Date.now() + VERIFICATION_TTL_MS),
  });
  return token;
}

export async function consumeEmailVerificationToken(email: string, token: string): Promise<{ ok: boolean; error?: string }> {
  const normalized = email.trim().toLowerCase();
  const [row] = await db
    .select()
    .from(verificationTokens)
    .where(and(eq(verificationTokens.identifier, normalized), eq(verificationTokens.token, token)))
    .limit(1);

  if (!row) return { ok: false, error: "Invalid or expired verification link" };
  if (row.expires.getTime() < Date.now()) {
    await db
      .delete(verificationTokens)
      .where(and(eq(verificationTokens.identifier, normalized), eq(verificationTokens.token, token)));
    return { ok: false, error: "Verification link has expired" };
  }

  await db.delete(verificationTokens).where(eq(verificationTokens.identifier, normalized));
  const now = new Date();
  await db
    .update(users)
    .set({ emailVerified: now, registration_completed_at: now })
    .where(eq(users.email, normalized));

  return { ok: true };
}
