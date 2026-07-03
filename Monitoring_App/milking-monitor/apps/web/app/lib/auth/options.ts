import type { NextAuthOptions } from "next-auth";
import { Resend } from "resend";
import EmailProvider from "next-auth/providers/email";
import CredentialsProvider from "next-auth/providers/credentials";
import type { SendVerificationRequestParams } from "next-auth/providers/email";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { eq } from "drizzle-orm";
import { db } from "../../../lib/db/client";
import { users, accounts, authSessions, verificationTokens } from "../../../lib/db/schema";
import { hashPassword, verifyPassword } from "../../../lib/auth/password";

const resend = new Resend(process.env.RESEND_API_KEY);

function normalizeFrom() {
  return process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev";
}

function normalizeFromName() {
  return process.env.RESEND_FROM_NAME || "Milking Monitor";
}

async function sendVerificationRequest(
  params: SendVerificationRequestParams
): Promise<void> {
  const { identifier, url } = params;

  if (!process.env.RESEND_API_KEY) {
    throw new Error("Missing RESEND_API_KEY");
  }

  const email = identifier;

  const subject = "Your Milking Monitor sign-in link";
  const html = `
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <p>Hello,</p>
      <p>You requested a sign-in link for <strong>Milking Monitor</strong>.</p>
      <p>
        <a href="${url}" target="_blank" rel="noopener"
           style="display:inline-block;background:#0f7a52;color:white;padding:10px 14px;border-radius:6px;text-decoration:none;">
          Sign in
        </a>
      </p>
      <p>This link will expire soon.</p>
      <p>If you didn’t request this, you can ignore this email.</p>
    </div>
  `;

  await resend.emails.send({
    from: `${normalizeFromName()} <${normalizeFrom()}>`,
    to: [email],
    subject,
    html,
    text: `Sign in to Milking Monitor: ${url}`,
  });
}

export const authOptions: NextAuthOptions = {
  adapter: DrizzleAdapter(db, {
    usersTable: users,
    accountsTable: accounts,
    sessionsTable: authSessions,
    verificationTokensTable: verificationTokens,
  }),
  secret: process.env.AUTH_SECRET,
  session: { strategy: "jwt" },
  providers: [
    EmailProvider({
      // EmailProvider requires server config, but we override sending via sendVerificationRequest.
      server: {
        host: "localhost",
        port: 25,
        auth: { user: "unused", pass: "unused" },
      },
      from: normalizeFrom(),
      sendVerificationRequest,
    }),
    CredentialsProvider({
      id: "credentials",
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          if (!credentials?.email || !credentials?.password) {
            throw new Error("Email and password are required");
          }

          const email = credentials.email.toLowerCase();
          const password = credentials.password;

          // Check if user exists in database
          let [existingUser] = await db
            .select()
            .from(users)
            .where(eq(users.email, email))
            .limit(1);

          // Auto-register user during local testing for convenience
          if (!existingUser) {
            const now = new Date();
            const userId = crypto.randomUUID ? crypto.randomUUID() : `user_${Date.now()}`;
            const passwordHash = hashPassword(password);

            [existingUser] = await db
              .insert(users)
              .values({
                id: userId,
                email: email,
                name: email.split("@")[0],
                emailVerified: now,
                password_hash: passwordHash,
              })
              .returning();

            if (!existingUser) {
              throw new Error("Failed to auto-register user");
            }
          } else {
            // Verify password for existing users
            if (!existingUser.password_hash) {
              // User was created before password_hash column existed — set it now
              const passwordHash = hashPassword(password);
              await db
                .update(users)
                .set({ password_hash: passwordHash })
                .where(eq(users.id, existingUser.id));
              existingUser.password_hash = passwordHash;
            }

            const isValid = verifyPassword(password, existingUser.password_hash);
            if (!isValid) {
              throw new Error("Invalid password");
            }
          }

          return {
            id: existingUser.id,
            email: existingUser.email,
            name: existingUser.name,
          };
        } catch (err) {
          console.error("[auth] authorize error:", err);
          throw err;
        }
      },
    }),
  ],
  pages: {
    signIn: "/sign-in",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
        session.user.email = token.email;
        session.user.name = token.name;
      }
      return session;
    },
  },
  debug: process.env.NODE_ENV !== "production",
};
