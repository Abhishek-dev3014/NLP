import { NextRequest } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (path.some((p) => p === ".." || p === "." || /[\\/]/.test(p)))
    return Response.json({ detail: "Invalid API path" }, { status: 400 });
  const base = (process.env.API_BASE_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
  try {
    const body = ["GET", "HEAD"].includes(request.method)
      ? undefined
      : await request.arrayBuffer();
    if (body && body.byteLength > 5 * 1024 * 1024 + 65536)
      return Response.json(
        { detail: "Files must be 5 MB or smaller." },
        { status: 413 },
      );
    const headers = new Headers();
    for (const key of ["content-type", "cookie", "origin"]) {
      const value = request.headers.get(key);
      if (value) headers.set(key, value);
    }
    const upstream = await fetch(
      `${base}/api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body,
        signal: AbortSignal.timeout(40000),
        cache: "no-store",
        redirect: "manual",
      },
    );
    const responseHeaders = new Headers({ "Cache-Control": "no-store" });
    for (const key of ["content-type", "set-cookie", "retry-after"]) {
      const value = upstream.headers.get(key);
      if (value) responseHeaders.set(key, value);
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      {
        detail:
          "The analysis service is unavailable. Start the FastAPI backend and try again.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
