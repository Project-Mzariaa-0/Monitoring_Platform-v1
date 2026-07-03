"use client";

import { useEffect, useState } from "react";

type Service = {
  name: string;
  url: string;
  type: "api" | "stream" | "model";
};

type ServiceStatus = {
  status: "checking" | "online" | "offline" | "unknown";
  detail: string;
};

export default function EquipmentStatus({ services }: { services: Service[] }) {
  const [statuses, setStatuses] = useState<Map<string, ServiceStatus>>(() => {
    const initial = new Map<string, ServiceStatus>();
    for (const service of services) {
      if (service.type === "stream" || service.type === "model") {
        initial.set(service.name, {
          status: service.url === "Not configured" ? "offline" : "unknown",
          detail: service.url === "Not configured" ? "Not configured" : "Manual check required",
        });
      } else {
        initial.set(service.name, { status: "checking", detail: "Checking..." });
      }
    }
    return initial;
  });

  useEffect(() => {
    const controllers: AbortController[] = [];

    for (const service of services) {
      if (service.type === "stream" || service.type === "model") {
        continue;
      }

      const controller = new AbortController();
      controllers.push(controller);
      const timeout = setTimeout(() => controller.abort(), 5000);

      fetch(service.url, { method: "GET", signal: controller.signal })
        .then(() => {
          if (!controller.signal.aborted) {
            setStatuses((prev) => {
              const next = new Map(prev);
              next.set(service.name, { status: "online", detail: "Reachable" });
              return next;
            });
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setStatuses((prev) => {
              const next = new Map(prev);
              next.set(service.name, { status: "offline", detail: "Unreachable" });
              return next;
            });
          }
        })
        .finally(() => clearTimeout(timeout));
    }

    return () => {
      controllers.forEach((c) => c.abort());
    };
  }, [services]);

  return (
    <div className="rail-list">
      {services.map((service) => {
        const st = statuses.get(service.name);
        const status = st?.status ?? "checking";
        const pillClass =
          status === "online"
            ? "status-success"
            : status === "offline"
              ? "status-danger"
              : status === "checking"
                ? "status-warning"
                : "status-neutral";

        return (
          <div className="data-row" key={service.name}>
            <div>
              <strong>{service.name}</strong>
              <div className="muted" style={{ fontSize: 13 }}>
                {st?.detail ?? service.url}
              </div>
            </div>
            <span className={`status-tag ${pillClass}`}>
              {status === "checking" ? "Checking..." : status === "online" ? "Online" : status === "offline" ? "Offline" : "Unknown"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
