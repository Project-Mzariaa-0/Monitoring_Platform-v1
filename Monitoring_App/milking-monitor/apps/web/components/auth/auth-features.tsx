export function AuthFeatures() {
  const features = [
    {
      icon: "📊",
      title: "Real-time Monitoring",
      description: "Track compliance across all positions live"
    },
    {
      icon: "⚡",
      title: "Instant Alerts",
      description: "Get notified of deviations immediately"
    },
    {
      icon: "✓",
      title: "99.2% Accuracy",
      description: "AI-powered detection you can trust"
    },
    {
      icon: "📋",
      title: "Complete Audit Trail",
      description: "Every session logged and documented"
    }
  ];

  return (
    <div className="auth-features">
      {features.map((feature, index) => (
        <div key={index} className="feature-item">
          <div className="feature-icon">{feature.icon}</div>
          <div className="feature-content">
            <h3 className="feature-title">{feature.title}</h3>
            <p className="feature-desc">{feature.description}</p>
          </div>
          <div className="feature-check">✓</div>
        </div>
      ))}
    </div>
  );
}
