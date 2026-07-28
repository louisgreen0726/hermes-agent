import { useCallback, useEffect, useState } from "react";
import { Clock, Wand2 } from "lucide-react";
import { Button } from "@nous-research/ui/ui/components/button";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Card, CardContent } from "@nous-research/ui/ui/components/card";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { api } from "@/lib/api";
import type { AutomationBlueprint, AutomationBlueprintField } from "@/lib/api";
import { cn, themedBody } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { formatMessage } from "@/lib/locale-format";

interface AutomationBlueprintsProps {
  profile: string;
  /** Called after a blueprint is instantiated so the parent can refresh its job list. */
  onCreated?: () => void;
}

/** Initial form values for a blueprint = each field's default (or ""). */
function initialValues(
  blueprint: AutomationBlueprint,
  localizedDefaults: Record<string, string>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const f of blueprint.fields) {
    out[f.name] =
      localizedDefaults[`${blueprint.key}.${f.name}`] ?? f.default ?? "";
  }
  return out;
}

function FieldInput({
  field,
  value,
  onChange,
  optionLabels,
  placeholder,
}: {
  field: AutomationBlueprintField;
  value: string;
  onChange: (v: string) => void;
  optionLabels: Record<string, string>;
  placeholder: string;
}) {
  if (field.type === "enum" || field.type === "weekdays") {
    return (
      <Select value={value} onValueChange={(v) => onChange(v)}>
        {field.options.map((opt) => (
          <SelectOption key={opt} value={opt}>
            {optionLabels[opt] ?? opt}
          </SelectOption>
        ))}
      </Select>
    );
  }
  if (field.type === "time") {
    return (
      <Input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  // text
  return (
    <Input
      type="text"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function BlueprintCard({
  blueprint,
  profile,
  showToast,
  onCreated,
}: {
  blueprint: AutomationBlueprint;
  profile: string;
  showToast: (message: string, type: "error" | "success") => void;
  onCreated?: () => void;
}) {
  const { t } = useI18n();
  const strings = t.components.automationBlueprints;
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>(() =>
    initialValues(blueprint, strings.fieldDefaults),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      const job = await api.instantiateAutomationBlueprint({ blueprint: blueprint.key, values }, profile);
      const when = job.schedule?.expr ? ` — ${job.schedule.expr}` : "";
      showToast(
        formatMessage(strings.scheduled, {
          title: strings.titles[blueprint.key] ?? blueprint.title,
          when,
        }),
        "success",
      );
      setOpen(false);
      setValues(initialValues(blueprint, strings.fieldDefaults));
      onCreated?.();
    } catch (e) {
      // 422 from the API carries the slot-level validation message.
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg.replace(/^\d+:\s*/, ""));
    } finally {
      setSubmitting(false);
    }
  }, [blueprint, values, profile, showToast, onCreated, strings]);

  const title = strings.titles[blueprint.key] ?? blueprint.title;
  const description =
    strings.descriptions[blueprint.key] ?? blueprint.description;

  return (
    <Card className={cn("overflow-hidden", themedBody)}>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Wand2 className="h-4 w-4 shrink-0 opacity-70" />
              <span className="font-medium">{title}</span>
            </div>
            <p className="mt-1 text-sm opacity-70">{description}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {blueprint.tags.map((t) => (
                <Badge key={t} tone="secondary">
                  {strings.tagLabels[t] ?? t}
                </Badge>
              ))}
            </div>
          </div>
          <Button
            ghost={open}
            size="sm"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? strings.cancel : strings.setup}
          </Button>
        </div>

        {open && (
          <div className="space-y-3 border-t pt-3">
            {blueprint.fields.map((f) => (
              <div key={f.name} className="space-y-1">
                <Label htmlFor={`${blueprint.key}-${f.name}`}>
                  {strings.fieldLabels[`${blueprint.key}.${f.name}`] ??
                    strings.fieldLabels[f.name] ??
                    f.label}
                </Label>
                <FieldInput
                  field={f}
                  value={values[f.name] ?? ""}
                  onChange={(v) => setValues((prev) => ({ ...prev, [f.name]: v }))}
                  optionLabels={strings.optionLabels}
                  placeholder={
                    strings.fieldHelp[`${blueprint.key}.${f.name}`] ??
                    strings.fieldHelp[f.name] ??
                    strings.fieldLabels[`${blueprint.key}.${f.name}`] ??
                    strings.fieldLabels[f.name] ??
                    (f.help || f.label)
                  }
                />
                {f.help && f.type !== "text" ? (
                  <p className="text-xs opacity-60">
                    {strings.fieldHelp[`${blueprint.key}.${f.name}`] ??
                      strings.fieldHelp[f.name] ??
                      f.help}
                  </p>
                ) : null}
              </div>
            ))}
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex items-center gap-2">
              <Button
                onClick={() => void submit()}
                disabled={submitting}
                prefix={submitting ? <Spinner /> : <Clock />}
              >
                {strings.scheduleIt}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Automation Blueprints gallery — the form-where-there's-a-screen surface. Each blueprint
 * card expands into an inline form (one field per typed slot); submitting POSTs
 * to /api/cron/blueprints/instantiate which fills the blueprint and creates the job
 * via the same create_job path as everything else.
 */
export function AutomationBlueprints({ profile, onCreated }: AutomationBlueprintsProps) {
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const [blueprints, setBlueprints] = useState<AutomationBlueprint[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getAutomationBlueprints()
      .then((r) => {
        if (!cancelled) setBlueprints(r.blueprints);
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return (
      <p className="text-sm text-destructive">
        {formatMessage(t.components.automationBlueprints.loadFailed, {
          error: loadError,
        })}
      </p>
    );
  }
  if (blueprints === null) {
    return (
      <div className="flex items-center gap-2 opacity-70">
        <Spinner className="h-4 w-4" />
        {t.components.automationBlueprints.loading}
      </div>
    );
  }
  if (blueprints.length === 0) {
    return (
      <p className="opacity-70">
        {t.components.automationBlueprints.empty}
      </p>
    );
  }

  return (
    <>
      <Toast toast={toast} />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {blueprints.map((r) => (
          <BlueprintCard
            key={r.key}
            blueprint={r}
            profile={profile}
            showToast={showToast}
            onCreated={onCreated}
          />
        ))}
      </div>
    </>
  );
}

export default AutomationBlueprints;
