import type { StorybookConfig } from "@storybook/nextjs-vite";

const config: StorybookConfig = {
  stories: ["../components/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-themes"],
  framework: { name: "@storybook/nextjs-vite", options: {} },
  core: { disableTelemetry: true },
};

export default config;
