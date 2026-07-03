import LiveSessionBanner from "../../../../../components/dashboard/live-session-banner";
import LiveSessionStream from "../../../../../components/dashboard/live-session-stream";
import TaskChecklist from "../../../../../components/dashboard/task-checklist";
import { getSessionDetails } from "../../../../../lib/data/store";

export default async function LiveSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const details = await getSessionDetails(sessionId);
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

  return (
    <div className="page-grid">
      <LiveSessionBanner />
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          Live session {sessionId}
        </h1>
        <p className="muted">
          {details?.session.employee_name ?? "Assigned employee"} · {details?.session.status ?? "unknown"}
        </p>
      </section>
      <LiveSessionStream sessionId={sessionId} initialEvents={initialEvents} />
      <TaskChecklist sessionId={sessionId} taskEvents={details?.taskEvents ?? []} />
    </div>
  );
}
