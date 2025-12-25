"use client";

import { useMemo, useState } from "react";

type ApiResult = {
  ok: boolean;
  urlTried: string;
  status?: number;
  bodyPreview?: string;
  error?: string;
};

function safePreview(text: string, max = 800) {
  const trimmed = text.trim();
  return trimmed.length > max ? trimmed.slice(0, max) + "…" : trimmed;
}

export default function Home() {
  const apiBase = useMemo(() => {
    const v = process.env.NEXT_PUBLIC_API_BASE_URL;
    return (v && v.trim()) ? v.trim().replace(/\/+$/, "") : "https://qryo-backend.onrender.com";
  }, []);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ApiResult | null>(null);

  async function tryFetch(path: string): Promise<ApiResult> {
    const url = `${apiBase}${path}`;
    try {
      const res = await fetch(url, {
        method: "GET",
        headers: { "Accept": "application/json, text/plain;q=0.9, */*;q=0.8" },
        cache: "no-store"
      });

      const text = await res.text();
      return {
        ok: res.ok,
        urlTried: url,
        status: res.status,
        bodyPreview: safePreview(text)
      };
    } catch (e: any) {
      return {
        ok: false,
        urlTried: url,
        error: e?.message || "Fetch failed"
      };
    }
  }

  async function runDemo() {
    setLoading(true);
    setResult(null);

    // Önce /health deneriz; yoksa root / deneriz (backend’in / GET 200 verdiğini görmüştük)
    const first = await tryFetch("/health");
    if (first.ok) {
      setResult(first);
      setLoading(false);
      return;
    }

    const fallback = await tryFetch("/");
    setResult(fallback);
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-5xl px-5 py-10">
      <div className="rounded-3xl border border-zinc-800 bg-zinc-900/30 p-6 shadow-sm">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-xs text-zinc-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Live demo — frontend on Vercel, backend on Render
            </div>

            <h1 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">
              Quantum jobs, simplified.
            </h1>

            <p className="mt-3 text-zinc-300 md:text-lg">
              Tek tıkla backend’e canlı istek at. Sonucu ekranda gör. Sonraki adımda bunu “job submit” akışına çeviriyoruz.
            </p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                onClick={runDemo}
                disabled={loading}
                className="rounded-2xl bg-white px-5 py-3 text-sm font-medium text-zinc-950 hover:opacity-90 disabled:opacity-60"
              >
                {loading ? "Running…" : "Run Demo Call"}
              </button>

              <div className="text-xs text-zinc-400">
                API Base: <span className="text-zinc-200">{apiBase}</span>
              </div>
            </div>
          </div>

          <div className="w-full md:w-[420px]">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
              <div className="text-sm font-medium text-zinc-100">Result</div>
              <div className="mt-2 text-xs text-zinc-400">
                Önce <code>/health</code> denenir, olmazsa <code>/</code> denenir.
              </div>

              <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-3">
                {!result ? (
                  <div className="text-sm text-zinc-400">
                    Henüz istek yok. “Run Demo Call” bas.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-xs text-zinc-400">
                      Tried: <span className="text-zinc-200">{result.urlTried}</span>
                    </div>
                    {"status" in result && typeof result.status === "number" && (
                      <div className="text-xs text-zinc-400">
                        Status: <span className="text-zinc-200">{result.status}</span>
                      </div>
                    )}
                    {result.error ? (
                      <div className="text-sm text-red-300">{result.error}</div>
                    ) : (
                      <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs text-zinc-200">
{result.bodyPreview || "(empty response)"}
                      </pre>
                    )}
                  </div>
                )}
              </div>

              <div className="mt-4 text-xs text-zinc-400">
                Sonraki adım: backend’de “job submit” endpoint’i netleşince bu buton POST atacak.
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
            <div className="text-sm font-medium">1) Landing</div>
            <div className="mt-1 text-xs text-zinc-400">Ne olduğunu 2 saniyede anlatır.</div>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
            <div className="text-sm font-medium">2) Live Call</div>
            <div className="mt-1 text-xs text-zinc-400">Frontend → Backend gerçek istek.</div>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
            <div className="text-sm font-medium">3) Upgrade</div>
            <div className="mt-1 text-xs text-zinc-400">Bunu “job submit” akışına çeviririz.</div>
          </div>
        </div>
      </div>

      <footer className="mt-8 text-center text-xs text-zinc-500">
        Qryo • Minimal MVP • Next.js + Vercel
      </footer>
    </main>
  );
}