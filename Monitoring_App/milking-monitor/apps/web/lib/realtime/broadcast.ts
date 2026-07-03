type EventPayload = {
  session_id: string;
  type: string;
  payload: Record<string, unknown>;
};

const subscribers = new Map<string, Set<ReadableStreamDefaultController<string>>>();
const history = new Map<string, EventPayload[]>();

export function subscribe(sessionId: string, controller: ReadableStreamDefaultController<string>) {
  const nextSubscribers = subscribers.get(sessionId) ?? new Set<ReadableStreamDefaultController<string>>();
  nextSubscribers.add(controller);
  subscribers.set(sessionId, nextSubscribers);

  for (const event of history.get(sessionId) ?? []) {
    controller.enqueue(`data: ${JSON.stringify(event)}\n\n`);
  }
}

export function unsubscribe(sessionId: string, controller: ReadableStreamDefaultController<string>) {
  const nextSubscribers = subscribers.get(sessionId);
  if (!nextSubscribers) {
    return;
  }

  nextSubscribers.delete(controller);
  if (nextSubscribers.size === 0) {
    subscribers.delete(sessionId);
  }
}

export function publish(sessionId: string, event: EventPayload) {
  const nextHistory = history.get(sessionId) ?? [];
  nextHistory.push(event);
  history.set(sessionId, nextHistory.slice(-100));

  for (const controller of subscribers.get(sessionId) ?? []) {
    controller.enqueue(`data: ${JSON.stringify(event)}\n\n`);
  }
}
