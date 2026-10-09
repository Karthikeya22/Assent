import { withThemeByDataAttribute } from "@storybook/addon-themes";
import type { Preview } from "@storybook/nextjs-vite";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "../app/globals.css";

const sans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const mono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const serif = Instrument_Serif({ variable: "--font-instrument-serif", subsets: ["latin"], weight: "400" });

const preview: Preview = {
  parameters: { layout: "padded", nextjs: { appDirectory: true } },
  decorators: [
    (Story) => (
      <div className={`${sans.variable} ${mono.variable} ${serif.variable} font-sans`}>
        <Story />
      </div>
    ),
    // Same mechanism as the app: tokens switch on <html data-theme>.
    withThemeByDataAttribute({
      themes: { light: "light", dark: "dark" },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
  ],
};

export default preview;
