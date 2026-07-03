import MultiStepSessionForm from "../../../../components/forms/multi-step-session-form";

export default function NewSessionPage() {
  return (
    <div className="page-grid">
      <section className="card card-pad">
        <h1 className="section-title" style={{ fontSize: 22 }}>
          New session
        </h1>
        <MultiStepSessionForm />
      </section>
    </div>
  );
}
