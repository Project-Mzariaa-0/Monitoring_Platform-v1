import { desc, eq, inArray, and, sql } from "drizzle-orm";
import { db } from "../db/client";
import { sessions, cowProcesses, taskEvents, reports, auditLog, supervisors, employees } from "../db/schema";
import { TASK_LABELS } from "../constants";
import { isDuplicateTaskEvent } from "./event-dedupe";

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
  completion_percentage: number;
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

function collectErrorMessages(error: unknown): string[] {
  const messages: string[] = [];
  let current: any = error;
  let depth = 0;
  while (current instanceof Error && depth < 5) {
    messages.push(String(current.message ?? "").toLowerCase());
    current = current.cause;
    depth += 1;
  }
  return messages;
}

function isMissingCompletionPercentageColumn(error: unknown): boolean {
  const messages = collectErrorMessages(error);
  return messages.some(
    (message) =>
      message.includes("completion_percentage") &&
      (message.includes("does not exist") ||
        message.includes("unknown column") ||
        message.includes("no such column")),
  );
}

/**
 * Close any `in_progress` cow processes belonging to already-`completed`
 * sessions (e.g. via the 30-min auto-complete). Without this, completed
 * sessions keep showing cows as `in_progress` with N/A end time.
 */
async function finalizeStaleCowProcesses(): Promise<void> {
  try {
    await db.execute(sql`
      update cow_processes cp
      set
        detected_end_time = coalesce(cp.detected_end_time, s.estimated_end_time, now()),
        overall_status = case
          when exists (
            select 1 from task_events te
            where te.cow_process_id = cp.id and (te.status = 'missed' or te.override_status = 'missed')
          ) then 'completed_with_missed_tasks'
          else 'completed'
        end,
        updated_at = now()
      from sessions s
      where cp.session_id = s.id
        and s.status in ('completed', 'ended_early')
        and cp.overall_status = 'in_progress'
    `);
  } catch {
    /* table may not exist yet */
  }
}

export async function listSessions(): Promise<SessionRecord[]> {
  const now = new Date().toISOString();

  // Auto-complete sessions 30 minutes after their estimated end time
  await db
    .update(sessions)
    .set({ status: "completed", actual_end_time: sessions.estimated_end_time, updated_at: new Date() })
    .where(and(inArray(sessions.status, ["scheduled", "active"]), sql`${sessions.estimated_end_time} + interval '30 minutes' < ${now}`));

  await finalizeStaleCowProcesses();

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

export async function listActiveSessions(): Promise<SessionRecord[]> {
  const now = new Date().toISOString();

  try {
    await db
      .update(sessions)
      .set({ status: "completed", actual_end_time: sessions.estimated_end_time, updated_at: new Date() })
      .where(and(inArray(sessions.status, ["scheduled", "active"]), sql`${sessions.estimated_end_time} + interval '30 minutes' < ${now}`));
  } catch { /* table may not exist */ }

  let rows: any[] = [];
  try {
    rows = await db
      .select()
      .from(sessions)
      .where(inArray(sessions.status, ["scheduled", "active"]))
      .orderBy(desc(sessions.scheduled_start_time));
  } catch { /* table may not exist */ }

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
  const now = new Date().toISOString();

  // Auto-complete 30 minutes after estimated end time
  try {
    await db
      .update(sessions)
      .set({ status: "completed", actual_end_time: sessions.estimated_end_time, updated_at: new Date() })
      .where(and(inArray(sessions.status, ["scheduled", "active"]), sql`${sessions.estimated_end_time} + interval '30 minutes' < ${now}`));
    await finalizeStaleCowProcesses();
  } catch { /* table may not exist */ }

  let row: any = null;
  try {
    [row] = await db.select().from(sessions).where(eq(sessions.id, sessionId)).limit(1);
  } catch { /* table may not exist */ }
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

  let cowRows: any[] = [];
  try { cowRows = await db.select().from(cowProcesses).where(eq(cowProcesses.session_id, sessionId)).orderBy(cowProcesses.cow_position); } catch { /* table may not exist */ }
  const cowProcessesRecords: CowProcessRecord[] = cowRows.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    cow_position: Number(r.cow_position) as 1 | 2,
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    overall_status: r.overall_status as CowProcessRecord["overall_status"],
  }));

  const cowIds = cowProcessesRecords.map((c) => c.id);
  let taskRows: any[] = [];
  if (cowIds.length > 0) {
    try {
      taskRows = await db.select().from(taskEvents).where(inArray(taskEvents.cow_process_id, cowIds)).orderBy(taskEvents.created_at);
    } catch (error) {
      if (isMissingCompletionPercentageColumn(error)) {
        const cowIdList = sql.join(cowIds.map((id) => sql`${id}::uuid`), sql`, `);
        const fallback = await db.execute(sql`
          select
            id,
            cow_process_id,
            task_id,
            detected_start_time,
            detected_end_time,
            duration_seconds,
            status,
            override_status,
            override_reason,
            overridden_by,
            overridden_at,
            created_at
          from task_events
          where cow_process_id in (${cowIdList})
          order by created_at
        `);
        taskRows = (fallback as { rows?: any[] }).rows ?? [];
      } else {
        console.error(`[store] Failed to load task events for session ${sessionId}:`, error);
      }
    }
  }
  const taskEventsRecords: TaskEventRecord[] = taskRows.map((r) => ({
    id: r.id,
    cow_process_id: r.cow_process_id,
    task_id: r.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    duration_seconds: Number(r.duration_seconds),
    status: r.status as TaskEventRecord["status"],
    completion_percentage: Number(r.completion_percentage ?? 0),
    override_status: (r.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: r.override_reason ?? undefined,
    overridden_by: r.overridden_by ?? undefined,
    overridden_at: toISO(r.overridden_at) ?? undefined,
  }));

  let reportRows: any[] = [];
  try { reportRows = await db.select().from(reports).where(eq(reports.session_id, sessionId)).orderBy(desc(reports.generated_at)); } catch { /* table may not exist */ }
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
  const updated = await db.transaction(async (tx) => {
    const [updatedSession] = await tx
      .update(sessions)
      .set({
        employee_id: employeeId,
        employee_name: employeeName,
        updated_at: new Date(),
      })
      .where(eq(sessions.id, sessionId))
      .returning();

    if (!updatedSession) return null;

    await tx.insert(auditLog).values({
      entity_type: "Session",
      entity_id: sessionId,
      action: "employee_reassigned",
      actor_id: actorId,
      reason: null,
      details: { employee_id: employeeId, employee_name: employeeName },
      created_at: new Date(),
    });

    return updatedSession;
  });

  if (!updated) return null;

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

export async function updateSessionStatus(
  sessionId: string,
  status: string,
  actorId = "inference-service",
): Promise<SessionRecord | null> {
  const updated = await db.transaction(async (tx) => {
    const [session] = await tx
      .select({ status: sessions.status })
      .from(sessions)
      .where(eq(sessions.id, sessionId))
      .limit(1);

    const setValues: Record<string, unknown> = { status, updated_at: new Date() };
    if (status === "completed" || status === "ended_early") {
      setValues.actual_end_time = new Date();
    }

    const [updatedSession] = await tx
      .update(sessions)
      .set(setValues)
      .where(eq(sessions.id, sessionId))
      .returning();

    if (!updatedSession) return null;

    if (status === "completed" || status === "ended_early") {
      const sessionCows = await tx
        .select()
        .from(cowProcesses)
        .where(eq(cowProcesses.session_id, sessionId));
      const cowIds = sessionCows.map((c) => c.id);
      let existingTasks: { cow_process_id: string; task_id: string; status: string }[] = [];
      if (cowIds.length > 0) {
        existingTasks = await tx
          .select({ cow_process_id: taskEvents.cow_process_id, task_id: taskEvents.task_id, status: taskEvents.status })
          .from(taskEvents)
          .where(inArray(taskEvents.cow_process_id, cowIds));
      }
      const seen = new Set(existingTasks.map((t) => `${t.cow_process_id}:${t.task_id}`));
      const now = new Date();
      for (const cow of sessionCows) {
        let missedCount = 0;
        // Only backfill missed tasks for cows that produced at least one real
        // task event. A lone "started" boundary signal with zero task events
        // is usually a false detection — fabricating 6x N/A rows for it
        // produces the duplicate Row-2 tables. Untouched positions are simply
        // closed below with no fake rows.
        const cowHadEvents = existingTasks.some((t) => t.cow_process_id === cow.id);
        if (cowHadEvents) {
          for (const taskId of Object.keys(TASK_LABELS)) {
            if (!seen.has(`${cow.id}:${taskId}`)) {
              missedCount += 1;
              await tx.insert(taskEvents).values({
                cow_process_id: cow.id,
                task_id: taskId,
                detected_start_time: null,
                detected_end_time: null,
                duration_seconds: 0,
                status: "missed",
                confidence_score: 0,
                completion_percentage: 0,
                override_status: null,
                override_reason: null,
                overridden_by: null,
                overridden_at: null,
                created_at: now,
              });
            }
          }
        }
        const cowTasks = existingTasks.filter((t) => t.cow_process_id === cow.id);
        const hasMissed = cowTasks.some((t) => t.status === "missed") || missedCount > 0;
        await tx
          .update(cowProcesses)
          .set({
            detected_end_time: cow.detected_end_time ?? now,
            overall_status: hasMissed ? "completed_with_missed_tasks" : "completed",
            updated_at: now,
          })
          .where(eq(cowProcesses.id, cow.id));
      }
    }

    await tx.insert(auditLog).values({
      entity_type: "Session",
      entity_id: sessionId,
      action: "status_changed",
      actor_id: actorId,
      reason: null,
      details: { previous_status: session?.status ?? null, status },
      created_at: new Date(),
    });

    return updatedSession;
  });

  if (!updated) return null;

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

export async function updateCowProcess(
  sessionId: string,
  cowPosition: 1 | 2,
  processStatus: "started" | "completed" | undefined,
  detectedTime: string | undefined,
): Promise<void> {
  const [cow] = await db
    .select()
    .from(cowProcesses)
    .where(and(eq(cowProcesses.session_id, sessionId), eq(cowProcesses.cow_position, cowPosition)))
    .limit(1);

  if (!cow) return;

  const time = detectedTime ? new Date(detectedTime) : new Date();

  if (processStatus === "started") {
    await db
      .update(cowProcesses)
      .set({ detected_start_time: time, overall_status: "in_progress", updated_at: new Date() })
      .where(eq(cowProcesses.id, cow.id));
  } else if (processStatus === "completed") {
    await db
      .update(cowProcesses)
      .set({ detected_end_time: time, overall_status: "completed", updated_at: new Date() })
      .where(eq(cowProcesses.id, cow.id));
  }
}

export async function ingestTaskEvent(input: {
  session_id: string;
  cow_position: 1 | 2;
  task_id: TaskEventRecord["task_id"];
  status: TaskEventRecord["status"];
  confidence_score?: number;
  completion_percentage?: number;
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
  if (!cow) {
    console.warn(
      `[store] Task event dropped: no cow process for session=${input.session_id} position=${input.cow_position} task=${input.task_id}`,
    );
    return null;
  }

  const detectedStart = input.detected_start_time ?? null;
  const detectedEnd = input.detected_end_time ?? null;

  const existingTaskEvents = await db
    .select()
    .from(taskEvents)
    .where(eq(taskEvents.cow_process_id, cow.id))
    .orderBy(taskEvents.created_at);

  const duplicateCandidate = existingTaskEvents.find((row) =>
    isDuplicateTaskEvent(
      {
        session_id: input.session_id,
        cow_position: input.cow_position,
        task_id: input.task_id,
        status: input.status,
        detected_start_time: detectedStart,
        detected_end_time: detectedEnd,
      },
      {
        session_id: input.session_id,
        cow_position: input.cow_position,
        task_id: row.task_id,
        status: row.status,
        detected_start_time: toISO(row.detected_start_time),
        detected_end_time: toISO(row.detected_end_time),
      },
    ),
  );

  if (duplicateCandidate) {
    return {
      id: duplicateCandidate.id,
      cow_process_id: duplicateCandidate.cow_process_id,
      task_id: duplicateCandidate.task_id as TaskEventRecord["task_id"],
      detected_start_time: toISO(duplicateCandidate.detected_start_time),
      detected_end_time: toISO(duplicateCandidate.detected_end_time),
      duration_seconds: Number(duplicateCandidate.duration_seconds),
      status: duplicateCandidate.status as TaskEventRecord["status"],
      completion_percentage: Number(duplicateCandidate.completion_percentage ?? 0),
      override_status: (duplicateCandidate.override_status as TaskEventRecord["override_status"]) ?? undefined,
      override_reason: duplicateCandidate.override_reason ?? undefined,
      overridden_by: duplicateCandidate.overridden_by ?? undefined,
      overridden_at: duplicateCandidate.overridden_at ? toISO(duplicateCandidate.overridden_at) ?? undefined : undefined,
    };
  }

  let inserted: any;
  try {
    [inserted] = await db
      .insert(taskEvents)
      .values({
        cow_process_id: cow.id,
        task_id: input.task_id,
        detected_start_time: detectedStart ? new Date(detectedStart) : null,
        detected_end_time: detectedEnd ? new Date(detectedEnd) : null,
        duration_seconds: input.duration_seconds ?? 0,
        status: input.status,
        confidence_score: Number(input.confidence_score ?? 0),
        completion_percentage: Number(input.completion_percentage ?? 0),
        override_status: null,
        override_reason: null,
        overridden_by: null,
        overridden_at: null,
        created_at: new Date(),
      })
      .returning();
  } catch (error) {
    if (!isMissingCompletionPercentageColumn(error)) {
      throw error;
    }

    const fallbackInserted = await db.execute(sql`
      insert into task_events (
        cow_process_id,
        task_id,
        detected_start_time,
        detected_end_time,
        duration_seconds,
        status,
        confidence_score,
        override_status,
        override_reason,
        overridden_by,
        overridden_at,
        created_at
      ) values (
        ${cow.id}::uuid,
        ${input.task_id},
        ${detectedStart ? new Date(detectedStart) : null},
        ${detectedEnd ? new Date(detectedEnd) : null},
        ${input.duration_seconds ?? 0},
        ${input.status},
        ${Number(input.confidence_score ?? 0)},
        ${null},
        ${null},
        ${null},
        ${null},
        ${new Date()}
      )
      returning
        id,
        cow_process_id,
        task_id,
        detected_start_time,
        detected_end_time,
        duration_seconds,
        status,
        override_status,
        override_reason,
        overridden_by,
        overridden_at
    `);
      inserted = (fallbackInserted as { rows?: any[] }).rows?.[0];
  }

  if (!inserted) return null;

  // Cow process boundaries: TASK-03 (attachment) opens, TASK-05/06 closes.
  // Previously only `completed` closed the process, so any missed/anomaly run
  // left cows stuck at `in_progress` with N/A end time forever.
  if (input.task_id === "TASK-03" && !cow.detected_start_time) {
    const startTime = detectedStart ? new Date(detectedStart) : new Date();
    await db.update(cowProcesses).set({ detected_start_time: startTime, overall_status: "in_progress", updated_at: new Date() }).where(eq(cowProcesses.id, cow.id));
  }
  if (input.task_id === "TASK-01" && !cow.detected_start_time) {
    const startTime = detectedStart ? new Date(detectedStart) : new Date();
    await db.update(cowProcesses).set({ detected_start_time: startTime, overall_status: "in_progress", updated_at: new Date() }).where(eq(cowProcesses.id, cow.id));
  }
  if (input.task_id === "TASK-05" || input.task_id === "TASK-06") {
    const endTime = detectedEnd ? new Date(detectedEnd) : new Date();
    const closedStatus = input.status === "completed" ? "completed" : "completed_with_missed_tasks";
    await db
      .update(cowProcesses)
      .set({ detected_end_time: endTime, overall_status: closedStatus, updated_at: new Date() })
      .where(eq(cowProcesses.id, cow.id));
  }

  return {
    id: inserted.id,
    cow_process_id: inserted.cow_process_id,
    task_id: inserted.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(inserted.detected_start_time),
    detected_end_time: toISO(inserted.detected_end_time),
    duration_seconds: Number(inserted.duration_seconds),
    status: inserted.status as TaskEventRecord["status"],
    completion_percentage: Number(inserted.completion_percentage ?? 0),
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
  const updated = await db.transaction(async (tx) => {
    const [previousEvent] = await tx
      .select({ status: taskEvents.status, override_status: taskEvents.override_status })
      .from(taskEvents)
      .where(eq(taskEvents.id, taskEventId))
      .limit(1);

    const [updatedEvent] = await tx
      .update(taskEvents)
      .set({
        override_status: overrideStatus,
        override_reason: reason,
        overridden_by: actorId,
        overridden_at: new Date(),
      })
      .where(eq(taskEvents.id, taskEventId))
      .returning();

    if (!updatedEvent) return null;

    await tx.insert(auditLog).values({
      entity_type: "TaskEvent",
      entity_id: taskEventId,
      action: "task_override",
      actor_id: actorId,
      reason,
      details: {
        override_status: overrideStatus,
        previous_status: previousEvent?.status ?? null,
        previous_override_status: previousEvent?.override_status ?? null,
      },
      created_at: new Date(),
    });

    return updatedEvent;
  });

  if (!updated) return null;

  return {
    id: updated.id,
    cow_process_id: updated.cow_process_id,
    task_id: updated.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(updated.detected_start_time),
    detected_end_time: toISO(updated.detected_end_time),
    duration_seconds: Number(updated.duration_seconds),
    status: updated.status as TaskEventRecord["status"],
    completion_percentage: Number(updated.completion_percentage ?? 0),
    override_status: (updated.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: updated.override_reason ?? undefined,
    overridden_by: updated.overridden_by ?? undefined,
    overridden_at: updated.overridden_at ? toISO(updated.overridden_at) ?? undefined : undefined,
  };
}

export async function createReport(sessionId: string, docxFileUrl: string | null): Promise<ReportRecord> {
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
    docx_file_url: inserted.docx_file_url ?? "",
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
  let sessionRows: any[] = [];
  try { sessionRows = await db.select().from(sessions); } catch { /* table may not exist */ }
  const totalSessions = sessionRows.length;
  const completedSessions = sessionRows.filter((s) => s.status === "completed").length;

  let taskRows: any[] = [];
  try { taskRows = await db.select().from(taskEvents); } catch { /* table may not exist */ }
  const missedCount = taskRows.filter((t) => t.status === "missed" || t.override_status === "missed").length;
  const averageDuration = taskRows.length === 0 ? 0 : Math.round(taskRows.reduce((sum, t) => sum + Number(t.duration_seconds), 0) / taskRows.length);

  let reportRows: any[] = [];
  try { reportRows = await db.select().from(reports).orderBy(desc(reports.generated_at)); } catch { /* table may not exist */ }
  const reportsRecords: ReportRecord[] = reportRows.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    generated_at: toISO(r.generated_at) ?? "",
    docx_file_url: r.docx_file_url,
    email_sent_at: toISO(r.email_sent_at),
  }));

  return { totalSessions, completedSessions, missedCount, averageDuration, reports: reportsRecords };
}

export type ModelHealthOverview = {
  totalEvents: number;
  averageConfidence: number;
  lowConfidenceRate: number;
  tasks: Array<{
    taskId: string;
    eventCount: number;
    averageConfidence: number;
    lowConfidenceCount: number;
    missedCount: number;
  }>;
};

export type OperationalAlert = {
  id: string;
  level: "critical" | "warning" | "info";
  title: string;
  detail: string;
  source: "database" | "inference" | "model" | "compliance";
};

export async function getModelHealthOverview(): Promise<ModelHealthOverview> {
  let rows: any[] = [];
  try {
    rows = await db.select({
      taskId: taskEvents.task_id,
      status: taskEvents.status,
      confidenceScore: taskEvents.confidence_score,
    }).from(taskEvents);
  } catch {
    return { totalEvents: 0, averageConfidence: 0, lowConfidenceRate: 0, tasks: [] };
  }

  const grouped = new Map<string, { confidenceTotal: number; lowConfidenceCount: number; missedCount: number; eventCount: number }>();
  for (const row of rows) {
    const task = grouped.get(row.taskId) ?? { confidenceTotal: 0, lowConfidenceCount: 0, missedCount: 0, eventCount: 0 };
    const confidence = Number(row.confidenceScore ?? 0);
    task.eventCount += 1;
    task.confidenceTotal += confidence;
    if (confidence < 0.7) task.lowConfidenceCount += 1;
    if (row.status === "missed") task.missedCount += 1;
    grouped.set(row.taskId, task);
  }

  const tasks = [...grouped.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([taskId, task]) => ({
    taskId,
    eventCount: task.eventCount,
    averageConfidence: task.eventCount === 0 ? 0 : task.confidenceTotal / task.eventCount,
    lowConfidenceCount: task.lowConfidenceCount,
    missedCount: task.missedCount,
  }));
  const totalEvents = rows.length;
  const lowConfidenceCount = tasks.reduce((total, task) => total + task.lowConfidenceCount, 0);
  const confidenceTotal = tasks.reduce((total, task) => total + task.averageConfidence * task.eventCount, 0);

  return {
    totalEvents,
    averageConfidence: totalEvents === 0 ? 0 : confidenceTotal / totalEvents,
    lowConfidenceRate: totalEvents === 0 ? 0 : lowConfidenceCount / totalEvents,
    tasks,
  };
}

export async function getOperationalAlerts(): Promise<OperationalAlert[]> {
  const alerts: OperationalAlert[] = [];

  try {
    await db.execute(sql`select 1`);
  } catch {
    alerts.push({
      id: "database-unavailable",
      level: "critical",
      title: "Database unavailable",
      detail: "The monitoring database health check failed. Persistence and reporting may be stale.",
      source: "database",
    });
  }

  const modelHealth = await getModelHealthOverview();
  if (modelHealth.totalEvents >= 5 && modelHealth.lowConfidenceRate >= 0.3) {
    alerts.push({
      id: "model-low-confidence",
      level: "warning",
      title: "Model confidence is degrading",
      detail: `${Math.round(modelHealth.lowConfidenceRate * 100)}% of recent task events are below the confidence review threshold.`,
      source: "model",
    });
  }

  const inferenceUrl = process.env.INFERENCE_SERVICE_URL || "http://localhost:8001";
  try {
    const response = await fetch(`${inferenceUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) {
      alerts.push({
        id: "inference-unhealthy",
        level: "critical",
        title: "Inference service unhealthy",
        detail: `Health endpoint returned HTTP ${response.status}.`,
        source: "inference",
      });
    }
  } catch {
    alerts.push({
      id: "inference-unreachable",
      level: "critical",
      title: "Inference service unreachable",
      detail: "The web app could not reach the inference health endpoint.",
      source: "inference",
    });
  }

  const overview = await getMonitoringOverview();
  for (const task of overview.activeTaskEvents.filter((event) => event.status === "missed" || event.override_status === "missed")) {
    alerts.push({
      id: `missed-task-${task.id}`,
      level: task.override_status ? "warning" : "critical",
      title: `${task.task_id} missed`,
      detail: "Review the task evidence and override if the event is unverifiable.",
      source: "compliance",
    });
  }

  return alerts;
}

export async function getMonitoringOverview(): Promise<{
  activeSession: SessionRecord | null;
  activeCowProcesses: CowProcessRecord[];
  activeTaskEvents: TaskEventRecord[];
  totalSessions: number;
  activeCount: number;
  missedCount: number;
}> {
  const now = new Date().toISOString();

  // Auto-complete sessions 30 minutes after their estimated end time
  try {
    await db
      .update(sessions)
      .set({ status: "completed", actual_end_time: sessions.estimated_end_time, updated_at: new Date() })
      .where(and(inArray(sessions.status, ["scheduled", "active"]), sql`${sessions.estimated_end_time} + interval '30 minutes' < ${now}`));
    await finalizeStaleCowProcesses();
  } catch { /* table may not exist */ }

  // Start of today in Morocco time, converted to UTC for DB comparison.
  // Since 20 Sep 2026 Morocco is permanent UTC+0, Morocco midnight == UTC midnight.
  // (Older Node tzdata still returns +1, so we bypass Intl for post-cutover dates.)
  const nowMs = Date.now();
  const MOROCCO_CUTOVER = Date.UTC(2026, 8, 20, 1, 0, 0);
  let todayStart: Date;
  if (nowMs >= MOROCCO_CUTOVER) {
    const n = new Date();
    todayStart = new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate(), 0, 0, 0));
  } else {
    const moroccoToday = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Africa/Casablanca",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    todayStart = new Date(`${moroccoToday}T00:00:00+00:00`);
    {
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(moroccoToday);
      if (match) {
        const targetUtc = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 0, 0);
        let candidate = targetUtc;
        for (let i = 0; i < 3; i += 1) {
          const parts = new Intl.DateTimeFormat("en", {
            timeZone: "Africa/Casablanca",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
          })
            .formatToParts(new Date(candidate))
            .reduce<Record<string, string>>((acc, p) => {
              acc[p.type] = p.value;
              return acc;
            }, {});
          const displayedUtc = Date.UTC(
            Number(parts.year),
            Number(parts.month) - 1,
            Number(parts.day),
            Number(parts.hour),
            Number(parts.minute),
          );
          const targetWall = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 0, 0);
          const diff = targetWall - displayedUtc;
          candidate += diff;
          if (diff === 0) break;
        }
        todayStart.setTime(candidate);
      }
    }
  }

  let totalSessionRows: any[] = [];
  try { totalSessionRows = await db.select().from(sessions).where(sql`${sessions.created_at} >= ${todayStart}`); } catch { /* table may not exist */ }
  const totalSessions = totalSessionRows.length;
  const activeCount = totalSessionRows.filter((s) => s.status === "active" || s.status === "scheduled").length;

  let activeSessionRow: any = null;
  try {
    activeSessionRow = (await db.select().from(sessions).where(inArray(sessions.status, ["active", "scheduled"])).orderBy(desc(sessions.updated_at)).limit(1)).at(0) ?? null;
  } catch { /* table may not exist */ }

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

  let activeCowProcessesRaw: any[] = [];
  if (activeSession) {
    try {
      activeCowProcessesRaw = await db
        .select()
        .from(cowProcesses)
        .where(eq(cowProcesses.session_id, activeSession.id))
        .orderBy(cowProcesses.cow_position);
    } catch { /* table may not exist */ }
  }
  const activeCowProcesses: CowProcessRecord[] = activeCowProcessesRaw.map((r) => ({
    id: r.id,
    session_id: r.session_id,
    cow_position: Number(r.cow_position) as 1 | 2,
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    overall_status: r.overall_status as CowProcessRecord["overall_status"],
  }));

  const cowIds = activeCowProcesses.map((c) => c.id);
  let activeTaskEventsRaw: any[] = [];
  if (cowIds.length > 0) {
    try {
      activeTaskEventsRaw = await db.select().from(taskEvents).where(inArray(taskEvents.cow_process_id, cowIds)).orderBy(taskEvents.created_at);
    } catch (error) {
      console.error(`[store] Failed to load task events for active session ${activeSession?.id}:`, error);
    }
  }
  const activeTaskEvents: TaskEventRecord[] = activeTaskEventsRaw.map((r) => ({
    id: r.id,
    cow_process_id: r.cow_process_id,
    task_id: r.task_id as TaskEventRecord["task_id"],
    detected_start_time: toISO(r.detected_start_time),
    detected_end_time: toISO(r.detected_end_time),
    duration_seconds: Number(r.duration_seconds),
    status: r.status as TaskEventRecord["status"],
    completion_percentage: Number(r.completion_percentage ?? 0),
    override_status: (r.override_status as TaskEventRecord["override_status"]) ?? undefined,
    override_reason: r.override_reason ?? undefined,
    overridden_by: r.overridden_by ?? undefined,
    overridden_at: r.overridden_at ? toISO(r.overridden_at) ?? undefined : undefined,
  }));

  let taskRows: any[] = [];
  try { taskRows = await db.select().from(taskEvents); } catch { /* table may not exist */ }
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
    completion_percentage: Number((row as any).completion_percentage ?? 0),
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
  let allSessions: any[] = [];
  let allCowProcesses: any[] = [];
  let allTaskEvents: any[] = [];
  try { allSessions = await db.select().from(sessions); } catch { /* table may not exist */ }
  try { allCowProcesses = await db.select().from(cowProcesses); } catch { /* table may not exist */ }
  try { allTaskEvents = await db.select().from(taskEvents); } catch { /* table may not exist */ }

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
  let allTaskEvents: any[] = [];
  try { allTaskEvents = await db.select().from(taskEvents); } catch { /* table may not exist */ }

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
