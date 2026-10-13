import { formatInMorocco, formatMoroccoDateTimeInput } from "../../../lib/time/morocco";

export async function GET() {
  const now = new Date();
  return Response.json({
    ok: true,
    data: {
      nowUtc: now.toISOString(),
      nowMoroccoInput: formatMoroccoDateTimeInput(now).slice(0, 16),
      nowMoroccoLabel: formatInMorocco(now.toISOString()),
    },
  });
}
