import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { eq } from "drizzle-orm";
import { db } from "../../../lib/db/client";
import { users, accounts, authSessions, verificationTokens } from "../../../lib/db/schema";
import { hashPassword, verifyPassword } from "../../../lib/auth/password";

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

          if (!existingUser) {
            throw new Error("Invalid credentials");
          }

          if (!existingUser.password_hash || !existingUser.registration_completed_at) {
            throw new Error("Invalid credentials");
          }

          const isValid = verifyPassword(password, existingUser.password_hash);
          if (!isValid) {
            throw new Error("Invalid credentials");
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
