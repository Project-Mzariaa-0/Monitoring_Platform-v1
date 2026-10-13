export type ApiErrorType =
  | "unauthorized"
  | "forbidden"
  | "not-found"
  | "rate-limited"
  | "validation"
  | "server-error"
  | "network";

export class ApiError extends Error {
  status: number;
  type: ApiErrorType;
  route: string;

  constructor(route: string, status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.route = route;
    this.status = status;
    this.type = typeForStatus(status);
  }
}

export function typeForStatus(status: number): ApiErrorType {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not-found";
  if (status === 429) return "rate-limited";
  if (status === 422 || (status >= 400 && status < 500)) return "validation";
  return "server-error";
}

/** Only unexpected/unauthenticated failures redirect to /error. Validation (422 etc.) stays inline. */
export function shouldRedirectToErrorPage(status: number): boolean {
  return status === 401 || status === 403 || status === 404 || status === 429 || status >= 500;
}

export async function parseApiError(route: string, response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => null);
  const message =
    (body as { error?: string } | null)?.error ??
    `Request failed with status ${response.status}`;
  return new ApiError(route, response.status, message);
}

export function buildErrorPageUrl(error: { status: number; type: ApiErrorType; message: string }, from: string): string {
  const params = new URLSearchParams({
    status: String(error.status),
    type: error.type,
    message: error.message.slice(0, 300),
    from: from.slice(0, 200),
  });
  return `/error?${params.toString()}`;
}

/** Call from client components when an API call fails. Returns true if redirected. */
export function redirectOnApiError(
  push: (url: string) => void,
  status: number,
  message: string,
  from: string,
): boolean {
  if (!shouldRedirectToErrorPage(status)) return false;
  push(buildErrorPageUrl({ status, type: typeForStatus(status), message }, from));
  return true;
}
