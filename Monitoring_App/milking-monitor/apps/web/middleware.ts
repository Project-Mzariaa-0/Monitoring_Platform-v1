import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const securityHeaders = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "X-XSS-Protection": "1; mode=block",
  "Content-Security-Policy": "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' http://localhost:8001 http://localhost:3000 ws: wss:;",
};

function applySecurityHeaders(response: NextResponse, request: NextRequest) {
  const requestId = request.headers.get("x-request-id") || crypto.randomUUID();

  response.headers.set("x-request-id", requestId);

  for (const [header, value] of Object.entries(securityHeaders)) {
    response.headers.set(header, value);
  }

  return response;
}

function unauthorizedApi(request: NextRequest) {
  const response = NextResponse.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  return applySecurityHeaders(response, request);
}

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public API clock — no auth, just headers.
  if (pathname === "/api/time" || pathname.startsWith("/api/time/")) {
    return applySecurityHeaders(NextResponse.next(), request);
  }

  // API routes: JSON 401 instead of HTML redirect when unauthenticated.
  if (pathname.startsWith("/api/")) {
    const token = await getToken({ req: request, secret: process.env.AUTH_SECRET });
    if (!token?.email) {
      return unauthorizedApi(request);
    }
    return applySecurityHeaders(NextResponse.next(), request);
  }

  // Pages: redirect to sign-in with callbackUrl.
  const token = await getToken({ req: request, secret: process.env.AUTH_SECRET });
  if (!token?.email) {
    const signInUrl = request.nextUrl.clone();
    signInUrl.pathname = "/sign-in";
    signInUrl.searchParams.set("callbackUrl", request.nextUrl.pathname);
    const response = NextResponse.redirect(signInUrl);
    return applySecurityHeaders(response, request);
  }

  return applySecurityHeaders(NextResponse.next(), request);
}

export const config = {
  matcher: [
    "/((?!api/auth|api/events/ingest|api/sessions/active|api/sessions/[^/]+/status|api/time|sign-in|sign-up|verify-email|_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
