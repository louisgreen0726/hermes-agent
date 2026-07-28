import { useEffect, useRef, useState } from "react";
import { Brain, Eye, Gauge, Lightbulb, Wrench } from "lucide-react";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { api } from "@/lib/api";
import type { ModelInfoResponse } from "@/lib/api";
import { formatTokenCount } from "@/lib/format";
import { useI18n } from "@/i18n";
import { formatMessage } from "@/lib/locale-format";

interface ModelInfoCardProps {
  /** Current model string from config state — used to detect changes */
  currentModel: string;
  /** Bumped after config saves to trigger re-fetch */
  refreshKey?: number;
}

export function ModelInfoCard({
  currentModel,
  refreshKey = 0,
}: ModelInfoCardProps) {
  const { t } = useI18n();
  const [info, setInfo] = useState<ModelInfoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const lastFetchKeyRef = useRef("");

  useEffect(() => {
    if (!currentModel) return;
    // Re-fetch when model changes OR when refreshKey bumps (after save)
    const fetchKey = `${currentModel}:${refreshKey}`;
    if (fetchKey === lastFetchKeyRef.current) return;
    lastFetchKeyRef.current = fetchKey;
    setLoading(true);
    api
      .getModelInfo()
      .then(setInfo)
      .catch(() => setInfo(null))
      .finally(() => setLoading(false));
  }, [currentModel, refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
        <Spinner className="text-xs" />
        {t.components.modelInfo.loading}
      </div>
    );
  }

  if (!info || !info.model || info.effective_context_length <= 0) return null;

  const caps = info.capabilities;
  const hasCaps = caps && Object.keys(caps).length > 0;

  return (
    <div className="border border-border/60 bg-muted/30 px-3 py-2.5 space-y-2">
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Gauge className="h-3.5 w-3.5" />
          <span className="font-medium">
            {t.components.modelInfo.contextWindow}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono font-semibold text-foreground">
            {formatTokenCount(info.effective_context_length)}
          </span>
          {info.config_context_length > 0 ? (
            <span className="text-warning text-xs">
              {formatMessage(t.components.modelInfo.overrideAuto, {
                value: formatTokenCount(info.auto_context_length),
              })}
            </span>
          ) : (
            <span className="text-text-tertiary text-xs">
              {t.components.modelInfo.autoDetected}
            </span>
          )}
        </div>
      </div>

      {hasCaps && caps.max_output_tokens && caps.max_output_tokens > 0 && (
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Lightbulb className="h-3.5 w-3.5" />
            <span className="font-medium">
              {t.components.modelInfo.maxOutput}
            </span>
          </div>
          <span className="font-mono font-semibold text-foreground">
            {formatTokenCount(caps.max_output_tokens)}
          </span>
        </div>
      )}

      {hasCaps && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          {caps.supports_tools && (
            <span className="inline-flex items-center gap-1 bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
              <Wrench className="h-2.5 w-2.5" /> {t.components.modelInfo.tools}
            </span>
          )}
          {caps.supports_vision && (
            <span className="inline-flex items-center gap-1 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              <Eye className="h-2.5 w-2.5" /> {t.components.modelInfo.vision}
            </span>
          )}
          {caps.supports_reasoning && (
            <span className="inline-flex items-center gap-1 bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
              <Brain className="h-2.5 w-2.5" /> {t.components.modelInfo.reasoning}
            </span>
          )}
          {caps.model_family && (
            <span className="inline-flex items-center gap-1 bg-muted px-2 py-0.5 text-xs font-medium text-text-secondary">
              {caps.model_family}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
