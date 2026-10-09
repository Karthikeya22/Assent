import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { MonoChip } from "./MonoChip";
import { VerdictChip } from "./VerdictChip";

const meta: Meta = { title: "UI/Chips" };
export default meta;

export const Verdicts: StoryObj = {
  render: () => (
    <div className="flex gap-2">
      <VerdictChip verdict="met" />
      <VerdictChip verdict="not_met" />
      <VerdictChip verdict="insufficient" />
    </div>
  ),
};

export const Mono: StoryObj = {
  render: () => (
    <div className="flex gap-2">
      <MonoChip>CPT 62323</MonoChip>
      <MonoChip>LCD L39240</MonoChip>
      <MonoChip>M54.16</MonoChip>
      <MonoChip tone="gap">Synthetic data</MonoChip>
    </div>
  ),
};
