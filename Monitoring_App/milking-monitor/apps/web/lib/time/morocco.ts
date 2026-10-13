export const MOROCCO_TIME_ZONE = "Africa/Casablanca";

/**
 * Morocco switched to permanent GMT (UTC+0) on 20 Sep 2026 at 02:00 local.
 * Node/ICU tzdata in many runtimes still returns the old +1 offset for dates
 * after the change, which shifts every displayed/entered time by 1 hour.
 * So for dates on/after the cutover we treat Morocco as UTC directly.
 */
export const MOROCCO_PERMANENT_GMT_START_MS = Date.UTC(2026, 8, 20, 1, 0, 0);

function isPermanentGmtPeriod(dateMs: number): boolean {
  return dateMs >= MOROCCO_PERMANENT_GMT_START_MS;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Format a Date as `YYYY-MM-DDTHH:mm` wall time in Morocco (for datetime-local inputs). */
export function formatMoroccoDateTimeInput(date: Date): string {
  const ms = date.getTime();
  if (isPermanentGmtPeriod(ms)) {
    // Morocco = UTC now: use UTC parts directly, no Intl (avoids stale tzdata).
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
  }
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: MOROCCO_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  })
    .formatToParts(date)
    .reduce<Record<string, string>>((result, part) => {
      result[part.type] = part.value;
      return result;
    }, {});

  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

/**
 * Convert a `datetime-local` wall-time string (interpreted as Morocco time)
 * to an ISO UTC string for storage/APIs.
 */
export function moroccoDateTimeInputToIso(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) return new Date(value).toISOString();

  const [, year, month, day, hour, minute] = match;
  const wallAsUtc = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));

  // Post-cutover: Morocco wall time IS UTC.
  if (wallAsUtc >= MOROCCO_PERMANENT_GMT_START_MS - 2 * 3_600_000) {
    return new Date(wallAsUtc).toISOString();
  }

  const targetUtc = wallAsUtc;
  let candidate = targetUtc;

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const formatted = formatMoroccoDateTimeInput(new Date(candidate));
    const parsed = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(formatted);
    if (!parsed) break;
    const displayedUtc = Date.UTC(
      Number(parsed[1]),
      Number(parsed[2]) - 1,
      Number(parsed[3]),
      Number(parsed[4]),
      Number(parsed[5]),
    );
    const difference = targetUtc - displayedUtc;
    candidate += difference;
    if (difference === 0) break;
  }

  return new Date(candidate).toISOString();
}

/** Format an ISO/UTC timestamp for display in Morocco time. Always explicit — never depends on server TZ. */
export function formatInMorocco(
  value: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = {},
): string {
  if (!value) return "N/A";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "N/A";
  if (isPermanentGmtPeriod(date.getTime())) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      dateStyle: "medium",
      timeStyle: "short",
      ...options,
    }).format(date);
  }
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: MOROCCO_TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
    ...options,
  }).format(date);
}

/** Short time-only Morocco format (HH:mm). */
export function formatTimeInMorocco(value: string | Date | null | undefined): string {
  if (!value) return "N/A";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "N/A";
  if (isPermanentGmtPeriod(date.getTime())) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(date);
  }
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: MOROCCO_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date);
}

/** Current wall-time in Morocco as `datetime-local` string (for min attributes / defaults). */
export function nowMoroccoInput(): string {
  return formatMoroccoDateTimeInput(new Date());
}
