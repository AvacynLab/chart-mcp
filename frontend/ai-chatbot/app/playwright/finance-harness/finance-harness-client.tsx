"use client";

import { useEffect, useMemo, useRef } from "react";
import type { DataUIPart } from "ai";
import { DataStreamProvider, useDataStream } from "@/components/data-stream-provider";
import type { CustomUIDataTypes } from "@/lib/types";
import {
  FINANCE_STREAM_FIXTURE,
  type FinanceStreamEvent,
} from "@/lib/test/finance-stream-fixture";

type FinanceDataPart = DataUIPart<CustomUIDataTypes>;

/**
 * Transform a single finance fixture event into the UI data parts emitted by
 * the production finance document handler. The helper mirrors the mapping in
 * `artifacts/finance/server.ts` so the Playwright harness exercises the same
 * client expectations as the live chat surface.
 */
function translateFinanceEvent(event: FinanceStreamEvent): FinanceDataPart[] {
  const payload = event.payload ?? {};

  switch (event.event) {
    case "step:start":
    case "step:end":
    case "metric":
    case "result_partial":
      return [
        {
          type: "data-finance:step",
          data: {
            event: event.event,
            payload,
          },
        },
      ];
    case "token": {
      const tokenText = typeof payload.text === "string" ? payload.text : "";
      if (!tokenText) {
        return [];
      }
      return [
        {
          type: "data-finance:token",
          data: tokenText,
          transient: true,
        },
      ];
    }
    case "result_final": {
      const parts: FinanceDataPart[] = [];
      if (typeof payload.summary === "string" && payload.summary.length > 0) {
        parts.push({ type: "data-finance:token", data: payload.summary });
      }
      if (payload.levels) {
        parts.push({ type: "data-finance:levels", data: payload.levels });
      }
      if (payload.patterns) {
        parts.push({ type: "data-finance:patterns", data: payload.patterns });
      }
      return parts;
    }
    case "done":
      return [
        {
          type: "data-finish",
          data: null,
          transient: true,
        },
      ];
    case "error":
      return [
        {
          type: "data-error",
          data: payload,
        },
      ];
    default:
      return [
        {
          type: `data-finance:${event.event}` as FinanceDataPart["type"],
          data: payload,
        },
      ];
  }
}

/**
 * Drive the shared finance fixture through the data stream provider, mimicking
 * the cadence of the real SSE connection. The events remain deterministic so
 * the Playwright assertions can synchronise on the lifecycle markers without
 * introducing flaky timeouts.
 */
function FinanceFixtureStreamer(): null {
  const { setDataStream } = useDataStream();
  const timersRef = useRef<number[]>([]);
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (hasStartedRef.current) {
      return;
    }

    hasStartedRef.current = true;
    let cancelled = false;

    FINANCE_STREAM_FIXTURE.forEach((event, index) => {
      const timeoutId = window.setTimeout(() => {
        if (cancelled) {
          return;
        }
        const parts = translateFinanceEvent(event);
        if (!parts.length) {
          return;
        }
        setDataStream((current) => [...current, ...parts]);
      }, index * 35);
      timersRef.current.push(timeoutId);
    });

    return () => {
      cancelled = true;
      timersRef.current.forEach((timeoutId) => {
        window.clearTimeout(timeoutId);
      });
      timersRef.current = [];
    };
  }, [setDataStream]);

  return null;
}

/**
 * Render a concise dashboard that mirrors the key artefact elements the
 * Playwright scenario inspects: heading, streamed summary and lifecycle
 * markers. The component reacts to the provider’s data stream so assertions
 * remain faithful to the production behaviour.
 */
function FinanceHarnessContent(): JSX.Element {
  const { dataStream } = useDataStream();

  const { steps, summary, finishCount } = useMemo(() => {
    const stepParts = dataStream.filter((part) => part.type === "data-finance:step");
    const tokenParts = dataStream.filter((part) => part.type === "data-finance:token");
    const finishEvents = dataStream.filter((part) => part.type === "data-finish");

    return {
      steps: stepParts.map((part) => part.data),
      summary: tokenParts.map((part) => String(part.data ?? "")).join(""),
      finishCount: finishEvents.length,
    };
  }, [dataStream]);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-100">Résumé IA</h1>
        <p className="text-sm text-slate-400">
          Flux de test Playwright — les évènements financiers synthétiques sont rejoués pour
          valider la cartographie des données côté UI.
        </p>
      </header>

      <section
        aria-label="Résumé du flux finance"
        data-testid="artifact"
        className="rounded-lg border border-slate-800 bg-slate-950 p-5 text-slate-200 shadow-lg"
      >
        <p>{summary || "En attente des tokens du flux finance…"}</p>
      </section>

      <section className="rounded-lg border border-slate-800 bg-slate-950 p-5 text-slate-300">
        <h2 className="text-lg font-medium text-slate-100">Évènements</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {steps.map((step, index) => (
            <li key={`step-${index}`} className="flex flex-col rounded-md bg-slate-900 p-3">
              <span className="font-semibold text-slate-100">{step?.event ?? "?"}</span>
              <code className="mt-2 whitespace-pre-wrap text-xs text-slate-400">
                {JSON.stringify(step?.payload ?? {}, null, 2)}
              </code>
            </li>
          ))}
          <li className="rounded-md bg-slate-900 p-3 text-xs text-slate-400">
            <strong className="mr-2 text-slate-100">Fin de flux</strong>
            {finishCount >= 1 ? `${finishCount} évènement(s) de fin reçus.` : "En attente…"}
          </li>
        </ul>
      </section>

      <FinanceFixtureStreamer />
    </main>
  );
}

/**
 * Public wrapper exported to the Next.js page. The provider hydrates the
 * custom data stream context so the fixture-driven content can reflect the
 * streamed lifecycle exactly as the end-to-end test expects.
 */
export function FinanceHarness(): JSX.Element {
  return (
    <DataStreamProvider>
      <FinanceHarnessContent />
    </DataStreamProvider>
  );
}

