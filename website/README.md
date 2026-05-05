# Benchmark documentation (VitePress)

Sidebar-style docs similar in spirit to [Gymnasium / Farama](https://gymnasium.farama.org/) documentation: left navigation, fast search, static build.

## Commands

```bash
cd website
npm install
npm run dev
```

Visit the local URL printed in the terminal (usually `http://localhost:5173`).

```bash
npm run build    # output: .vitepress/dist
npm run preview  # serve production build locally
```

## Static assets

Example figures for the **Visualizations** page live in `public/figures/` (copied from `results_comparison/report/charts/benchmark_full_apr21/` and an example montage). Re-copy after regenerating charts if you want the site to stay in sync.

## Deploy

Upload `.vitepress/dist` to any static host, or use GitHub Actions / Pages with `npm run build` as the build step and `dist` as the publish directory (repo-relative: `website/.vitepress/dist`).
