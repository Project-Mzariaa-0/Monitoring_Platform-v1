import { createReport, getSessionDetails } from "../../../../lib/data/store";
import { generateReportSchema } from "../../../../lib/validation/report";
import { generateDocxReport } from "../../../../lib/reporting/docx-generator";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) {
    return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = generateReportSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json(
      { ok: false, error: "Validation failed", details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  const details = await getSessionDetails(parsed.data.session_id);
  if (!details) {
    return Response.json({ ok: false, error: "Session not found" }, { status: 404 });
  }

  const docxBuffer = await generateDocxReport(details);

  const report = await createReport(parsed.data.session_id, `/reports/${parsed.data.session_id}.docx`);

  return new Response(Buffer.from(docxBuffer), {
    status: 201,
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "Content-Disposition": `attachment; filename="report-${parsed.data.session_id}.docx"`,
    },
  });
}
