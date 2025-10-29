/**
 * Runtime store recording HTTP parameters for the search artifact.
 *
 * The createSearchArtifact tool pushes the user's query metadata into this map
 * before triggering the document handler. The handler then consumes the
 * configuration to call the FastAPI `/api/v1/search` endpoint exactly once per
 * artifact creation.
 */
export type SearchArtifactConfig = {
  /** Raw query typed by the end user. */
  query: string;
  /** Optional SearxNG categories selected by the model. */
  categories?: string[];
  /** Optional SearxNG relative time range such as "day" or "week". */
  timeRange?: string;
};

const configStore = new Map<string, SearchArtifactConfig>();

/** Persist a search artifact configuration under the generated document id. */
export function setSearchArtifactConfig(id: string, config: SearchArtifactConfig): void {
  configStore.set(id, config);
}

/** Retrieve and remove the stored configuration for a given document id. */
export function consumeSearchArtifactConfig(id: string): SearchArtifactConfig | undefined {
  const config = configStore.get(id);
  if (config) {
    configStore.delete(id);
  }
  return config;
}
