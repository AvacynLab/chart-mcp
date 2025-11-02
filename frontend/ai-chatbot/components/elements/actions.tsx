"use client";

import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Lightweight flex wrapper for action buttons displayed next to messages.
 *
 * The props are always forwarded to the root element so Playwright selectors,
 * accessibility attributes or extra styling hooks make it down to the DOM.
 */
export type ActionsProps = ComponentProps<"div">;

export const Actions = ({ className, children, ...props }: ActionsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props}>
    {children}
  </div>
);

export type ActionProps = ComponentProps<typeof Button> & {
  tooltip?: string;
  label?: string;
};

export const Action = ({
  tooltip,
  children,
  label,
  className,
  variant = "ghost",
  size = "icon",
  ...props
}: ActionProps) => {
  /**
   * Build the button once so it can optionally be wrapped by a tooltip. Using
   * the spread operator ensures data attributes (`data-testid`) and callbacks
   * bubble all the way to the actual clickable control that lives in the DOM.
   */
  const button = (
    <Button
      className={cn(
        "relative size-9 p-1.5 text-muted-foreground hover:text-foreground",
        className
      )}
      size={size}
      type="button"
      variant={variant}
      {...props}
    >
      {children}
      <span className="sr-only">{label || tooltip}</span>
    </Button>
  );

  if (tooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
};
