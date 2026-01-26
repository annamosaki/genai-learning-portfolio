"use client";

import { useState } from "react";
import { clsx } from "clsx";
import { ZoneLink } from "@/components/zone-link";

interface DemoEmbedProps {
  url: string;
  title: string;
  className?: string;
}

export function DemoEmbed({ url, title, className }: DemoEmbedProps) {
  const [embedMode, setEmbedMode] = useState<"iframe" | "link">("link");
  const [isLoading, setIsLoading] = useState(true);

  const handleIframeLoad = () => {
    setIsLoading(false);
  };

  if (embedMode === "link") {
    return (
      <div className={clsx("rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-8", className)}>
        <div className="text-center">
          <div className="mb-4 text-4xl">🚀</div>
          <h3 className="mb-4 text-xl font-medium">{title} Demo</h3>
          <p className="mb-6 text-[var(--color-muted)]">
            Open the live demo to interact with the full application. Use ← Portfolio in the demo header to return home.
          </p>
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <ZoneLink href={url} className="btn btn-primary">
              Open Demo →
            </ZoneLink>
            <button
              type="button"
              onClick={() => setEmbedMode("iframe")}
              className="btn btn-secondary"
            >
              Embed Preview
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx("relative rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)]", className)}>
      <div className="flex items-center justify-between border-b border-[var(--color-line)] p-4">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            <div className="h-3 w-3 rounded-full bg-red-400" />
            <div className="h-3 w-3 rounded-full bg-amber-400" />
            <div className="h-3 w-3 rounded-full bg-green-400" />
          </div>
          <span className="text-sm text-[var(--color-muted)]">{title}</span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEmbedMode("link")}
            className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)]"
          >
            Card View
          </button>
          <ZoneLink
            href={url}
            className="text-sm text-[var(--color-muted)] hover:text-[var(--color-accent)]"
          >
            Open full screen →
          </ZoneLink>
        </div>
      </div>

      <div className="relative aspect-[16/10] overflow-hidden rounded-b-2xl">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-panel)]">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent" />
              <span className="text-sm text-[var(--color-muted)]">Loading demo...</span>
            </div>
          </div>
        )}
        <iframe
          src={url}
          title={title}
          className="h-full w-full"
          onLoad={handleIframeLoad}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>
    </div>
  );
}
