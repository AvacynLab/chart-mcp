/**
 * Minimal ambient module declarations used exclusively for the standalone TypeScript
 * checks executed in CI. The real Next.js runtime provides richer typings, but the
 * bare `tsc --noEmit` invocation lacks the Next compiler plugins that normally
 * inject them. These shims satisfy the few symbols imported throughout the repo
 * without masking potential runtime issues.
 */
declare module "next" {
  export interface Metadata {
    /** Arbitrary metadata properties attached to Next.js layouts or pages. */
    readonly [key: string]: unknown;
  }
}

declare module "next/headers" {
  interface CookieRecord {
    readonly name: string;
    readonly value?: string;
  }

  interface CookieStore {
    /** Retrieve a cookie by name. */
    get(name: string): CookieRecord | undefined;
  }

  export function cookies(): CookieStore;
}

declare module "lightweight-charts" {
  export type Time = number;

  export interface CandlestickData<TTime = Time> {
    readonly time: TTime;
    readonly open?: number;
    readonly high?: number;
    readonly low?: number;
    readonly close?: number;
    readonly volume?: number;
  }

  export interface LineData<TTime = Time> {
    readonly time: TTime;
    readonly value?: number | null;
  }

  export interface HistogramData<TTime = Time> {
    readonly time: TTime;
    readonly value?: number | null;
    readonly color?: string;
  }

  export interface ISeriesApi<TPoint = unknown> {
    /** Replace the underlying series data with the provided points. */
    setData(data: readonly TPoint[] | readonly unknown[]): void;
    /** Optional teardown hook exposed by lightweight-charts. */
    remove?(): void;
  }

  export interface IChartApi {
    addCandlestickSeries(options?: unknown): ISeriesApi;
    addLineSeries(options?: unknown): ISeriesApi;
    addHistogramSeries(options?: unknown): ISeriesApi;
    removeSeries(series: ISeriesApi): void;
    remove(): void;
    timeScale(): { fitContent(): void };
  }

  export function createChart(container: HTMLElement, options?: unknown): IChartApi;
}

declare module "@microsoft/fetch-event-source" {
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

  export function fetchEventSource(url: string, init?: FetchEventSourceInit): Promise<void>;
}
