import { useState } from "react";

export function useHint() {
  const [hints, setHints] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchMcqHint = async (question: string, options: string[]): Promise<void> => {
    setLoading(true);
    const res = await fetch("http://localhost:8000/hint/mcq", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, options }),
    });
    const data = await res.json();
    setHints(data.hints);
    setLoading(false);
  };

  const clearHints = (): void => setHints([]);

  return { hints, loading, fetchMcqHint, clearHints };
}