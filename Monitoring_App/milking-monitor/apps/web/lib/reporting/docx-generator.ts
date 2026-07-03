import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
} from "docx";

interface ReportData {
  session: {
    id: string;
    supervisor_name: string;
    employee_name: string;
    scheduled_start_time: string;
    estimated_end_time: string;
    actual_end_time: string | null;
    row_1_cow_count: number;
    row_2_cow_count: number;
    status: string;
  };
  cowProcesses: Array<{
    id: string;
    cow_position: number;
    detected_start_time: string | null;
    detected_end_time: string | null;
    overall_status: string;
  }>;
  taskEvents: Array<{
    id: string;
    task_id: string;
    detected_start_time: string | null;
    detected_end_time: string | null;
    duration_seconds: number;
    status: string;
    override_status?: string;
  }>;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "N/A";
  return new Date(dateString).toLocaleString();
}

function statusToDisplay(status: string): string {
  return status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export async function generateDocxReport(data: ReportData): Promise<Uint8Array> {
  const { session, cowProcesses, taskEvents } = data;

  const children: (Paragraph | Table)[] = [];

  // Title
  children.push(
    new Paragraph({
      children: [new TextRun({ text: "Milking Session Report", bold: true, size: 32 })],
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
    }),
  );

  // Session details
  children.push(
    new Paragraph({
      children: [new TextRun({ text: "Session Details", bold: true, size: 24 })],
      heading: HeadingLevel.HEADING_1,
    }),
  );

  const sessionDetails = [
    `Session ID: ${session.id}`,
    `Supervisor: ${session.supervisor_name}`,
    `Employee: ${session.employee_name}`,
    `Scheduled Start: ${formatDate(session.scheduled_start_time)}`,
    `Estimated End: ${formatDate(session.estimated_end_time)}`,
    `Actual End: ${formatDate(session.actual_end_time)}`,
    `Row 1 Cow Count: ${session.row_1_cow_count}`,
    `Row 2 Cow Count: ${session.row_2_cow_count}`,
    `Status: ${statusToDisplay(session.status)}`,
  ];

  for (const detail of sessionDetails) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: detail, size: 20 })],
        spacing: { after: 60 },
      }),
    );
  }

  // Cow processes
  if (cowProcesses.length > 0) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: "Cow Processes", bold: true, size: 24 })],
        heading: HeadingLevel.HEADING_1,
      }),
    );

    const headerRow = new TableRow({
      children: [
        new TableCell({ children: [new Paragraph("Position")], width: { size: 1500, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("Start Time")], width: { size: 2500, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("End Time")], width: { size: 2500, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("Status")], width: { size: 2000, type: WidthType.DXA } }),
      ],
    });

    const cowRows = cowProcesses.map(
      (cp) =>
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph(`Row ${cp.cow_position}`)] }),
            new TableCell({ children: [new Paragraph(formatDate(cp.detected_start_time))] }),
            new TableCell({ children: [new Paragraph(formatDate(cp.detected_end_time))] }),
            new TableCell({ children: [new Paragraph(statusToDisplay(cp.overall_status))] }),
          ],
        }),
    );

    children.push(
      new Table({
        rows: [headerRow, ...cowRows],
        width: { size: 8500, type: WidthType.DXA },
      }),
    );
  }

  // Task events
  if (taskEvents.length > 0) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: "Task Events", bold: true, size: 24 })],
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240 },
      }),
    );

    const headerRow = new TableRow({
      children: [
        new TableCell({ children: [new Paragraph("Task")], width: { size: 1200, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("Start Time")], width: { size: 2000, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("End Time")], width: { size: 2000, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("Duration (s)")], width: { size: 1200, type: WidthType.DXA } }),
        new TableCell({ children: [new Paragraph("Status")], width: { size: 1500, type: WidthType.DXA } }),
      ],
    });

    const taskRows = taskEvents.map(
      (te) =>
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph(te.task_id)] }),
            new TableCell({ children: [new Paragraph(formatDate(te.detected_start_time))] }),
            new TableCell({ children: [new Paragraph(formatDate(te.detected_end_time))] }),
            new TableCell({ children: [new Paragraph(String(te.duration_seconds))] }),
            new TableCell({ children: [new Paragraph(statusToDisplay(te.override_status ?? te.status))] }),
          ],
        }),
    );

    children.push(
      new Table({
        rows: [headerRow, ...taskRows],
        width: { size: 8500, type: WidthType.DXA },
      }),
    );
  }

  // Summary
  const completedTasks = taskEvents.filter((t) => t.status === "completed").length;
  const missedTasks = taskEvents.filter((t) => t.status === "missed").length;
  const avgDuration =
    taskEvents.length > 0
      ? Math.round(taskEvents.reduce((sum, t) => sum + t.duration_seconds, 0) / taskEvents.length)
      : 0;

  children.push(
    new Paragraph({
      children: [new TextRun({ text: "Summary", bold: true, size: 24 })],
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 240 },
    }),
  );

  const summaryLines = [
    `Total Cow Processes: ${cowProcesses.length}`,
    `Total Task Events: ${taskEvents.length}`,
    `Completed Tasks: ${completedTasks}`,
    `Missed Tasks: ${missedTasks}`,
    `Average Task Duration: ${avgDuration}s`,
  ];

  for (const line of summaryLines) {
    children.push(
      new Paragraph({
        children: [new TextRun({ text: line, size: 20 })],
        spacing: { after: 60 },
      }),
    );
  }

  const doc = new Document({
    sections: [{ children }],
  });

  return Packer.toBuffer(doc);
}
