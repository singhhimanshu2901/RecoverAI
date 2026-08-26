# RecoverAI Dashboard

React dashboard for the RecoverAI revenue recovery agent. Connects to the
live backend at `https://recoverai-soqt.onrender.com`.

## Run locally
```
npm install
npm run dev
```

## Deploy on Vercel
1. Push this repo to GitHub (separate repo from the backend, e.g. `recoverai-frontend`).
2. Go to https://vercel.com -> Add New -> Project -> import this repo.
3. Vercel auto-detects Vite. Click Deploy.
4. Live in ~1 minute at `https://<your-app>.vercel.app`

## Deploy on Netlify (alternative)
1. Push to GitHub.
2. https://netlify.com -> Add new site -> Import from GitHub.
3. Build command: `npm run build`, Publish directory: `dist`
4. Deploy.

## Backend URL
The API base URL is set in `src/App.jsx` as the `API` constant. Change it
if your backend URL changes.
