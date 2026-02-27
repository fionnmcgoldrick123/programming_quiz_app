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

const fetchCodingHint = async (
    question: string,
    studentCode: string,
    starterCode: string,
    testCases: string[],
    language: string
): Promise<void> => {
    setLoading(true);
    const res = await fetch("http://localhost:8000/hint/coding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            question,
            student_code: studentCode,
            starter_code: starterCode,
            test_cases: testCases,
            language,
        }),
    });
    const data = await res.json();
    setHints(data.hints);
    setLoading(false);
};

  const clearHints = (): void => setHints([]);

  return { hints, loading, fetchMcqHint, fetchCodingHint, clearHints };
}