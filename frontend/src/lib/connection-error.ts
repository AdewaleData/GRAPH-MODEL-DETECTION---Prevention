import { describeApiTarget } from "./config";

export function formatConnectionError(): string {
  const target = describeApiTarget();
  const isLocal = target.includes("127.0.0.1") || target.includes("localhost:8000");

  if (isLocal) {
    return `Cannot reach the API at ${target}. Start the backend (port 8000) or set NEXT_PUBLIC_API_URL to your Render URL in frontend/.env.local, then restart the frontend.`;
  }

  return `Cannot reach the API at ${target}. Confirm Render is Live (/health), set BACKEND_URL and NEXT_PUBLIC_API_URL on Vercel to your Render URL, and set CORS_ORIGINS on Render to your Vercel URL — then redeploy both.`;
}
