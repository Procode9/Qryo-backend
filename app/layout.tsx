import "./globals.css";

export const metadata = {
  title: "Qryo — Quantum Jobs, Simplified",
  description: "Submit a job. We route and run it."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-50">
        {children}
      </body>
    </html>
  );
}