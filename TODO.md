# Auth Switch & Verification Fix TODO

## 0) Confirm requirements (from user)
- Switch auth away from Clerk to a “better auth” using **magic link**.
- Use **Resend** for email (RESEND_API_KEY exists).
- VERIFICATION method: **magic link**
- AUTH_SECRET / NEXTAUTH_URL: **not present** in `apps/web/.env.local`

## 1) Repo inspection (before editing)
- Inspect current auth-related dependencies in `apps/web/package.json`
- Inspect current auth usage:
  - `apps/web/app/layout.tsx` (ClerkProvider)
  - `apps/web/middleware.ts` (clerkMiddleware protect)
  - `apps/web/app/sign-in/**` and `apps/web/app/sign-up/**`
  - `apps/web/components/auth/*` (email forms)
- Inspect any existing protected route logic (dashboard layout/middleware)

## 2) Choose auth implementation that works with missing env vars
- Prefer an implementation that can function with a secret we can add:
  - Add `NEXTAUTH_SECRET` / `AUTH_SECRET` usage
  - Derive URL from runtime if `NEXTAUTH_URL` missing
- Decide concrete framework:
  - NextAuth/Auth.js v5 with custom email provider via Resend (magic link)

## 3) Planned code changes (high level)
- Remove Clerk integration:
  - Remove `ClerkProvider` from `apps/web/app/layout.tsx`
  - Remove `clerkMiddleware` usage from `apps/web/middleware.ts`
  - Remove/replace Clerk-based sign-in/sign-up pages & components
- Add new auth route(s) + callbacks:
  - Add NextAuth route handler under `apps/web/app/api/auth/[...]/route.ts`
- Add new UI:
  - Replace `apps/web/app/sign-in/.../page.tsx`
  - Replace `apps/web/app/sign-up/.../page.tsx`
  - Replace `apps/web/components/auth/email-sign-in-form.tsx`
  - Replace `apps/web/components/auth/email-sign-up-form.tsx`
- Ensure protected routes work:
  - Update middleware/protection to use NextAuth session checks

## 4) Add required env documentation
- Update README or create `AUTH_SETUP.md` describing required env vars:
  - `NEXTAUTH_SECRET` (or `AUTH_SECRET`)
  - `NEXTAUTH_URL` (recommended)
  - `RESEND_API_KEY`

## 5) Testing (THOROUGH = choice “2”)
- Frontend:
  - Sign up → request magic link → confirm email arrives (Resend)
  - Click magic link → confirm session is created → redirect works
  - Sign out → sign in via magic link works
  - Error cases:
    - invalid magic link / expired magic link
    - requesting multiple links quickly (rate limiting / UI)
    - email send failure handling
- Backend/API:
  - Exercise auth endpoints (NextAuth):
    - happy path (request link)
    - error path (missing email, invalid token)
    - callback handling
  - Curl tests where possible

## Progress
- [ ] 0) Confirm requirements (done)
- [ ] 1) Repo inspection
- [ ] 2) Implementation choice
- [ ] 3) Implement code changes
- [ ] 4) Add env documentation
- [ ] 5) Thorough testing
