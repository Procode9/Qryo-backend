"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

export default function HomePage() {
  const [status, setStatus] = useState<string>("loading...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet("/")
      .then((data) => {
        setStatus(JSON.stringify(data));
      })
      .catch((err) => {
        console.error(err);
        setError("Backend bağlantısı başarısız");
      });
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0b1020",
        color: "white",
        fontFamily: "system-ui",
      }}
    >
      <div
        style={{
          maxWidth: 600,
          padding: 32,
          borderRadius: 12,
          background: "rgba(255,255,255,0.05)",
          boxShadow: "0 10px 40px rgba(0,0,0,0.4)",
        }}
      >
        <h1 style={{ fontSize: 32, marginBottom: 16 }}>Qryo</h1>

        <p style={{ opacity: 0.8, marginBottom: 24 }}>
          Serverless Quantum Job Submission API
        </p>

        <div
          style={{
            padding: 16,
            borderRadius: 8,
            background: "rgba(0,0,0,0.4)",
            fontFamily: "monospace",
            fontSize: 14,
          }}
        >
          {error ? (
            <span style={{ color: "#ff6b6b" }}>{error}</span>
          ) : (
            <>
              <strong>Backend response:</strong>
              <pre style={{ marginTop: 8 }}>{status}</pre>
            </>
          )}
        </div>
      </div>
    </main>
  );
}