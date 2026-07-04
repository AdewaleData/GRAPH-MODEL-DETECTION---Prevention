import { NextResponse } from "next/server";

/** Exposes backend URL to the browser for WebSockets (server-only env vars). */
export function GET() {
  const http = (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");

  return NextResponse.json({
    apiUrl: http,
    wsUrl: http.replace(/^http/, "ws"),
  });
}
