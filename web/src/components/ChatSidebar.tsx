/**
 * ChatSidebar — structured-events panel that sits next to the xterm.js
 * terminal in the dashboard Chat tab.
 *
 * Two WebSockets, one per concern:
 *
 *   1. **JSON-RPC sidecar** (`GatewayClient` → /api/ws) — drives the
 *      sidebar's own slot of the dashboard's in-process gateway.  Owns
 *      the model badge / picker / connection state / error banner.
 *      Independent of the PTY pane's session by design — those are the
 *      pieces the sidebar needs to be able to drive directly (model
 *      switch via slash.exec, etc.).
 *
 *   2. **Event subscriber** (/api/events?channel=…) — passive, receives
 *      every dispatcher emit from the PTY-side `tui_gateway.entry` that
 *      the dashboard fanned out.  This is how `tool.start/progress/
 *      complete` from the agent loop reach the sidebar even though the
 *      PTY child runs three processes deep from us.  The `channel` id
 *      ties this listener to the same chat tab's PTY child — see
 *      `ChatPage.tsx` for where the id is generated.
 *
 * Best-effort throughout: WS failures show in the badge / banner, the
 * terminal pane keeps working unimpaired.
 */

import { Button } from "@nous-research/ui/ui/components/button";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Card } from "@/components/ui/card";

import { ModelPickerDialog } from "@/components/ModelPickerDialog";
import { ToolCall, type ToolEntry } from "@/components/ToolCall";
import { GatewayClient, type ConnectionState } from "@/lib/gatewayClient";
import { api, type VestaSessionStatusResponse } from "@/lib/api";

import { cn } from "@/lib/utils";
import { AlertCircle, ChevronDown, ClipboardList, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

interface SessionInfo {
  cwd?: string;
  model?: string;
  provider?: string;
  session_id?: string;
  credential_warning?: string;
}

interface RpcEnvelope {
  method?: string;
  params?: { payload?: unknown; session_id?: string; type?: string };
}

const TOOL_LIMIT = 20;

const STATE_LABEL: Record<ConnectionState, string> = {
  idle: "idle",
  connecting: "connecting",
  open: "live",
  closed: "closed",
  error: "error",
};

const STATE_TONE: Record<
  ConnectionState,
  "secondary" | "warning" | "success" | "destructive"
> = {
  idle: "secondary",
  connecting: "warning",
  open: "success",
  closed: "secondary",
  error: "destructive",
};

function finalizationTone(
  status: string | undefined,
): "secondary" | "warning" | "success" | "destructive" | "outline" {
  if (status === "accepted") return "success";
  if (status === "blocked" || status === "failed") return "destructive";
  if (status === "not_written" || !status) return "outline";
  return "warning";
}

function shortPath(path: string | undefined): string {
  if (!path) return "—";
  const parts = path.split("/").filter(Boolean);
  return parts.slice(-3).join("/") || path;
}

function shortModelName(model: string | undefined): string {
  if (!model) return "—";
  return model.split("/").filter(Boolean).slice(-1)[0] ?? model;
}

function runtimeSessionId(
  payload: SessionInfo | undefined,
  fallback: string | undefined,
): string | null {
  const sessionId = payload?.session_id?.trim();
  if (sessionId) return sessionId;
  return fallback?.trim() || null;
}

interface ChatSidebarProps {
  channel: string;
  sessionIdHint?: string | null;
  className?: string;
}

export function ChatSidebar({ channel, sessionIdHint = null, className }: ChatSidebarProps) {
  // `version` bumps on reconnect; gw is derived so we never call setState
  // for it inside an effect (React 19's set-state-in-effect rule). The
  // counter is the dependency on purpose — it's not read in the memo body,
  // it's the signal that says "rebuild the client".
  const [version, setVersion] = useState(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const gw = useMemo(() => new GatewayClient(), [version]);

  const [state, setState] = useState<ConnectionState>("idle");
  const [controlSessionId, setControlSessionId] = useState<string | null>(null);
  const [observedSessionId, setObservedSessionId] = useState<string | null>(
    sessionIdHint,
  );
  const [info, setInfo] = useState<SessionInfo>({});
  const [tools, setTools] = useState<ToolEntry[]>([]);
  const [vesta, setVesta] = useState<VestaSessionStatusResponse | null>(null);
  const [modelOpen, setModelOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshVesta = useCallback((sid: string | null = observedSessionId) => {
    if (!sid) {
      setVesta(null);
      return;
    }

    api
      .getSessionVestaStatus(sid)
      .then(async (primary) => {
        if (primary.active || !sessionIdHint || sessionIdHint === sid) {
          setVesta(primary);
          return;
        }

        const fallback = await api.getSessionVestaStatus(sessionIdHint);
        setVesta(fallback.active ? fallback : primary);
      })
      .catch(() => {
        setVesta({ active: false, error: "Vesta status unavailable", session_id: sid });
      });
  }, [observedSessionId, sessionIdHint]);

  useEffect(() => {
    setObservedSessionId(sessionIdHint);
  }, [sessionIdHint]);

  useEffect(() => {
    let cancelled = false;
    const offState = gw.onState(setState);

    const offSessionInfo = gw.on<SessionInfo>("session.info", (ev) => {
      if (ev.session_id) {
        setControlSessionId(ev.session_id);
      }

      if (ev.payload) {
        setInfo((prev) => ({ ...prev, ...ev.payload }));
      }
    });

    const offError = gw.on<{ message?: string }>("error", (ev) => {
      const message = ev.payload?.message;

      if (message) {
        setError(message);
      }
    });

    // Adopt whichever session the gateway hands us. session.create on the
    // sidecar is independent of the PTY pane's session by design — we
    // only need a sid to drive the model picker's slash.exec calls.
    gw.connect()
      .then(() => {
        if (cancelled) {
          return;
        }
        return gw.request<{ session_id: string }>("session.create", {});
      })
      .then((created) => {
        if (cancelled || !created?.session_id) {
          return;
        }
        setControlSessionId(created.session_id);
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setError(e.message);
        }
      });

    return () => {
      cancelled = true;
      offState();
      offSessionInfo();
      offError();
      gw.close();
    };
  }, [gw]);

  useEffect(() => {
    if (!observedSessionId) {
      setVesta(null);
      return;
    }

    refreshVesta(observedSessionId);
    const id = window.setInterval(() => refreshVesta(observedSessionId), 5000);
    return () => window.clearInterval(id);
  }, [refreshVesta, observedSessionId]);

  // Event subscriber WebSocket — receives the rebroadcast of every
  // dispatcher emit from the PTY child's gateway.  See /api/pub +
  // /api/events in hermes_cli/web_server.py for the broadcast hop.
  //
  // Failures (auth/loopback rejection, server too old to expose the
  // endpoint, transient drops) surface in the same banner as the
  // JSON-RPC sidecar so the sidebar matches its documented best-effort
  // UX and the user always has a reconnect affordance.
  useEffect(() => {
    const token = window.__HERMES_SESSION_TOKEN__;

    if (!token || !channel) {
      return;
    }

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const qs = new URLSearchParams({ token, channel });
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/events?${qs.toString()}`,
    );

    // `unmounting` suppresses the banner during cleanup — `ws.close()`
    // from the effect's return fires a close event with code 1005 that
    // would otherwise look like an unexpected drop.
    const DISCONNECTED = "events feed disconnected — tool calls may not appear";
    let unmounting = false;
    const surface = (msg: string) => !unmounting && setError(msg);

    ws.addEventListener("error", () => surface(DISCONNECTED));

    ws.addEventListener("close", (ev) => {
      if (ev.code === 4401 || ev.code === 4403) {
        surface(`events feed rejected (${ev.code}) — reload the page`);
      } else if (ev.code !== 1000) {
        surface(DISCONNECTED);
      }
    });

    ws.addEventListener("message", (ev) => {
      let frame: RpcEnvelope;

      try {
        frame = JSON.parse(ev.data);
      } catch {
        return;
      }

      if (frame.method !== "event" || !frame.params) {
        return;
      }

      const { type, payload } = frame.params;
      const eventSessionId = frame.params.session_id;

      if (type === "session.info") {
        const p = payload as SessionInfo | undefined;
        if (p) {
          setInfo((prev) => ({ ...prev, ...p }));
        }
        const runtimeSid = runtimeSessionId(p, eventSessionId);
        if (runtimeSid) {
          setObservedSessionId(runtimeSid);
          refreshVesta(runtimeSid);
        }
      } else if (type === "tool.start") {
        const p = payload as
          | { tool_id?: string; name?: string; context?: string }
          | undefined;
        const toolId = p?.tool_id;

        if (!toolId) {
          return;
        }

        setTools((prev) =>
          [
            ...prev,
            {
              kind: "tool" as const,
              id: `tool-${toolId}-${prev.length}`,
              tool_id: toolId,
              name: p?.name ?? "tool",
              context: p?.context,
              status: "running" as const,
              startedAt: Date.now(),
            },
          ].slice(-TOOL_LIMIT),
        );
      } else if (type === "tool.progress") {
        const p = payload as
          | { name?: string; preview?: string }
          | undefined;

        if (!p?.name || !p.preview) {
          return;
        }

        setTools((prev) =>
          prev.map((t) =>
            t.status === "running" && t.name === p.name
              ? { ...t, preview: p.preview }
              : t,
          ),
        );
      } else if (type === "tool.complete") {
        const p = payload as
          | {
              tool_id?: string;
              summary?: string;
              error?: string;
              inline_diff?: string;
            }
          | undefined;

        if (!p?.tool_id) {
          return;
        }

        setTools((prev) =>
          prev.map((t) =>
            t.tool_id === p.tool_id
              ? {
                  ...t,
                  status: p.error ? "error" : "done",
                  summary: p.summary,
                  error: p.error,
                  inline_diff: p.inline_diff,
                  completedAt: Date.now(),
                }
              : t,
          ),
        );
        refreshVesta();
      }
    });

    return () => {
      unmounting = true;
      ws.close();
    };
  }, [channel, refreshVesta, version]);

  const reconnect = useCallback(() => {
    setError(null);
    setTools([]);
    setVersion((v) => v + 1);
  }, []);

  // Picker hands us a fully-formed slash command (e.g. "/model anthropic/...").
  // Fire-and-forget through `slash.exec`; the TUI pane will render the result
  // via PTY, so the sidebar doesn't need to surface output of its own.
  const onModelSubmit = useCallback(
    (slashCommand: string) => {
      if (!controlSessionId) {
        return;
      }

      void gw.request("slash.exec", {
        session_id: controlSessionId,
        command: slashCommand,
      });
      setModelOpen(false);
    },
    [gw, controlSessionId],
  );

  const canPickModel = state === "open" && !!controlSessionId;
  const modelLabel = (info.model ?? "—").split("/").slice(-1)[0] ?? "—";
  const banner = error ?? info.credential_warning ?? null;
  const vestaRun = vesta?.status;
  const runtime = vestaRun?.runtime;
  const workers = vestaRun?.worker_state?.workers ?? [];
  const workerLanes = Array.from(
    new Set(
      workers
        .map((worker) =>
          typeof worker.model_lane === "string" ? worker.model_lane.trim() : "",
        )
        .filter(Boolean),
    ),
  );
  const mainModel = runtime?.model;
  const delegateModel = runtime?.delegation_model || workerLanes[0];
  const openArtifactCount = vestaRun?.artifacts?.open_artifacts?.length ?? 0;
  const artifactCount = vestaRun?.artifacts?.artifacts?.length ?? 0;
  const workerCount = workers.length;
  const blockerCount =
    (vestaRun?.worker_state?.blockers?.length ?? 0) +
    (vestaRun?.validator_blockers?.length ?? 0);
  const finalization = vestaRun?.finalization_status ?? "not_written";

  return (
    <aside
      className={cn(
        "flex h-full w-full min-w-0 shrink-0 flex-col gap-3 overflow-y-auto overflow-x-hidden pr-1 normal-case lg:w-80",
        className,
      )}
    >
      <Card className="flex items-center justify-between gap-2 px-3 py-2">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            model
          </div>

          <Button
            ghost
            size="sm"
            disabled={!canPickModel}
            onClick={() => setModelOpen(true)}
            suffix={
              canPickModel ? (
                <ChevronDown className="opacity-60" />
              ) : undefined
            }
            className="self-start min-w-0 px-0 py-0 normal-case tracking-normal text-sm font-medium hover:underline disabled:no-underline"
            title={info.model ?? "switch model"}
          >
            <span className="truncate">{modelLabel}</span>
          </Button>
        </div>

        <Badge tone={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
      </Card>

      {banner && (
        <Card className="flex items-start gap-2 border-destructive/40 bg-destructive/5 px-3 py-2 text-xs">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />

          <div className="min-w-0 flex-1">
            <div className="wrap-break-word text-destructive">{banner}</div>

            {error && (
              <Button
                size="sm"
                outlined
                className="mt-1"
                onClick={reconnect}
                prefix={<RefreshCw />}
              >
                reconnect
              </Button>
            )}
          </div>
        </Card>
      )}

      <Card className="flex flex-col gap-2 px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <ClipboardList className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <div className="truncate text-xs uppercase tracking-wider text-muted-foreground">
              vesta run
            </div>
          </div>

          <Badge tone={vesta?.active ? finalizationTone(finalization) : "outline"}>
            {vesta?.active ? finalization : "none"}
          </Badge>
        </div>

        {vesta?.active && vestaRun ? (
          <div className="grid gap-1 text-xs text-muted-foreground">
            <div className="flex min-w-0 justify-between gap-3">
              <span>run</span>
              <span className="min-w-0 truncate font-mono text-foreground" title={vestaRun.run_id}>
                {vestaRun.run_id ?? "—"}
              </span>
            </div>
            <div className="flex min-w-0 justify-between gap-3">
              <span>validator</span>
              <span className="truncate text-foreground">{vestaRun.validator_status ?? "absent"}</span>
            </div>
            <div className="flex min-w-0 justify-between gap-3">
              <span>main</span>
              <span className="min-w-0 truncate font-mono text-foreground" title={mainModel}>
                {shortModelName(mainModel)}
              </span>
            </div>
            <div className="flex min-w-0 justify-between gap-3">
              <span>validator</span>
              <span className="min-w-0 truncate font-mono text-foreground" title={delegateModel}>
                {shortModelName(delegateModel)}
              </span>
            </div>
            <div className="flex min-w-0 justify-between gap-3">
              <span>artifacts</span>
              <span className={openArtifactCount > 0 ? "text-warning" : "text-foreground"}>
                {openArtifactCount} open / {artifactCount} total
              </span>
            </div>
            <div className="flex min-w-0 justify-between gap-3">
              <span>workers</span>
              <span className={blockerCount > 0 ? "text-warning" : "text-foreground"}>
                {workerCount} total{blockerCount > 0 ? ` · ${blockerCount} blockers` : ""}
              </span>
            </div>
            <div className="grid gap-0.5">
              <span>next action</span>
              <span className="line-clamp-3 text-foreground">
                {vestaRun.next_action || "unresolved"}
              </span>
            </div>
            <div className="truncate font-mono text-[10px]" title={vestaRun.run_dir}>
              {shortPath(vestaRun.run_dir)}
            </div>
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">
            {vesta?.error ?? "no Vesta state for this session yet"}
          </div>
        )}
      </Card>

      <Card className="flex min-h-0 flex-none flex-col px-2 py-2">
        <div className="px-1 pb-2 text-xs uppercase tracking-wider text-muted-foreground">
          tools
        </div>

        <div className="flex min-h-0 flex-col gap-1.5">
          {tools.length === 0 ? (
            <div className="px-2 py-4 text-center text-xs text-muted-foreground">
              no tool calls yet
            </div>
          ) : (
            tools.map((t) => <ToolCall key={t.id} tool={t} />)
          )}
        </div>
      </Card>

      {modelOpen && canPickModel && controlSessionId && (
        <ModelPickerDialog
          gw={gw}
          sessionId={controlSessionId}
          onClose={() => setModelOpen(false)}
          onSubmit={onModelSubmit}
        />
      )}
    </aside>
  );
}
