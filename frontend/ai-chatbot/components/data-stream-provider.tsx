"use client";

import type { DataUIPart } from "ai";
import type React from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { CustomUIDataTypes } from "@/lib/types";

type DataStreamContextValue = {
  dataStream: DataUIPart<CustomUIDataTypes>[];
  setDataStream: React.Dispatch<
    React.SetStateAction<DataUIPart<CustomUIDataTypes>[]>
  >;
};

const DataStreamContext = createContext<DataStreamContextValue | null>(null);

export function DataStreamProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [dataStream, setDataStream] = useState<DataUIPart<CustomUIDataTypes>[]>(
    []
  );

  useEffect(() => {
    /**
     * Surface the raw data stream on the `window` object when the dedicated
     * Playwright flag is enabled. This keeps the production build pristine
     * while giving end-to-end tests a stable hook to inspect finance SSE
     * lifecycles without reaching into React internals.
     */
    const enableDebug =
      process.env.NEXT_PUBLIC_ENABLE_E2E_STREAM_DEBUG === "1" ||
      process.env.NEXT_PUBLIC_ENABLE_E2E_STREAM_DEBUG === "true";

    if (!enableDebug || typeof window === "undefined") {
      return;
    }

    (window as typeof window & { __chartMcpDataStream?: DataUIPart<CustomUIDataTypes>[] }).__chartMcpDataStream = dataStream;
  }, [dataStream]);

  const value = useMemo(() => ({ dataStream, setDataStream }), [dataStream]);

  return (
    <DataStreamContext.Provider value={value}>
      {children}
    </DataStreamContext.Provider>
  );
}

export function useDataStream() {
  const context = useContext(DataStreamContext);
  if (!context) {
    throw new Error("useDataStream must be used within a DataStreamProvider");
  }
  return context;
}
