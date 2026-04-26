import { useLocation, useNavigate } from "react-router-dom";
import { useState, useMemo, useEffect, useRef } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis,
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import Navbar from "../layout/Navbar";
import { useAuth } from "../../utils/AuthContext";

import '../../css-files/pages/CodeSandboxPage.css';

interface CodeQuestion {
    question: string;
    starter_code: string;
    test_cases: string[];
    hints?: string[];
    difficulty?: string;
    // AI-generated metadata
    time_limit_ms?: number;
    memory_limit_kb?: number;
    topic_tags?: string[];
    avg_cpu_time_ms?: number;
    avg_memory_kb?: number;
    avg_code_lines?: number;
    // Computed metadata
    desc_char_len?: number;
    desc_word_count?: number;
    num_sample_inputs?: number;
    has_constraints?: boolean;
    num_large_numbers?: number;
    num_code_tokens?: number;
}

interface TestResult {
    test_number: number;
    input: unknown;
    expected: unknown;
    actual: unknown;
    passed?: boolean;
    error?: string;
}

interface QuestionStat {
    index: number;
    solved: boolean;
    attempts: number;       // failed submit attempts before passing
    timeSec: number;        // seconds spent on this question
    solvedCode: string;     // final accepted code
    xpEarned: number;
}

const XP_PER_DIFFICULTY: Record<string, number> = {
    easy: 75,
    medium: 150,
    hard: 250,
};

const codeSessionKey = (userId: number) => `codeSandboxSession_${userId}`;

function CodeSandboxPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, token, updateUser } = useAuth();


    const CODE_SESSION_KEY = user ? codeSessionKey(user.id) : null;

    function getDefaultStub(lang: string): string {
        const lower = lang.toLowerCase();
        if (lower === "python") return "# Write your solution here\n\n";
        if (lower === "java") return "public class Solution {\n    // Write your solution here\n    public int solve() {\n        return 0;\n    }\n}\n";
        if (lower === "c#" || lower === "csharp") return "public class Solution {\n    // Write your solution here\n    public int Solve() {\n        return 0;\n    }\n}\n";
        if (lower === "typescript") return "// Write your solution here\n\nfunction solve(): number {\n    return 0;\n}\n";
        return "// Write your solution here\n\n";
    }

    // Parse saved session once for use in state initializers
    const savedSession = (() => {
        try {
            if (!CODE_SESSION_KEY) return null;
            const raw = sessionStorage.getItem(CODE_SESSION_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    })();

    const isFreshQuiz = Boolean(
        location.state?.quizData?.length &&
        (!savedSession || savedSession.sessionId !== location.state.sessionId)
    );

    const [questions] = useState<CodeQuestion[]>(() => {
        if (isFreshQuiz) return location.state.quizData;
        return savedSession?.questions ?? location.state?.quizData ?? [];
    });

    const [quizPrompt] = useState<string>(() => {
        if (isFreshQuiz) return location.state?.prompt ?? "";
        return savedSession?.quizPrompt ?? location.state?.prompt ?? "";
    });

    const [language] = useState<string>(() => {
        if (isFreshQuiz) return location.state?.language ?? "javascript";
        return savedSession?.language ?? location.state?.language ?? "javascript";
    });

    const [sessionId] = useState<number>(() => {
        if (isFreshQuiz) return location.state.sessionId ?? Date.now();
        return savedSession?.sessionId ?? location.state?.sessionId ?? Date.now();
    });

    const [currentIndex, setCurrentIndex] = useState<number>(() => {
        if (isFreshQuiz) return 0;
        return savedSession?.currentIndex ?? 0;
    });

    const [code, setCode] = useState<string>(() => {
        if (isFreshQuiz) {
            return location.state.quizData[0]?.starter_code || getDefaultStub(location.state?.language ?? "javascript");
        }
        if (savedSession?.code != null) return savedSession.code;
        const qs = savedSession?.questions ?? [];
        const idx = savedSession?.currentIndex ?? 0;
        const lang = savedSession?.language ?? "javascript";
        return qs[idx]?.starter_code || getDefaultStub(lang);
    });

    const [output, setOutput] = useState<string>("");
    const [isRunning, setIsRunning] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Output panel resize
    const [outputHeight, setOutputHeight] = useState(180);
    const isDraggingRef = useRef(false);
    const dragStartYRef = useRef(0);
    const dragStartHeightRef = useRef(0);

    function handleResizeDragStart(e: React.MouseEvent) {
        isDraggingRef.current = true;
        dragStartYRef.current = e.clientY;
        dragStartHeightRef.current = outputHeight;
        e.preventDefault();
    }

    useEffect(() => {
        function onMouseMove(e: MouseEvent) {
            if (!isDraggingRef.current) return;
            const delta = dragStartYRef.current - e.clientY; // drag up = taller output
            const newHeight = Math.max(60, Math.min(500, dragStartHeightRef.current + delta));
            setOutputHeight(newHeight);
        }
        function onMouseUp() {
            isDraggingRef.current = false;
        }
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
        return () => {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
        };
    }, []);

    const [finished, setFinished] = useState<boolean>(() => {
        if (isFreshQuiz) return false;
        return savedSession?.finished ?? false;
    });

    const solvedCountRef = useRef(isFreshQuiz ? 0 : (savedSession?.solvedCount ?? 0));

    // Per-question stats
    const [questionStats, setQuestionStats] = useState<QuestionStat[]>(() =>
        isFreshQuiz ? [] : (savedSession?.questionStats ?? [])
    );
    const [attemptCount, setAttemptCount] = useState(0); // failed attempts for current q
    const questionStartTimeRef = useRef<number>(Date.now());

    // Reward overlay state
    const [showReward, setShowReward] = useState(false);
    const [rewardXp, setRewardXp] = useState(0);
    const [animatedXp, setAnimatedXp] = useState(0);
    const [pendingNextFn, setPendingNextFn] = useState<(() => void) | null>(null);

    // Review mode: browse past solved questions (index into questionStats)
    const [reviewIndex, setReviewIndex] = useState<number | null>(null);

    // Quit confirmation
    const [showQuitConfirm, setShowQuitConfirm] = useState(false);

    // XP counter animation when reward overlay appears
    useEffect(() => {
        if (!showReward) return;
        setAnimatedXp(0);
        let start: number | null = null;
        const duration = 1200;
        function step(ts: number) {
            if (start === null) start = ts;
            const elapsed = ts - start;
            const pct = Math.min(elapsed / duration, 1);
            // ease-out
            setAnimatedXp(Math.round(rewardXp * (1 - Math.pow(1 - pct, 3))));
            if (pct < 1) requestAnimationFrame(step);
        }
        const raf = requestAnimationFrame(step);
        return () => cancelAnimationFrame(raf);
    }, [showReward, rewardXp]);

    // Save coding quiz result when finished
    useEffect(() => {
        if (!finished || !token || !questions.length) return;
        const allTags = [...new Set(questions.flatMap(q => q.topic_tags ?? []))];
        fetch('http://127.0.0.1:8000/save-quiz-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({
                quiz_type: 'coding',
                total_questions: questions.length,
                correct_answers: solvedCountRef.current,
                tags: allTags,
                language: language,
                prompt: quizPrompt || undefined,
            }),
        }).catch(err => console.error('Error saving quiz result:', err));
    }, [finished, token, questions, language, quizPrompt]);

    // Persist session to sessionStorage whenever progress changes.
    // When the quiz is finished, remove the session so a future new quiz is never
    // blocked by a stale finished-state entry.
    useEffect(() => {
        if (!CODE_SESSION_KEY) return;
        if (!questions.length) return;
        if (finished) {
            sessionStorage.removeItem(CODE_SESSION_KEY);
        } else {
            sessionStorage.setItem(CODE_SESSION_KEY, JSON.stringify({
                sessionId,
                questions,
                language,
                currentIndex,
                code,
                finished,
                solvedCount: solvedCountRef.current,
                quizPrompt,
                questionStats,
            }));
        }
    }, [sessionId, questions, language, currentIndex, code, finished, quizPrompt, CODE_SESSION_KEY, questionStats]);

    const languageMap: { [key: string]: string } = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "java": "java",
        "c#": "csharp",
    };

    const currentQ = questions[currentIndex];
    const progress = questions.length > 0 ? ((currentIndex) / questions.length) * 100 : 0;

    // Normalise the AI markdown so ReactMarkdown parses bold/italic/code properly.
    // - Ensure blank lines around headings and fenced code blocks.
    // - Trim each non-code line so JSX indentation doesn't create <pre> blocks.
    const questionMarkdown = useMemo(() => {
        if (!currentQ) return "";
        let md = currentQ.question ?? "";
        // Ensure blank line before headings
        md = md.replace(/([^\n])\n(#{1,3} )/g, "$1\n\n$2");
        // Ensure blank line before fenced code blocks
        md = md.replace(/([^\n])\n```/g, "$1\n\n```");
        // Ensure blank line after closing fenced code blocks
        md = md.replace(/```\n([^\n])/g, "```\n\n$1");
        return md;
    }, [currentQ]);

    function handleQuitQuiz() {
        setShowQuitConfirm(true);
    }

    function confirmQuit() {
        if (CODE_SESSION_KEY) sessionStorage.removeItem(CODE_SESSION_KEY);
        navigate('/prompt');
    }

    // Used on the results screen — no confirmation needed since the quiz is already done
    function handleStartNewChallenge() {
        if (CODE_SESSION_KEY) sessionStorage.removeItem(CODE_SESSION_KEY);
        navigate('/prompt');
    }

    if (!questions.length) {
        return (
            <div className="sandbox-container">
                <Navbar />
                <div className="sandbox-content">
                    <div className="sandbox-empty-state">
                        <p className="sandbox-empty-text">No coding challenge data found. Go back and generate a quiz first.</p>
                        <button
                            className="sandbox-back-button"
                            onClick={handleQuitQuiz}
                        >
                            Back to Prompt
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    function handleNextQuestion() {
        setShowReward(false);
        setPendingNextFn(null);
        setAttemptCount(0);
        questionStartTimeRef.current = Date.now();
        if (currentIndex + 1 < questions.length) {
            setCurrentIndex(currentIndex + 1);
            setCode(questions[currentIndex + 1]?.starter_code || getDefaultStub(language));
            setOutput("");
        } else {
            setFinished(true);
        }
    }

    async function handleRunCode() {
        setIsRunning(true);
        setOutput("Running code...");

        try {
            const response = await fetch("http://127.0.0.1:8000/run-code", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    code: code,
                    language: language
                })
            });

            const result = await response.json();

            if (result.success) {
                setOutput(`✓ Execution successful\n\nOutput:\n${result.output || '(no output)'}`);
            } else {
                setOutput(`✗ Execution failed\n\nError:\n${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            setOutput(`✗ Failed to execute code\n\nError: ${error}`);
        } finally {
            setIsRunning(false);
        }
    }

    async function handleSubmit() {
        setIsSubmitting(true);
        setOutput("Running tests...");

        try {
            const response = await fetch("http://127.0.0.1:8000/submit-code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: code,
                    language: language,
                    test_cases: currentQ.test_cases,
                })
            });

            const result = await response.json();

            if (result.success) {
                solvedCountRef.current += 1;

                // Record stats for this question
                const difficulty = currentQ.difficulty ?? "medium";
                const baseXp = XP_PER_DIFFICULTY[difficulty] ?? 60;
                const penalty = Math.min(attemptCount * 5, baseXp - 10);
                const earned = Math.max(10, baseXp - penalty);
                const timeSec = Math.round((Date.now() - questionStartTimeRef.current) / 1000);

                const stat: QuestionStat = {
                    index: currentIndex,
                    solved: true,
                    attempts: attemptCount,
                    timeSec,
                    solvedCode: code,
                    xpEarned: earned,
                };

                // Persist XP to backend and update auth context so profile bar reflects it live
                // Awaited so reward popup only shows after XP is confirmed assigned
                if (token) {
                    try {
                        const xpRes = await fetch('http://127.0.0.1:8000/add-xp', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                            body: JSON.stringify({ xp_amount: earned }),
                        });
                        if (xpRes.ok) {
                            const data = await xpRes.json();
                            const { xp_gained: _xg, leveled_up: _lu, new_level: _nl, ...updatedUser } = data; // eslint-disable-line @typescript-eslint/no-unused-vars
                            updateUser(updatedUser);
                        }
                    } catch { /* silently ignore network errors */ }
                }

                setQuestionStats(prev => {
                    const updated = [...prev];
                    updated[currentIndex] = stat;
                    return updated;
                });

                let outputText = "✓ All tests passed!\n\n";
                result.test_results.forEach((test: TestResult) => {
                    outputText += `Test ${test.test_number}: ✓ PASSED\n`;
                    outputText += `  Input: ${JSON.stringify(test.input)}\n`;
                    outputText += `  Expected: ${JSON.stringify(test.expected)}\n`;
                    outputText += `  Got: ${JSON.stringify(test.actual)}\n\n`;
                });
                setOutput(outputText);

                // Show reward overlay
                const isLast = currentIndex + 1 >= questions.length;
                setRewardXp(earned);
                setAnimatedXp(0);
                setPendingNextFn(() => isLast
                    ? () => setFinished(true)
                    : handleNextQuestion
                );
                setShowReward(true);
            } else {
                setAttemptCount(prev => prev + 1);
                // Record failed attempt stat (update attempts count, not solved)
                setQuestionStats(prev => {
                    const updated = [...prev];
                    const existing = updated[currentIndex];
                    updated[currentIndex] = {
                        index: currentIndex,
                        solved: false,
                        attempts: (existing?.attempts ?? 0) + 1,
                        timeSec: Math.round((Date.now() - questionStartTimeRef.current) / 1000),
                        solvedCode: existing?.solvedCode ?? "",
                        xpEarned: existing?.xpEarned ?? 0,
                    };
                    return updated;
                });

                let outputText = "✗ Some tests failed\n\n";
                result.test_results.forEach((test: TestResult) => {
                    const status = test.passed ? "✓ PASSED" : "✗ FAILED";
                    outputText += `Test ${test.test_number}: ${status}\n`;
                    outputText += `  Input: ${JSON.stringify(test.input)}\n`;
                    outputText += `  Expected: ${JSON.stringify(test.expected)}\n`;
                    outputText += `  Got: ${JSON.stringify(test.actual)}\n`;
                    if (test.error) outputText += `  Error: ${test.error}\n`;
                    outputText += `\n`;
                });
                setOutput(outputText);
            }
        } catch (error) {
            setOutput(`✗ Failed to submit code\n\nError: ${error}`);
        } finally {
            setIsSubmitting(false);
        }
    }

    if (finished) {
        const totalXp = questionStats.reduce((s, q) => s + (q?.xpEarned ?? 0), 0);
        const solvedCount = questionStats.filter(q => q?.solved).length;
        const totalAttempts = questionStats.reduce((s, q) => s + (q?.attempts ?? 0), 0);
        const avgTimeSec = questionStats.length
            ? Math.round(questionStats.reduce((s, q) => s + (q?.timeSec ?? 0), 0) / questionStats.length)
            : 0;

        const barData = questions.map((_q, i) => ({
            name: `Q${i + 1}`,
            xp: questionStats[i]?.xpEarned ?? 0,
            attempts: questionStats[i]?.attempts ?? 0,
            solved: questionStats[i]?.solved ? 1 : 0,
        }));

        const radarData = [
            { subject: "Solved", value: solvedCount, full: questions.length },
            { subject: "Accuracy", value: solvedCount, full: Math.max(1, solvedCount + totalAttempts) },
            { subject: "Speed", value: Math.max(0, 5 - Math.floor(avgTimeSec / 60)), full: 5 },
        ];

        const diffCounts: Record<string, { solved: number; total: number }> = {};
        questions.forEach((q, i) => {
            const d = q.difficulty ?? "unknown";
            if (!diffCounts[d]) diffCounts[d] = { solved: 0, total: 0 };
            diffCounts[d].total++;
            if (questionStats[i]?.solved) diffCounts[d].solved++;
        });

        if (reviewIndex !== null) {
            const stat = questionStats[reviewIndex];
            const rq = questions[reviewIndex];
            const reviewMarkdown = (() => {
                let md = rq?.question ?? "";
                md = md.replace(/([^\n])\n(#{1,3} )/g, "$1\n\n$2");
                md = md.replace(/([^\n])\n```/g, "$1\n\n```");
                md = md.replace(/```\n([^\n])/g, "```\n\n$1");
                return md;
            })();

            return (
                <div className="sandbox-container">
                    <Navbar />
                    <div className="sandbox-review-layout">
                        <div className="sandbox-review-sidebar">
                            <button className="sandbox-review-back-btn" onClick={() => setReviewIndex(null)}>← Back to Results</button>
                            <p className="sandbox-review-sidebar-title">Questions</p>
                            {questions.map((_, i) => {
                                const s = questionStats[i];
                                return (
                                    <button
                                        key={i}
                                        className={`sandbox-review-q-btn ${i === reviewIndex ? "active" : ""} ${s?.solved ? "solved" : "failed"}`}
                                        onClick={() => setReviewIndex(i)}
                                    >
                                        Q{i + 1} {s?.solved ? "✓" : "✗"}
                                    </button>
                                );
                            })}
                        </div>
                        <div className="sandbox-review-main">
                            <div className="sandbox-review-header">
                                <h2 className="sandbox-review-title">Question {reviewIndex + 1}</h2>
                                <div className="sandbox-review-badges">
                                    {rq?.difficulty && (
                                        <span className={`sandbox-review-diff sandbox-difficulty-${rq.difficulty}`}>{rq.difficulty}</span>
                                    )}
                                    {stat?.solved
                                        ? <span className="sandbox-review-badge-pass">✓ Solved</span>
                                        : <span className="sandbox-review-badge-fail">✗ Not solved</span>
                                    }
                                </div>
                            </div>
                            <div className="sandbox-review-stats-row">
                                <div className="sandbox-review-stat"><span>Attempts</span><strong>{stat?.attempts ?? 0}</strong></div>
                                <div className="sandbox-review-stat"><span>Time</span><strong>{stat?.timeSec ?? 0}s</strong></div>
                                <div className="sandbox-review-stat"><span>XP Earned</span><strong className="xp-text">+{stat?.xpEarned ?? 0}</strong></div>
                            </div>
                            <div className="sandbox-review-panels">
                                <div className="sandbox-review-question">
                                    <h3 className="sandbox-review-section-label">Problem</h3>
                                    <div className="sandbox-markdown-body">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{reviewMarkdown}</ReactMarkdown>
                                    </div>
                                </div>
                                {stat?.solved && stat.solvedCode && (
                                    <div className="sandbox-review-code">
                                        <h3 className="sandbox-review-section-label">Your Solution</h3>
                                        <Editor
                                            height="400px"
                                            language={languageMap[language.toLowerCase()] || "javascript"}
                                            value={stat.solvedCode}
                                            theme="vs-dark"
                                            options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, fontFamily: "'Courier New', monospace", automaticLayout: true, scrollBeyondLastLine: false }}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            );
        }

        return (
            <div className="sandbox-container">
                <Navbar />
                <div className="sandbox-results-layout">
                    <div className="sandbox-results-header">
                        <div className="sandbox-results-trophy">🏆</div>
                        <h1 className="sandbox-results-title">Quiz Complete!</h1>
                        <p className="sandbox-results-subtitle">{language.toUpperCase()} Challenge · {questions.length} Questions</p>
                    </div>

                    {/* Summary stat cards */}
                    <div className="sandbox-results-stats-row">
                        <div className="sandbox-results-stat-card">
                            <span className="sandbox-results-stat-value xp-text">+{totalXp}</span>
                            <span className="sandbox-results-stat-label">XP Earned</span>
                        </div>
                        <div className="sandbox-results-stat-card">
                            <span className="sandbox-results-stat-value">{solvedCount}/{questions.length}</span>
                            <span className="sandbox-results-stat-label">Solved</span>
                        </div>
                        <div className="sandbox-results-stat-card">
                            <span className="sandbox-results-stat-value">{totalAttempts}</span>
                            <span className="sandbox-results-stat-label">Failed Attempts</span>
                        </div>
                        <div className="sandbox-results-stat-card">
                            <span className="sandbox-results-stat-value">{avgTimeSec}s</span>
                            <span className="sandbox-results-stat-label">Avg. Time / Q</span>
                        </div>
                    </div>

                    {/* Difficulty breakdown */}
                    {Object.keys(diffCounts).length > 0 && (
                        <div className="sandbox-results-diff-row">
                            {Object.entries(diffCounts).map(([d, v]) => (
                                <div key={d} className={`sandbox-results-diff-card sandbox-difficulty-${d}`}>
                                    <span className="sandbox-results-diff-name">{d}</span>
                                    <span className="sandbox-results-diff-score">{v.solved}/{v.total}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Charts row */}
                    <div className="sandbox-results-charts-row">
                        {/* XP per question bar chart */}
                        <div className="sandbox-results-chart-box">
                            <h3 className="sandbox-results-chart-title">XP per Question</h3>
                            <ResponsiveContainer width="100%" height={200}>
                                <BarChart data={barData} barCategoryGap="30%">
                                    <XAxis dataKey="name" stroke="#808080" tick={{ fontFamily: "'Fira Code',monospace", fontSize: 11 }} />
                                    <YAxis stroke="#808080" tick={{ fontFamily: "'Fira Code',monospace", fontSize: 11 }} />
                                    <Tooltip
                                        contentStyle={{ background: "#252526", border: "1px solid #3d3d3d", borderRadius: 8, fontFamily: "'Fira Code',monospace", fontSize: 12 }}
                                        labelStyle={{ color: "#ff9500" }}
                                        itemStyle={{ color: "#e0e0e0" }}
                                    />
                                    <Bar dataKey="xp" radius={[6, 6, 0, 0]}>
                                        {barData.map((entry: { xp: number; attempts: number; solved: number }, i) => (
                                            <Cell key={i} fill={entry.solved ? "#ff9500" : "#3d3d3d"} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Failed attempts per question */}
                        <div className="sandbox-results-chart-box">
                            <h3 className="sandbox-results-chart-title">Failed Attempts / Question</h3>
                            <ResponsiveContainer width="100%" height={200}>
                                <BarChart data={barData} barCategoryGap="30%">
                                    <XAxis dataKey="name" stroke="#808080" tick={{ fontFamily: "'Fira Code',monospace", fontSize: 11 }} />
                                    <YAxis allowDecimals={false} stroke="#808080" tick={{ fontFamily: "'Fira Code',monospace", fontSize: 11 }} />
                                    <Tooltip
                                        contentStyle={{ background: "#252526", border: "1px solid #3d3d3d", borderRadius: 8, fontFamily: "'Fira Code',monospace", fontSize: 12 }}
                                        labelStyle={{ color: "#ff9500" }}
                                        itemStyle={{ color: "#e0e0e0" }}
                                    />
                                    <Bar dataKey="attempts" radius={[6, 6, 0, 0]}>
                                        {barData.map((entry: { xp: number; attempts: number; solved: number }, i) => (
                                            <Cell key={i} fill={entry.attempts === 0 ? "#2ecc71" : entry.attempts <= 2 ? "#f39c12" : "#e74c3c"} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Radar overview */}
                        <div className="sandbox-results-chart-box">
                            <h3 className="sandbox-results-chart-title">Performance Overview</h3>
                            <ResponsiveContainer width="100%" height={200}>
                                <RadarChart data={radarData} outerRadius={70}>
                                    <PolarGrid stroke="#3d3d3d" />
                                    <PolarAngleAxis dataKey="subject" tick={{ fill: "#808080", fontFamily: "'Fira Code',monospace", fontSize: 11 }} />
                                    <Radar name="score" dataKey="value" stroke="#ff9500" fill="#ff9500" fillOpacity={0.35} />
                                </RadarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Per-question review list */}
                    <div className="sandbox-results-qlist">
                        <h3 className="sandbox-results-qlist-title">Question Breakdown — click to review</h3>
                        {questions.map((q, i) => {
                            const s = questionStats[i];
                            return (
                                <button
                                    key={i}
                                    className={`sandbox-results-qrow ${s?.solved ? "solved" : "failed"}`}
                                    onClick={() => setReviewIndex(i)}
                                >
                                    <span className="sandbox-results-qrow-num">Q{i + 1}</span>
                                    <span className={`sandbox-results-qrow-status ${s?.solved ? "pass" : "fail"}`}>{s?.solved ? "✓ Solved" : "✗ Failed"}</span>
                                    {q.difficulty && <span className={`sandbox-results-qrow-diff sandbox-difficulty-${q.difficulty}`}>{q.difficulty}</span>}
                                    <span className="sandbox-results-qrow-attempts">{s?.attempts ?? 0} failed attempt{s?.attempts !== 1 ? "s" : ""}</span>
                                    <span className="sandbox-results-qrow-time">{s?.timeSec ?? 0}s</span>
                                    <span className="sandbox-results-qrow-xp xp-text">+{s?.xpEarned ?? 0} XP</span>
                                    <span className="sandbox-results-qrow-arrow">›</span>
                                </button>
                            );
                        })}
                    </div>

                    <div className="sandbox-results-actions">
                        <button className="sandbox-back-button" onClick={handleStartNewChallenge}>
                            Start New Challenge
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="sandbox-container">
            <Navbar />

            {/* Quit confirmation popup */}
            {showQuitConfirm && (
                <div className="sandbox-quit-overlay">
                    <div className="sandbox-quit-modal">
                        <h3 className="sandbox-quit-modal-title">Exit Quiz?</h3>
                        <p className="sandbox-quit-modal-body">Your progress will be lost. Are you sure you want to quit?</p>
                        <div className="sandbox-quit-modal-actions">
                            <button className="sandbox-quit-modal-cancel" onClick={() => setShowQuitConfirm(false)}>Keep Playing</button>
                            <button className="sandbox-quit-modal-confirm" onClick={confirmQuit}>Yes, Exit</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Reward overlay */}
            {showReward && (
                <div className="sandbox-reward-overlay">
                    <div className="sandbox-reward-card">
                        <div className="sandbox-reward-burst">✓</div>
                        <h2 className="sandbox-reward-title">All Tests Passed!</h2>
                        <p className="sandbox-reward-sub">Question {currentIndex + 1} of {questions.length} solved</p>
                        <div className="sandbox-reward-xp-row">
                            <span className="sandbox-reward-xp-label">XP Earned</span>
                            <span className="sandbox-reward-xp-value">+{animatedXp}</span>
                        </div>
                        {attemptCount > 0 && (
                            <p className="sandbox-reward-penalty-note">({attemptCount} failed attempt{attemptCount !== 1 ? "s" : ""} — penalty applied)</p>
                        )}
                        <div className="sandbox-reward-stats">
                            <div className="sandbox-reward-stat">
                                <span>Difficulty</span>
                                <strong className={`sandbox-difficulty-${currentQ?.difficulty ?? "medium"}`}>
                                    {currentQ?.difficulty ?? "medium"}
                                </strong>
                            </div>
                            <div className="sandbox-reward-stat">
                                <span>Time</span>
                                <strong>{Math.round((Date.now() - questionStartTimeRef.current) / 1000)}s</strong>
                            </div>
                            <div className="sandbox-reward-stat">
                                <span>Attempts</span>
                                <strong>{attemptCount + 1}</strong>
                            </div>
                        </div>
                        <div className="sandbox-reward-actions">
                            {currentIndex + 1 < questions.length ? (
                                <button
                                    className="sandbox-reward-next-btn"
                                    onClick={() => pendingNextFn && pendingNextFn()}
                                >
                                    Next Question →
                                </button>
                            ) : (
                                <button
                                    className="sandbox-reward-finish-btn"
                                    onClick={() => pendingNextFn && pendingNextFn()}
                                >
                                    See Results 🏆
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
            <div className="sandbox-main">
                {/* Left Panel - Editor */}
                <div className="sandbox-editor-panel">
                    <div className="sandbox-editor-header">
                        <span className="sandbox-language-badge">{language.toUpperCase()}</span>
                        <button className="sandbox-quit-button" onClick={handleQuitQuiz}>
                            ✕ Exit Quiz
                        </button>
                    </div>

                    <div className="sandbox-editor-wrapper">
                        <Editor
                            key={currentIndex}
                            height="100%"
                            language={languageMap[language.toLowerCase()] || "javascript"}
                            value={code}
                            onChange={(value) => setCode(value ?? "")}
                            theme="vs-dark"
                            options={{
                                fontSize: 13,
                                fontFamily: "'Courier New', Courier, monospace",
                                fontLigatures: false,
                                minimap: { enabled: false },
                                scrollBeyondLastLine: false,
                                padding: { top: 16, bottom: 16 },
                                lineNumbers: "on",
                                roundedSelection: false,
                                automaticLayout: true,
                                letterSpacing: 0,
                                lineHeight: 19,
                                renderWhitespace: "none",
                                smoothScrolling: false,
                                cursorBlinking: "solid",
                                cursorSmoothCaretAnimation: "off",
                                cursorStyle: "line",
                                cursorWidth: 2,
                            }}
                        />
                    </div>

                    {/* Drag handle to resize output panel */}
                    <div
                        className="sandbox-output-resize-handle"
                        onMouseDown={handleResizeDragStart}
                        title="Drag to resize output"
                    />

                    <div className="sandbox-output-section" style={{ height: outputHeight }}>
                        <h3 className="sandbox-output-title">Output</h3>
                        <div className="sandbox-output-box">
                            <pre>{output || "Run your code to see output..."}</pre>
                        </div>
                    </div>

                    <div className="sandbox-button-group">
                        <button
                            className="sandbox-run-button"
                            onClick={handleRunCode}
                            disabled={isRunning || isSubmitting}
                        >
                            {isRunning ? "Running..." : "Run Code"}
                        </button>
                        <button
                            className="sandbox-submit-button"
                            onClick={handleSubmit}
                            disabled={isRunning || isSubmitting}
                        >
                            {isSubmitting ? "Submitting..." : "Submit Solution"}
                        </button>
                    </div>
                </div>

                {/* Right Panel - Question */}
                <div className="sandbox-question-panel">
                    {/* XP Status Bar */}
                    {user && (
                        <div className="sandbox-xp-bar">
                            <span className="sandbox-xp-level">LVL {user.level}</span>
                            <div className="sandbox-xp-track">
                                <div
                                    className="sandbox-xp-fill"
                                    style={{ width: `${(user.exp / (user.xp_required ?? 100)) * 100}%` }}
                                />
                            </div>
                            <span className="sandbox-xp-text">{user.exp}/{user.xp_required ?? 100} XP</span>
                        </div>
                    )}

                    <div className="sandbox-progress-section">
                        <p className="sandbox-progress-text">
                            Question {currentIndex + 1} of {questions.length}
                        </p>
                        <div className="sandbox-progress-bar">
                            <div
                                className="sandbox-progress-fill"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>

                    <div className="sandbox-question-content">
                        <div className="sandbox-challenge-header">
                            <h2 className="sandbox-question-title">Challenge</h2>
                        </div>

                        {/* Difficulty Banner */}
                        {currentQ.difficulty && (
                            <div className={`sandbox-difficulty-banner sandbox-difficulty-${currentQ.difficulty}`}>
                                <span className="sandbox-difficulty-label">Difficulty</span>
                                <span className="sandbox-difficulty-value">{currentQ.difficulty}</span>
                            </div>
                        )}

                        {/* Problem Metadata Panel */}
                        {(currentQ.time_limit_ms || currentQ.topic_tags?.length) && (
                            <div className="sandbox-meta-panel">
                                <p className="sandbox-meta-note">These are reference targets for an efficient solution — there is no time limit on your attempt.</p>
                                <div className="sandbox-meta-row">
                                    {currentQ.time_limit_ms && (
                                        <div className="sandbox-meta-stat">
                                            <span className="sandbox-meta-label">Target Runtime</span>
                                            <span className="sandbox-meta-value">{currentQ.time_limit_ms} ms</span>
                                        </div>
                                    )}
                                    {currentQ.memory_limit_kb && (
                                        <div className="sandbox-meta-stat">
                                            <span className="sandbox-meta-label">Memory Budget</span>
                                            <span className="sandbox-meta-value">{currentQ.memory_limit_kb >= 1024 ? `${currentQ.memory_limit_kb / 1024} MB` : `${currentQ.memory_limit_kb} KB`}</span>
                                        </div>
                                    )}
                                    {currentQ.avg_cpu_time_ms != null && currentQ.avg_cpu_time_ms > 0 && (
                                        <div className="sandbox-meta-stat">
                                            <span className="sandbox-meta-label">Typical CPU</span>
                                            <span className="sandbox-meta-value">{currentQ.avg_cpu_time_ms} ms</span>
                                        </div>
                                    )}
                                    {currentQ.avg_memory_kb != null && currentQ.avg_memory_kb > 0 && (
                                        <div className="sandbox-meta-stat">
                                            <span className="sandbox-meta-label">Typical Memory</span>
                                            <span className="sandbox-meta-value">{currentQ.avg_memory_kb >= 1024 ? `${(currentQ.avg_memory_kb / 1024).toFixed(1)} MB` : `${currentQ.avg_memory_kb} KB`}</span>
                                        </div>
                                    )}
                                    {currentQ.avg_code_lines != null && currentQ.avg_code_lines > 0 && (
                                        <div className="sandbox-meta-stat">
                                            <span className="sandbox-meta-label">Typical Length</span>
                                            <span className="sandbox-meta-value">{currentQ.avg_code_lines} lines</span>
                                        </div>
                                    )}
                                </div>
                                {currentQ.topic_tags && currentQ.topic_tags.length > 0 && (
                                    <div className="sandbox-meta-tags">
                                        {currentQ.topic_tags.map((tag) => (
                                            <span key={tag} className="sandbox-meta-tag">{tag.replace(/_/g, ' ')}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                        <div className="sandbox-markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {questionMarkdown}
                            </ReactMarkdown>
                        </div>

                        {currentQ.test_cases && currentQ.test_cases.length > 0 && (
                            <div className="sandbox-test-cases">
                                <h3 className="sandbox-section-title">Test Cases</h3>
                                {currentQ.test_cases.map((testCase, idx) => (
                                    <div key={idx} className="sandbox-test-case">
                                        <code>{testCase}</code>
                                    </div>
                                ))}
                            </div>
                        )}

                    </div>
                </div>
            </div>
        </div>
    );
}

export default CodeSandboxPage;
