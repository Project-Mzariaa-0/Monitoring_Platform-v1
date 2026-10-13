import { getServerSession } from "next-auth";
import { authOptions } from "../../app/lib/auth/options";

export async function getApiSession() {
  return getServerSession(authOptions);
}

export async function requireApiSession(): Promise<Response | null> {
  const session = await getApiSession();

  if (!session?.user?.email) {
    return Response.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }

  return null;
}

export async function requireApiSessionOrServiceToken(request: Request): Promise<Response | null> {
  const expectedToken = process.env.INFERENCE_SERVICE_TOKEN;
  const authorization = request.headers.get("authorization");

  if (expectedToken && authorization === `Bearer ${expectedToken}`) {
    return null;
  }

  return requireApiSession();
}