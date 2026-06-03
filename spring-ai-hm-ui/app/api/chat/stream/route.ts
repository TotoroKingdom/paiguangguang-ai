const DEFAULT_BACKEND_URL = "http://localhost:8080/ai/chat/stream";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const prompt = searchParams.get("prompt")?.trim();

  if (!prompt) {
    return new Response("Prompt is required.", { status: 400 });
  }

  const backendUrl = new URL(
    process.env.AI_CHAT_BACKEND_URL ?? DEFAULT_BACKEND_URL,
  );
  backendUrl.searchParams.set("prompt", prompt);

  try {
    const upstream = await fetch(backendUrl, {
      cache: "no-store",
      headers: {
        Accept: "text/event-stream, text/plain, */*",
      },
    });

    if (!upstream.ok) {
      const message = await upstream.text().catch(() => "");

      return new Response(
        message || `Backend request failed with status ${upstream.status}.`,
        {
          status: upstream.status,
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
          },
        },
      );
    }

    if (!upstream.body) {
      return new Response("Backend returned an empty stream.", { status: 502 });
    }

    return new Response(upstream.body, {
      headers: {
        "Cache-Control": "no-cache, no-transform",
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  } catch {
    return new Response("Unable to reach the chat backend.", {
      status: 502,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  }
}
