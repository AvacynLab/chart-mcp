"use client";

import { Artifact } from "@/components/create-artifact";
import type { UIArtifact } from "@/components/artifact";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type SearchArtifactResult = {
  title: string;
  url: string;
  snippet: string;
  source: string;
  score: number;
};

type SearchMetadata = {
  results: SearchArtifactResult[];
  error?: string;
};

function createInitialMetadata(): SearchMetadata {
  return {
    results: [],
    error: undefined,
  };
}

function renderResults(results: SearchArtifactResult[]): JSX.Element {
  if (!results.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Aucun résultat</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-300">
            Le moteur SearxNG n’a retourné aucun résultat pour cette requête.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {results.map((result, index) => (
        <Card key={`${result.url}-${index}`} className="border-slate-700/60 bg-slate-900/40">
          <CardHeader className="space-y-2">
            <a
              href={result.url}
              target="_blank"
              rel="noreferrer"
              className="text-base font-semibold text-sky-300 hover:underline"
            >
              {result.title || result.url}
            </a>
            <Badge variant="outline" className="w-fit text-xs uppercase">
              {result.source}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-200">{result.snippet}</p>
            <p className="mt-2 text-xs text-slate-400">Score : {result.score.toFixed(2)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export const searchArtifact = new Artifact<"search", SearchMetadata>({
  kind: "search",
  description: "Recherche d’actualités et de documentation via SearxNG.",
  initialize: async ({ setMetadata }) => {
    setMetadata(createInitialMetadata());
  },
  onStreamPart: ({ streamPart, setMetadata, setArtifact }) => {
    switch (streamPart.type) {
      case "data-clear": {
        setMetadata(() => createInitialMetadata());
        setArtifact((draft: UIArtifact) => ({
          ...draft,
          content: "",
          status: "streaming",
        }));
        break;
      }
      case "data-search:batch": {
        const results = streamPart.data;
        setMetadata(() => ({ results, error: undefined }));
        setArtifact((draft: UIArtifact) => ({
          ...draft,
          content: results.map((item: SearchArtifactResult) => item.title).join("\n"),
          isVisible: true,
          status: "streaming",
        }));
        break;
      }
      case "data-finish": {
        setArtifact((draft) => ({
          ...draft,
          content: (draft.content ?? "").trim(),
          status: "idle",
          isVisible: true,
        }));
        break;
      }
      case "data-error": {
        const errorPayload = streamPart.data ?? {};
        setMetadata((state) => ({ ...state, error: String(errorPayload.message ?? "Erreur inattendue.") }));
        setArtifact((draft) => ({
          ...draft,
          status: "idle",
        }));
        break;
      }
      default:
        break;
    }
  },
  content: ({ metadata }) => {
    return (
      <div className="flex flex-col gap-4 p-4 lg:p-8">
        {metadata.error ? (
          <Card className="border-red-500/40 bg-red-900/10">
            <CardHeader>
              <CardTitle>Erreur de recherche</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-red-200">{metadata.error}</p>
            </CardContent>
          </Card>
        ) : null}
        {renderResults(metadata.results)}
      </div>
    );
  },
  actions: [],
  toolbar: [],
});
