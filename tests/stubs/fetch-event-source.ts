/**
 * Stub implementation of ``@microsoft/fetch-event-source`` for Vitest. Unit tests
 * inject their own EventSource factory so the real network implementation is never
 * exercised. Returning an immediately resolved promise keeps behaviour deterministic.
 */
export interface EventSourceMessage {
  readonly event?: string;
  readonly data?: string;
}

export interface FetchEventSourceInit {
  readonly method?: string;
  readonly headers?: Record<string, string>;
  readonly signal?: AbortSignal;
  readonly onmessage?: (message: EventSourceMessage) => void;
  readonly onerror?: (error: unknown) => void;
}

export async function fetchEventSource(_url: string, init?: FetchEventSourceInit): Promise<void> {
  // Invoke the callbacks synchronously to emulate the control flow of the real
  // library without performing any network I/O.
  if (init?.onmessage) {
    init.onmessage({ event: "ready", data: "" });
  }
}
