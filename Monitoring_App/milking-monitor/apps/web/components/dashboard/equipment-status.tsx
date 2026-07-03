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
  const [statuses, setStatuses] = useState<Map<string, ServiceStatus>>(new Map());

  useEffect(() => {
    for (const service of services) {
      if (service.type === "stream" || service.type === "model") {
        setStatuses((prev) => {
          const next = new Map(prev);
          next.set(service.name, {
            status: service.url === "Not configured" ? "offline" : "unknown",
            detail: service.url === "Not configured" ? "Not configured" : "Manual check required",
          });
          return next;
        });
        continue;
      }

      setStatuses((prev) => {
        const next = new Map(prev);
        next.set(service.name, { status: "checking", detail: "Checking..." });
        return next;
      });

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      fetch(service.url, { method: "HEAD", signal: controller.signal, mode: "no-cors" })
        .then(() => {
          setStatuses((prev) => {
            const next = new Map(prev);
            next.set(service.name, { status: "online", detail: "Reachable" });
            return next;
          });
        })
        .catch(() => {
          setStatuses((prev) => {
            const next = new Map(prev);
            next.set(service.name, { status: "offline", detail: "Unreachable" });
            return next;
          });
        })
        .finally(() => clearTimeout(timeout));
    }
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
            <span className={`status-pill ${pillClass}`}>
              {status === "checking" ? "Checking..." : status === "online" ? "Online" : status === "offline" ? "Offline" : "Unknown"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
