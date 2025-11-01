"use client";

import { useEffect, useState } from "react";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "./elements/reasoning";

type MessageReasoningProps = {
  isLoading: boolean;
  reasoning: string;
};

export function MessageReasoning({
  isLoading,
  reasoning,
}: MessageReasoningProps) {
  const [hasBeenStreaming, setHasBeenStreaming] = useState(isLoading);

  useEffect(() => {
    if (isLoading) {
      setHasBeenStreaming(true);
    }
  }, [isLoading]);

  return (
    <>
      {/* Expose the full reasoning text so automated accessibility checks and the Playwright smoke tests can assert on the content without forcing the accordion open. */}
      <Reasoning
        data-reasoning-text={reasoning}
        data-testid="message-reasoning"
        defaultOpen={hasBeenStreaming}
        isStreaming={isLoading}
      >
        <ReasoningTrigger />
        <ReasoningContent>{reasoning}</ReasoningContent>
      </Reasoning>
    </>
  );
}
