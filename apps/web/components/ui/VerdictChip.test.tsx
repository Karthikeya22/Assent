import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictChip, type Verdict } from "./VerdictChip";

describe("VerdictChip", () => {
  it.each<[Verdict, string, string]>([
    ["met", "✓", "Met"],
    ["not_met", "✕", "Not met"],
    ["insufficient", "○", "Insufficient"],
  ])("%s shows a glyph and a text label, never color alone", (verdict, glyph, label) => {
    const { container } = render(<VerdictChip verdict={verdict} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    const g = screen.getByText(glyph);
    expect(g).toHaveAttribute("aria-hidden", "true");
    expect(container.textContent).toBe(`${glyph}${label}`);
  });
});
