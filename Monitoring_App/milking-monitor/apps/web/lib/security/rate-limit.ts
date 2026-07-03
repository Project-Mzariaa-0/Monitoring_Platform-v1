type RateLimitResult = {
  allowed: boolean;
  remaining: number;
  resetAt: number;
};

type Bucket = {
  count: number;
  resetAt: number;
};

const buckets = new Map<string, Bucket>();

export function rateLimit(identifier: string, limit = 60, windowMs = 60_000): RateLimitResult {
  const now = Date.now();
  const current = buckets.get(identifier);

  if (!current || current.resetAt <= now) {
    const resetAt = now + windowMs;
    buckets.set(identifier, { count: 1, resetAt });
    return { allowed: true, remaining: limit - 1, resetAt };
  }

  if (current.count >= limit) {
    return { allowed: false, remaining: 0, resetAt: current.resetAt };
  }

  current.count += 1;
  return { allowed: true, remaining: Math.max(limit - current.count, 0), resetAt: current.resetAt };
}
