/**
 * Lightweight stub for the ``lightweight-charts`` module used in Vitest. The real
 * library is only required in the browser; providing a deterministic fallback keeps
 * the unit tests focused on the React integration instead of the rendering engine.
 */
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
  setData(_data: readonly TPoint[] | readonly unknown[]): void;
  remove?(): void;
}

export interface IChartApi {
  addCandlestickSeries(_options?: unknown): ISeriesApi<CandlestickData>;
  addLineSeries(_options?: unknown): ISeriesApi<LineData>;
  addHistogramSeries(_options?: unknown): ISeriesApi<HistogramData>;
  removeSeries(_series: ISeriesApi): void;
  remove(): void;
  timeScale(): { fitContent(): void };
}

export function createChart(): IChartApi {
  const makeSeries = (): ISeriesApi => ({
    setData: () => {
      // Series updates are ignored by design in the stub.
    },
    remove: () => {
      // Removing a stubbed series has no effect in unit tests.
    },
  });

  return {
    addCandlestickSeries: () => makeSeries(),
    addLineSeries: () => makeSeries(),
    addHistogramSeries: () => makeSeries(),
    removeSeries: () => {
      // Removing a series is a no-op in the stub implementation.
    },
    remove: () => {
      // Disposing the chart does not need to alter the DOM in tests.
    },
    timeScale: () => ({
      fitContent: () => {
        // Layout adjustments are ignored in the testing environment.
      },
    }),
  };
}
