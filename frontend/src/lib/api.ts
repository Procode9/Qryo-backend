const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error("API request failed");
  }
  return res.json();
}