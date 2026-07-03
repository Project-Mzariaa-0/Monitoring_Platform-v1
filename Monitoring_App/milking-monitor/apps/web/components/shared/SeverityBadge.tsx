export default function SeverityBadge({ level }: { level: "critical" | "warning" | "info" }) {
  const colors = {
    critical: "var(--danger)",
    warning: "var(--warning)",
    info: "var(--primary)",
  } as const;

  return (
    <span
      className="button"
      style={{
        padding: "6px 10px",
        fontSize: 12,
        background: colors[level],
        color: "white",
      }}
    >
      {level}
    </span>
  );
}