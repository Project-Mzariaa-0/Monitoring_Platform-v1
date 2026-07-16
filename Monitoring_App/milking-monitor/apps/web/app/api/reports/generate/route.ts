import { mkdir, writeFile } from "fs/promises";
import { join } from "path";
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

  // Fetch employee analytics for this session's employee
  const employeeAnalyticsList = await getEmployeeAnalytics();
  const employeeAnalytics = employeeAnalyticsList.find(
    (e) => e.employee_name === details.session.employee_name,
  ) ?? null;

  // Fetch task analytics
  const taskAnalytics = await getTaskAnalytics();

  try {
    const docxBuffer = await generateDocxReport({
      ...details,
      employeeAnalytics: employeeAnalytics ?? undefined,
      taskAnalytics,
    });

    const reportsDir = join(process.cwd(), "public", "reports");
    await mkdir(reportsDir, { recursive: true });
    const filePath = join(reportsDir, `${parsed.data.session_id}.docx`);
    await writeFile(filePath, Buffer.from(docxBuffer));

    const report = await createReport(parsed.data.session_id, `/reports/${parsed.data.session_id}.docx`);

    return Response.json({
      ok: true,
      route: "reports:generate",
      data: {
        report: {
          id: report.id,
          session_id: report.session_id,
          docx_file_url: report.docx_file_url,
          generated_at: report.generated_at,
        },
      },
    }, { status: 201 });
  } catch (error) {
    console.error("[reports] generation failed:", error);
    return Response.json({ ok: false, error: "Report generation failed" }, { status: 500 });
  }
}
