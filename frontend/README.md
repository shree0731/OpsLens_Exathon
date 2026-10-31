# OpsLens Frontend Dashboard

Modern React Single Page Application (SPA) built for **OpsLens** — operational intelligence and data observability on Exasol Personal Edition.

---

## Tech Stack
- **Framework**: Vite + React 18 + TypeScript
- **Styling**: Tailwind CSS + Custom Design Tokens (`tokens.ts`)
- **Graph DAG**: `@xyflow/react` (v12) with `dagre` automatic left-to-right hierarchical layout
- **State & Caching**: `@tanstack/react-query` (auto-refetch every 5s on lineage canvas)
- **Routing**: `react-router-dom` (v7)
- **Charts**: `recharts` for sparklines and trust trends
- **Animations & Icons**: `framer-motion` and `lucide-react`

---

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Development Server (Port 5173)
```bash
npm run dev
```
The app will be accessible at [http://localhost:5173](http://localhost:5173). Requests to `/api` are automatically proxied to the FastAPI backend running at `http://127.0.0.1:8000`.

### 3. Build for Production
```bash
npm run build
```
Generates production build in `dist/`.
