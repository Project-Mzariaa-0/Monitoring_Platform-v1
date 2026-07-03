import { desc, eq, inArray, and } from "drizzle-orm";
import { db } from "../db/client";
import { sessions, cowProcesses, taskEvents, reports, auditLog, supervisors, employees } from "../db/schema";
import { TASK_LABELS } from "../constants";

export type SessionStatus = "scheduled" | "active" | "completed" | "ended_early";

export type SessionRecord = {
  id: string;
  supervisor_id: string;
  employee_id: string;
  employee_name: string;
  supervisor_name: string;
  supervisor_email: string;
  scheduled_start_time: string;
  estimated_end_time: string;
  actual_end_time: string | null;
  row_1_cow_count: number;
  row_2_cow_count: number;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
};

export type CowProcessRecord = {
  id: string;
  session_id: string;
  cow_position: 1 | 2;
  detected_start_time: string | null;
  detected_end_time: string | null;
  overall_status: "in_progress" | "completed" | "completed_with_missed_tasks";
};

export type TaskEventRecord = {
  id: string;
  cow_process_id: string;
  task_id: "TASK-01" | "TASK-02" | "TASK-03" | "TASK-04" | "TASK-05" | "TASK-06";
  detected_start_time: string | null;
  detected_end_time: string | null;
  duration_seconds: number;
  status: "completed" | "missed" | "anomaly_flagged" | "unverifiable";
  override_status?: "completed" | "missed" | "anomaly_flagged" | "unverifiable";
  override_reason?: string;
  overridden_by?: string;
  overridden_at?: string;
};

export type AuditLogEntry = {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string;
  reason?: string;
  created_at: string;
};

export type ReportRecord = {
  id: string;
  session_id: string;
  generated_at: string;
  docx_file_url: string;
  email_sent_at: string | null;
};

function toISO(value: Date | string | null): string | null {
  if (value === null) return null;
  if (typeof value === "string") return value;
  return value.toISOString();
}

export async function listSessions(): Promise<SessionRecord[]> {
  const rows = await db.select().from(sessions).orderBy(desc(sessions.created_at));
  return rows.map((r) => ({
    id: r.id,
    supervisor_id: r.supervisor_id,
    employee_id: r.employee_id,
    employee_name: r.employee_name,
    supervisor_name: r.supervisor_name,
    supervisor_email: r.supervisor_email,
    scheduled_start_time: toISO(r.scheduled_start_time) ?? "",
    estimated_end_time: toISO(r.estimated_end_time) ?? "",
    actual_end_time: toISO(r.actual_end_time),
    row_1_cow_count: Number(r.row_1_cow_count),
    row_2_cow_count: Number(r.row_2_cow_count),
    status: r.status as SessionStatus,
    created_at: toISO(r.created_at) ?? "",
    updated_at: toISO(r.updated_at) ?? "",
  }));
}

export async function getSession(sessionId: string): Promise<SessionRecord | null> {
  const [row] = await db.select().from(sessions).where(eq(sessions.id, sessionId)).limit(1);
  if (!row) return null;
  return {
    id: row.id,
    supervisor_id: row.supervisor_id,
    employee_id: row.employee_id,
    employee_name: row.employee_name,
    supervisor_name: row.supervisor_name,
    supervisor_email: row.supervisor_email,
    scheduled_start_time: toISO(row.scheduled_start_time) ?? "",
    estimated_end_time: toISO(row.estimated_end_time) ?? "",
    actual_end_time: toISO(row.actual_end_time),
    row_1_cow_count: Number(row.row_1_cow_count),
    row_2_cow_count: Number(row.row_2_cow_count),
    status: row.status as SessionStatus,
    created_at: toISO(row.created_at) ?? "",
    updated_at: toISO(row.updated_at) ?? "",
  };
}

export async function getSessionDetails(
  sessionId: string,
): Promise<{
  session: SessionRecord;
  cowProcesses: CowProcessRecord[];
  taskEvents: TaskEventRecord[];
  reports: ReportRecord[];
} | null> {
  const session = await getSession(sessionId);
  if (!session) return null;

  const cowRows = await db.select().from(cowProcesses).where(eq(cowProcesses.session_id, sessionId)).orderBy(cowProcesses.cow_position);
  const cowProcessesRecords: CowProcessRecord[] = cowRows.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    cow_position: Number(r.cow_position) as 1 | 2,
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    overall_status: r.overall_status as CowProcessRecord["overall_status"],
  }));

  const cowIds = cowProcessesRecords.map((c) => c.id);
  const taskRows =
    cowIds.length > 0
      ? await db.select().from(taskEvents).where(inArray(taskEvents.cow_process_id, cowIds)).orderBy(taskEvents.created_at)
      : [];
  const taskEventsRecords: TaskEventRecord[] = taskRows.map((r) => ({
    id: r.id,
    cow_process_id: r.cow_process_id,
    task_id: r.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    duration_seconds: Number(r.duration_seconds),
    status: r.status as TaskEventRecord["status"],
    override_status: (r.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: r.override_reason ?? undefined,
    overridden_by: r.overridden_by ?? undefined,
    overridden_at: toISO(r.overridden_at) ?? undefined,
  }));

  const reportRows = await db.select().from(reports).where(eq(reports.session_id, sessionId)).orderBy(desc(reports.generated_at));
  const reportRecords: ReportRecord[] = reportRows.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    generated_at: toISO(r.generated_at) ?? "",
    docx_file_url: r.docx_file_url,
    email_sent_at: toISO(r.email_sent_at),
  }));

  return { session, cowProcesses: cowProcessesRecords, taskEvents: taskEventsRecords, reports: reportRecords };
}

export async function createSession(input: {
  supervisor_id: string;
  employee_id: string;
  employee_name: string;
  supervisor_name: string;
  supervisor_email: string;
  scheduled_start_time: string;
  estimated_end_time: string;
  row_1_cow_count: number;
  row_2_cow_count: number;
}): Promise<SessionRecord> {
  const isUUID = (s: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

  if (isUUID(input.supervisor_id)) {
    const [supervisor] = await db.select().from(supervisors).where(eq(supervisors.id, input.supervisor_id)).limit(1);
    if (!supervisor) throw new Error("Supervisor not found");
  }

  if (isUUID(input.employee_id)) {
    const [employee] = await db.select().from(employees).where(eq(employees.id, input.employee_id)).limit(1);
    if (!employee) throw new Error("Employee not found");
  }

  const now = new Date();

  const result = await db.transaction(async (tx) => {
    const [inserted] = await tx
      .insert(sessions)
      .values({
        supervisor_id: input.supervisor_id,
        employee_id: input.employee_id,
        employee_name: input.employee_name,
        supervisor_name: input.supervisor_name,
        supervisor_email: input.supervisor_email,
        scheduled_start_time: new Date(input.scheduled_start_time),
        estimated_end_time: new Date(input.estimated_end_time),
        actual_end_time: null,
        row_1_cow_count: input.row_1_cow_count,
        row_2_cow_count: input.row_2_cow_count,
        status: "scheduled",
        created_at: now,
        updated_at: now,
      })
      .returning();

    if (!inserted) throw new Error("Failed to insert session");

    await tx.insert(cowProcesses).values([
      {
        session_id: inserted.id,
        cow_position: 1,
        detected_start_time: null,
        detected_end_time: null,
        overall_status: "in_progress",
        created_at: now,
        updated_at: now,
      },
      {
        session_id: inserted.id,
        cow_position: 2,
        detected_start_time: null,
        detected_end_time: null,
        overall_status: "in_progress",
        created_at: now,
        updated_at: now,
      },
    ]);

    return inserted;
  });

  return {
    id: result.id,
    supervisor_id: result.supervisor_id,
    employee_id: result.employee_id,
    employee_name: result.employee_name,
    supervisor_name: result.supervisor_name,
    supervisor_email: result.supervisor_email,
    scheduled_start_time: toISO(result.scheduled_start_time) ?? "",
    estimated_end_time: toISO(result.estimated_end_time) ?? "",
    actual_end_time: toISO(result.actual_end_time),
    row_1_cow_count: Number(result.row_1_cow_count),
    row_2_cow_count: Number(result.row_2_cow_count),
    status: result.status as SessionStatus,
    created_at: toISO(result.created_at) ?? "",
    updated_at: toISO(result.updated_at) ?? "",
  };
}

export async function updateSessionEmployee(
  sessionId: string,
  employeeId: string,
  employeeName: string,
  actorId: string,
): Promise<SessionRecord | null> {
  const [updated] = await db
    .update(sessions)
    .set({
      employee_id: employeeId,
      employee_name: employeeName,
      updated_at: new Date(),
    })
    .where(eq(sessions.id, sessionId))
    .returning();

  if (!updated) return null;

  await db.insert(auditLog).values({
    entity_type: "Session",
    entity_id: sessionId,
    action: "employee_reassigned",
    actor_id: actorId,
    reason: null,
    created_at: new Date(),
  });

  return {
    id: updated.id,
    supervisor_id: updated.supervisor_id,
    employee_id: updated.employee_id,
    employee_name: updated.employee_name,
    supervisor_name: updated.supervisor_name,
    supervisor_email: updated.supervisor_email,
    scheduled_start_time: toISO(updated.scheduled_start_time) ?? "",
    estimated_end_time: toISO(updated.estimated_end_time) ?? "",
    actual_end_time: toISO(updated.actual_end_time),
    row_1_cow_count: Number(updated.row_1_cow_count),
    row_2_cow_count: Number(updated.row_2_cow_count),
    status: updated.status as SessionStatus,
    created_at: toISO(updated.created_at) ?? "",
    updated_at: toISO(updated.updated_at) ?? "",
  };
}

export async function ingestTaskEvent(input: {
  session_id: string;
  cow_position: 1 | 2;
  task_id: TaskEventRecord["task_id"];
  status: TaskEventRecord["status"];
  confidence_score?: number;
  detected_start_time?: string | null;
  detected_end_time?: string | null;
  duration_seconds?: number;
}): Promise<TaskEventRecord | null> {
  const cowRow = await db
    .select()
    .from(cowProcesses)
    .where(and(eq(cowProcesses.session_id, input.session_id), eq(cowProcesses.cow_position, input.cow_position)))
    .limit(1);

  const cow = cowRow[0];
  if (!cow) return null;

  const detectedStart = input.detected_start_time ?? null;
  const detectedEnd = input.detected_end_time ?? null;

  const [inserted] = await db
    .insert(taskEvents)
    .values({
      cow_process_id: cow.id,
      task_id: input.task_id,
      detected_start_time: detectedStart ? new Date(detectedStart) : null,
      detected_end_time: detectedEnd ? new Date(detectedEnd) : null,
      duration_seconds: input.duration_seconds ?? 0,
      status: input.status,
      override_status: null,
      override_reason: null,
      overridden_by: null,
      overridden_at: null,
      created_at: new Date(),
    })
    .returning();

  if (!inserted) return null;

  return {
    id: inserted.id,
    cow_process_id: inserted.cow_process_id,
    task_id: inserted.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(inserted.detected_start_time),
    detected_end_time: toISO(inserted.detected_end_time),
    duration_seconds: Number(inserted.duration_seconds),
    status: inserted.status as TaskEventRecord["status"],
    override_status: (inserted.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: inserted.override_reason ?? undefined,
    overridden_by: inserted.overridden_by ?? undefined,
    overridden_at: inserted.overridden_at ? toISO(inserted.overridden_at) ?? undefined : undefined,
  };
}

export async function overrideTaskEvent(
  taskEventId: string,
  overrideStatus: TaskEventRecord["status"],
  reason: string,
  actorId: string,
): Promise<TaskEventRecord | null> {
  const [updated] = await db
    .update(taskEvents)
    .set({
      override_status: overrideStatus,
      override_reason: reason,
      overridden_by: actorId,
      overridden_at: new Date(),
    })
    .where(eq(taskEvents.id, taskEventId))
    .returning();

  if (!updated) return null;

  await db.insert(auditLog).values({
    entity_type: "TaskEvent",
    entity_id: taskEventId,
    action: "task_override",
    actor_id: actorId,
    reason,
    created_at: new Date(),
  });

  return {
    id: updated.id,
    cow_process_id: updated.cow_process_id,
    task_id: updated.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(updated.detected_start_time),
    detected_end_time: toISO(updated.detected_end_time),
    duration_seconds: Number(updated.duration_seconds),
    status: updated.status as TaskEventRecord["status"],
    override_status: (updated.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: updated.override_reason ?? undefined,
    overridden_by: updated.overridden_by ?? undefined,
    overridden_at: updated.overridden_at ? toISO(updated.overridden_at) ?? undefined : undefined,
  };
}

export async function createReport(sessionId: string, docxFileUrl: string): Promise<ReportRecord> {
  const now = new Date();
  const [inserted] = await db
    .insert(reports)
    .values({
      session_id: sessionId,
      generated_at: now,
      docx_file_url: docxFileUrl,
      email_sent_at: now,
      created_at: now,
      updated_at: now,
    })
    .returning();

  if (!inserted) throw new Error("Failed to insert report");

  return {
    id: inserted.id,
    session_id: inserted.session_id,
    generated_at: toISO(inserted.generated_at) ?? "",
    docx_file_url: inserted.docx_file_url,
    email_sent_at: toISO(inserted.email_sent_at),
  };
}

export async function getStatistics(): Promise<{
  totalSessions: number;
  completedSessions: number;
  missedCount: number;
  averageDuration: number;
  reports: ReportRecord[];
}> {
  const sessionRows = await db.select().from(sessions);
  const totalSessions = sessionRows.length;
  const completedSessions = sessionRows.filter((s) => s.status === "completed").length;

  const taskRows = await db.select().from(taskEvents);
  const missedCount = taskRows.filter((t) => t.status === "missed" || t.override_status === "missed").length;
  const averageDuration = taskRows.length === 0 ? 0 : Math.round(taskRows.reduce((sum, t) => sum + Number(t.duration_seconds), 0) / taskRows.length);

  const reportRows = await db.select().from(reports).orderBy(desc(reports.generated_at));
  const reportsRecords: ReportRecord[] = reportRows.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    generated_at: toISO(r.generated_at) ?? "",
    docx_file_url: r.docx_file_url,
    email_sent_at: toISO(r.email_sent_at),
  }));

  return { totalSessions, completedSessions, missedCount, averageDuration, reports: reportsRecords };
}

export async function getMonitoringOverview(): Promise<{
  activeSession: SessionRecord | null;
  activeCowProcesses: CowProcessRecord[];
  activeTaskEvents: TaskEventRecord[];
  totalSessions: number;
  activeCount: number;
  missedCount: number;
}> {
  const totalSessionRows = await db.select().from(sessions);
  const totalSessions = totalSessionRows.length;
  const activeCount = totalSessionRows.filter((s) => s.status === "active").length;

  const activeSessionRow =
    (await db.select().from(sessions).where(eq(sessions.status, "active")).orderBy(desc(sessions.updated_at)).limit(1)).at(0) ??
    (await db.select().from(sessions).orderBy(desc(sessions.created_at)).limit(1)).at(0) ??
    null;

  const activeSession: SessionRecord | null = activeSessionRow
    ? {
        id: activeSessionRow.id,
        supervisor_id: activeSessionRow.supervisor_id,
        employee_id: activeSessionRow.employee_id,
        employee_name: activeSessionRow.employee_name,
        supervisor_name: activeSessionRow.supervisor_name,
        supervisor_email: activeSessionRow.supervisor_email,
        scheduled_start_time: toISO(activeSessionRow.scheduled_start_time) ?? "",
        estimated_end_time: toISO(activeSessionRow.estimated_end_time) ?? "",
        actual_end_time: toISO(activeSessionRow.actual_end_time),
        row_1_cow_count: Number(activeSessionRow.row_1_cow_count),
        row_2_cow_count: Number(activeSessionRow.row_2_cow_count),
        status: activeSessionRow.status as SessionStatus,
        created_at: toISO(activeSessionRow.created_at) ?? "",
        updated_at: toISO(activeSessionRow.updated_at) ?? "",
      }
    : null;

  const activeCowProcesses: CowProcessRecord[] = activeSession
    ? (await db
        .select()
        .from(cowProcesses)
        .where(eq(cowProcesses.session_id, activeSession.id))
        .orderBy(cowProcesses.cow_position)).map((r) => ({
        id: r.id,
        session_id: r.session_id,
        cow_position: Number(r.cow_position) as 1 | 2,
        detected_start_time: toISO(r.detected_start_time),
        detected_end_time: toISO(r.detected_end_time),
        overall_status: r.overall_status as CowProcessRecord["overall_status"],
      }))
    : [];

  const cowIds = activeCowProcesses.map((c) => c.id);
  const activeTaskEvents: TaskEventRecord[] =
    cowIds.length > 0
      ? (await db.select().from(taskEvents).where(inArray(taskEvents.cow_process_id, cowIds)).orderBy(taskEvents.created_at)).map((r) => ({
          id: r.id,
          cow_process_id: r.cow_process_id,
          task_id: r.task_id as TaskEventRecord["task_id"],
          detected_start_time: toISO(r.detected_start_time),
          detected_end_time: toISO(r.detected_end_time),
          duration_seconds: Number(r.duration_seconds),
          status: r.status as TaskEventRecord["status"],
          override_status: (r.override_status as TaskEventRecord["override_status"]) ?? undefined,
          override_reason: r.override_reason ?? undefined,
          overridden_by: r.overridden_by ?? undefined,
          overridden_at: r.overridden_at ? toISO(r.overridden_at) ?? undefined : undefined,
        }))
      : [];

  const taskRows = await db.select().from(taskEvents);
  const missedCount = taskRows.filter((t) => t.status === "missed" || t.override_status === "missed").length;

  return { activeSession, activeCowProcesses, activeTaskEvents, totalSessions, activeCount, missedCount };
}

export async function getTaskEvent(taskEventId: string): Promise<TaskEventRecord | null> {
  const [row] = await db.select().from(taskEvents).where(eq(taskEvents.id, taskEventId)).limit(1);
  if (!row) return null;

  return {
    id: row.id,
    cow_process_id: row.cow_process_id,
    task_id: row.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(row.detected_start_time),
    detected_end_time: toISO(row.detected_end_time),
    duration_seconds: Number(row.duration_seconds),
    status: row.status as TaskEventRecord["status"],
    override_status: (row.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: row.override_reason ?? undefined,
    overridden_by: row.overridden_by ?? undefined,
    overridden_at: row.overridden_at ? toISO(row.overridden_at) ?? undefined : undefined,
  };
}

export type EmployeeAnalytics = {
  employee_name: string;
  total_sessions: number;
  completed_tasks: number;
  missed_tasks: number;
  compliance: number;
  avg_duration_seconds: number;
  status: string;
};

export type TaskAnalytics = {
  task_id: string;
  label: string;
  total: number;
  completed: number;
  missed: number;
  avg_duration_seconds: number;
};

export async function getEmployeeAnalytics(): Promise<EmployeeAnalytics[]> {
  const allSessions = await db.select().from(sessions);
  const allCowProcesses = await db.select().from(cowProcesses);
  const allTaskEvents = await db.select().from(taskEvents);

  const sessionMap = new Map(allSessions.map((s) => [s.id, s]));
  const cowProcessMap = new Map(allCowProcesses.map((c) => [c.id, c]));

  const employeeSessions = new Map<string, { name: string; sessionIds: Set<string> }>();
  for (const session of allSessions) {
    const key = session.employee_id;
    const existing = employeeSessions.get(key);
    if (existing) {
      existing.sessionIds.add(session.id);
    } else {
      employeeSessions.set(key, { name: session.employee_name, sessionIds: new Set([session.id]) });
    }
  }

  const result: EmployeeAnalytics[] = [];

  for (const [, { name, sessionIds }] of employeeSessions) {
    const employeeCowProcesses = allCowProcesses.filter((c) => sessionIds.has(c.session_id));
    const cowProcessIds = new Set(employeeCowProcesses.map((c) => c.id));
    const employeeTasks = allTaskEvents.filter((t) => cowProcessIds.has(t.cow_process_id));

    const completed = employeeTasks.filter((t) => t.status === "completed").length;
    const missed = employeeTasks.filter((t) => t.status === "missed" || t.override_status === "missed").length;
    const total = employeeTasks.length;
    const compliance = total > 0 ? Math.round((completed / total) * 100) : 0;
    const avgDuration = total > 0 ? Math.round(employeeTasks.reduce((s, t) => s + Number(t.duration_seconds), 0) / total) : 0;

    let status = "Stable";
    if (compliance >= 95) status = "Top Performer";
    else if (compliance >= 85) status = "Stable";
    else if (compliance >= 70) status = "High Speed";
    else status = "Review Req.";

    result.push({
      employee_name: name,
      total_sessions: sessionIds.size,
      completed_tasks: completed,
      missed_tasks: missed,
      compliance,
      avg_duration_seconds: avgDuration,
      status,
    });
  }

  return result.sort((a, b) => b.compliance - a.compliance);
}

export async function getTaskAnalytics(): Promise<TaskAnalytics[]> {
  const allTaskEvents = await db.select().from(taskEvents);

  const grouped = new Map<string, { total: number; completed: number; missed: number; totalDuration: number }>();

  for (const te of allTaskEvents) {
    const key = te.task_id;
    const existing = grouped.get(key) ?? { total: 0, completed: 0, missed: 0, totalDuration: 0 };
    existing.total += 1;
    if (te.status === "completed") existing.completed += 1;
    if (te.status === "missed" || te.override_status === "missed") existing.missed += 1;
    existing.totalDuration += Number(te.duration_seconds);
    grouped.set(key, existing);
  }

  const result: TaskAnalytics[] = [];

  for (const taskId of Object.keys(TASK_LABELS)) {
    const data = grouped.get(taskId);
    if (!data) {
      result.push({ task_id: taskId, label: TASK_LABELS[taskId], total: 0, completed: 0, missed: 0, avg_duration_seconds: 0 });
    } else {
      result.push({
        task_id: taskId,
        label: TASK_LABELS[taskId],
        total: data.total,
        completed: data.completed,
        missed: data.missed,
        avg_duration_seconds: data.total > 0 ? Math.round(data.totalDuration / data.total) : 0,
      });
    }
  }

  return result;
}
