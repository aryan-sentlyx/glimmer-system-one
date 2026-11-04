# demo

The judge-facing web demo. One Modal app serves the built frontend and the `/api/*` routes.

Live: https://aryan-59489--glimmer-demo.us-east.modal.run

| Folder | What |
|---|---|
| `frontend/` | Vite, React 19, TypeScript, Tailwind CSS v4. Four tabs: Playground, Benchmark, API, Model card. |
| `backend/` | FastAPI on Modal, CPU only. Calls the GPU class by name. See `backend/README.md`. |

## Develop

```
cd frontend && npm install && npm run dev      # http://localhost:5173, proxies /api to the live backend
```

Set `VITE_BACKEND` to point the proxy at another backend, for example `modal serve` in `backend/`.

## Deploy

```
cd frontend && npm run build                   # writes frontend/dist
cd ../backend && uv run modal deploy app.py    # bundles frontend/dist and deploys
```

The backend reads `frontend/dist` at deploy time. Build first, then deploy.

## Frontend files

| File | What |
|---|---|
| `src/App.tsx` | State: tab, model card, examples, GPU state, form, result. Wakes the GPU on load and polls `/api/health` until warm. |
| `src/components/Playground.tsx` | The example strip, the context card (image drop and state text), the questions box (one question per line, parsed live), the Run bar, the Advanced fold (object, JSON keys, heads, gates, request JSON), and the output panel with the threshold slider. |
| `src/components/Answers.tsx` | The three answer views: noul bar, choice rows, score distribution, plus the timing line. |
| `src/components/Benchmark.tsx`, `Api.tsx`, `ModelCardView.tsx` | The other tabs. All read `/api/model`. |
| `src/form.ts` | Parses the questions box, one line per question: a statement is a noul, `[a, b, c]` is a choice, `[a < b < c]` is a score. A noul line about a defect gets the trained head when an image is present. Converts between the lines and the API body. The head names live in `HEADS`. |
| `src/api.ts` | The four API calls and the client-side resize to 448 px. |
| `src/index.css` | The theme tokens: warm charcoal neutrals, amber signal, one color per question type. IBM Plex fonts. |
