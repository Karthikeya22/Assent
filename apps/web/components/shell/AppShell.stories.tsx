import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { AppShell } from "./AppShell";

const meta: Meta<typeof AppShell> = {
  title: "Shell/AppShell",
  component: AppShell,
  parameters: { layout: "fullscreen", nextjs: { navigation: { pathname: "/app/worklist" } } },
};
export default meta;

export const EmptyWorklist: StoryObj<typeof AppShell> = {
  args: {
    user: { name: "Coordinator Demo", role: "coordinator" },
    signOut: async () => {},
    breadcrumb: <span className="text-ink">Worklist</span>,
    children: (
      <div className="px-6 py-5">
        <h1 className="display text-xl">Worklist</h1>
        <p className="display mt-16 text-2xl">No cases yet.</p>
      </div>
    ),
  },
};
