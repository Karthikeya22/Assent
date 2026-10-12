"use client";

import { useEffect } from "react";
import type { RunEvent } from "./reducer";
import { useRunStore } from "./store";

const TERMINAL = new Set(["run_finished", "run_failed"]);

/**
 * Follow a run over SSE. The server replays the full event log on every connection, so state is
 * reset on (re)connect: correct after a dropped connection, never double-counted. The source is
 * closed on a terminal event; otherwise EventSource would reconnect forever.
 */
export function useRunStream(runId: string | null) {
  const { dispatch, reset } = useRunStore.getState();

  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(`/api/runs/${runId}/stream`);
    es.onopen = () => reset();
    es.onmessage = (m) => {
      const e = JSON.parse(m.data) as RunEvent;
      dispatch(e);
      if (TERMINAL.has(e.type)) es.close();
    };
    return () => es.close();
  }, [runId, dispatch, reset]);
}

/** Replay recorded events with their original pacing compressed (demo, Storybook, tests). */
export function useRunReplay(events: RunEvent[] | null, speed = 4) {
  const { dispatch, reset } = useRunStore.getState();

  useEffect(() => {
    if (!events) return;
    reset();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timers = events.map((e, i) =>
      window.setTimeout(() => dispatch(e), reduce ? 0 : (i * 220) / speed),
    );
    return () => timers.forEach(clearTimeout);
  }, [events, speed, dispatch, reset]);
}
