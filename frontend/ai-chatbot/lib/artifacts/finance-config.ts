/**
 * Runtime store keeping track of finance streaming job configuration.
 *
 * The createFinanceArtifact tool records the parameters required to call the
 * backend SSE endpoint before delegating to the document handler. The handler
 * later retrieves and consumes the configuration using the generated document
 * identifier.
 */
export type FinanceArtifactConfig = {
  /** Trading symbol requested by the user, e.g. "BTCUSDT". */
  symbol: string;
  /** Exchange timeframe such as "1h" or "4h". */
  timeframe: string;
  /** Optional indicator specifiers formatted like "ema:21". */
  indicators?: string[];
  /** Number of OHLCV rows requested for the analysis stream. */
  limit?: number;
  /** Whether the pipeline should emit support/resistance levels. */
  includeLevels: boolean;
  /** Whether the pipeline should emit chart patterns. */
  includePatterns: boolean;
  /** Optional cap on the number of returned levels (maps to the `max` query parameter). */
  maxLevels?: number;
};

const configStore = new Map<string, FinanceArtifactConfig>();

/** Persist a configuration so the finance document handler can fetch it later. */
export function setFinanceArtifactConfig(id: string, config: FinanceArtifactConfig): void {
  configStore.set(id, config);
}

/** Retrieve and delete a stored finance configuration by identifier. */
export function consumeFinanceArtifactConfig(id: string): FinanceArtifactConfig | undefined {
  const config = configStore.get(id);
  if (config) {
    configStore.delete(id);
  }
  return config;
}
