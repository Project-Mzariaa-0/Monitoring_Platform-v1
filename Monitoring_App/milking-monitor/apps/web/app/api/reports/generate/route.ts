import { createReport, getSessionDetails, getEmployeeAnalytics, getTaskAnalytics } from "../../../../lib/data/store";
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

  const employeeAnalyticsList = await getEmployeeAnalytics();
  const employeeAnalytics = employeeAnalyticsList.find(
    (e) => e.employee_name === details.session.employee_name,
  ) ?? null;

  const taskAnalytics = await getTaskAnalytics();

  try {
    const docxBuffer = await generateDocxReport({
      ...details,
      employeeAnalytics: employeeAnalytics ?? undefined,
      taskAnalytics,
    });

    await createReport(parsed.data.session_id, null);

    return new Response(Buffer.from(docxBuffer), {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="milking-report-${parsed.data.session_id.slice(0, 8)}.docx"`,
      },
    });
  } catch (error) {
    console.error("[reports] generation failed:", error);
    return Response.json({ ok: false, error: "Report generation failed" }, { status: 500 });
  }
}
