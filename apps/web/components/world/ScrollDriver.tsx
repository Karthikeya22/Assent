"use client";

import Lenis from "lenis";
import { useEffect } from "react";
import { locate, measure, type Ranges } from "./chapters";
import { useWorld } from "./store";

/**
 * Lenis is the scroll engine for the marketing pages (never the app). It owns its own rAF loop and
 * reports every scroll position; we turn that into the chapter place the world flies by.
 * Lenis honours prefers-reduced-motion itself (lerp 1, instant anchors) and still reports scroll.
 */
export function ScrollDriver() {
  useEffect(() => {
    let ranges: Ranges = { starts: [], end: 0 };
    const remeasure = () => {
      const y = window.scrollY;
      const tops = Array.from(document.querySelectorAll<HTMLElement>("[data-chapter]"), (el) => el.getBoundingClientRect().top + y);
      ranges = measure(tops, window.innerHeight, document.documentElement.scrollHeight);
    };
    const update = (y: number) => useWorld.setState(locate(y, ranges));

    const lenis = new Lenis({ autoRaf: true, anchors: true, lerp: 0.1 });
    lenis.on("scroll", (l: Lenis) => update(l.scroll));
    (window as Window & { __lenis?: Lenis }).__lenis = lenis; // scripted screenshots + poster capture drive the real scroller
    const ro = new ResizeObserver(() => {
      remeasure();
      update(window.scrollY);
    });
    ro.observe(document.body);
    remeasure();
    update(window.scrollY);
    return () => {
      ro.disconnect();
      lenis.destroy();
    };
  }, []);
  return null;
}
