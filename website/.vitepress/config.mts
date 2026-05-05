import { defineConfig } from "vitepress";

export default defineConfig({
  title: "ZTF Stamp Benchmark",
  description:
    "Vision–language benchmark for ZTF / ALeRCE alert stamps: montages, structured JSON (Parts A–C), and cascade evaluation.",
  lastUpdated: true,
  cleanUrls: true,
  themeConfig: {
    logo: "/logo.svg",
    nav: [
      { text: "Guide", link: "/guide/overview", activeMatch: "^/guide/(?!leaderboard)(?!visualizations)(?!resources)" },
      { text: "Leaderboard", link: "/guide/leaderboard" },
      { text: "Figures", link: "/guide/visualizations" },
      { text: "Links", link: "/guide/resources" },
      {
        text: "GitHub",
        link: "https://github.com/Cruuusade/LLM_FOR_ASTRONOMY",
      },
    ],
    sidebar: [
      {
        text: "Introduction",
        items: [
          { text: "Welcome", link: "/" },
          { text: "Overview", link: "/guide/overview" },
        ],
      },
      {
        text: "Leaderboard",
        items: [
          { text: "Full benchmark (n = 1500)", link: "/guide/leaderboard" },
        ],
      },
      {
        text: "Visualizations",
        items: [
          { text: "Images, graphs & examples", link: "/guide/visualizations" },
        ],
      },
      {
        text: "Dataset",
        items: [
          { text: "Sources & splits", link: "/guide/dataset" },
          { text: "Images & montages", link: "/guide/images" },
          { text: "Manifest columns", link: "/guide/manifest" },
        ],
      },
      {
        text: "Task",
        items: [
          { text: "JSON contract (Parts A–C)", link: "/guide/task-format" },
        ],
      },
      {
        text: "Evaluation",
        items: [
          { text: "Metrics & runner", link: "/guide/evaluation" },
        ],
      },
      {
        text: "Get started",
        items: [
          { text: "Setup & reproduction", link: "/guide/reproduction" },
        ],
      },
      {
        text: "Resources",
        items: [
          { text: "GitHub, Hugging Face, Zooniverse", link: "/guide/resources" },
        ],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/Cruuusade/LLM_FOR_ASTRONOMY" },
    ],
    footer: {
      message: "Released under the same terms as the accompanying paper repository.",
      copyright: "Copyright © contributors",
    },
    search: {
      provider: "local",
    },
  },
});
