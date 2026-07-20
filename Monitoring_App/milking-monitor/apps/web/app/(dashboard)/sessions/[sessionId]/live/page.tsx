import LiveSessionBanner from "../../../../../components/dashboard/live-session-banner";
import LiveSessionStream from "../../../../../components/dashboard/live-session-stream";
import TaskChecklist from "../../../../../components/dashboard/task-checklist";
import { getSessionDetails } from "../../../../../lib/data/store";

export default async function LiveSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const details = await getSessionDetails(sessionId);
  const session = details?.session;
  const initialEvents = details
    ? details.taskEvents.map((taskEvent) => ({
        session_id: sessionId,
        type: taskEvent.status,
        payload: {
          task_id: taskEvent.task_id,
          cow_process_id: taskEvent.cow_process_id,
          status: taskEvent.status,
          duration_seconds: taskEvent.duration_seconds,
          detected_start_time: taskEvent.detected_start_time,
          detected_end_time: taskEvent.detected_end_time,
        },
      }))
    : [];

  const isActive = session?.status === "active" || session?.status === "scheduled";
  const cowCount = details?.cowProcesses?.length ?? 0;

  return (
    <div className="page-grid">
      <LiveSessionBanner
        sessionId={sessionId}
        operator={session?.employee_name ?? undefined}
        active={isActive}
        scheduledStart={session?.scheduled_start_time ?? undefined}
        estimatedEnd={session?.estimated_end_time ?? undefined}
        cowCount={cowCount}
      />
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Live session {sessionId.slice(0, 8)}
        </h1>
        <p className="muted">
          {session?.employee_name ?? "Unassigned operator"} · {session?.status ?? "unknown"}
        </p>
      </section>
      <LiveSessionStream sessionId={sessionId} initialEvents={initialEvents} />
      <TaskChecklist sessionId={sessionId} taskEvents={details?.taskEvents ?? []} />
    </div>
  );
}
