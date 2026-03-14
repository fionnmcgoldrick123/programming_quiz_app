import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../utils/AuthContext";
import Navbar from "./Navbar";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    RadialBarChart, RadialBar,
} from "recharts";
import '../css-files/StatsPage.css';

interface TagStat { name: string; count: number; }
interface LangStat { name: string; count: number; }
interface RecentQuiz {
    quiz_type: string;
    total_questions: number;
    correct_answers: number;
    tags: string[];
    language: string | null;
    prompt: string | null;
    completed_at: string | null;
}

interface UserStats {
    total_quizzes: number;
    total_questions: number;
    total_correct: number;
    total_wrong: number;
    mcq_quizzes: number;
    coding_quizzes: number;
    accuracy: number;
    tags: TagStat[];
    languages: LangStat[];
    recent: RecentQuiz[];
}

const ORANGE_PALETTE = [
    "#ff9500", "#ff7700", "#ffb347", "#e68a00",
    "#ffd699", "#cc7000", "#ffcc80", "#b35900",
    "#ffe0b2", "#994d00",
];

const PIE_COLORS = ["#ff9500", "#6c63ff"];

function StatsPage() {
    const navigate = useNavigate();
    const { user, token, isAuthenticated, isLoading: authLoading } = useAuth();
    const [stats, setStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (authLoading) return;
        if (!isAuthenticated || !token) { navigate("/login"); return; }

        (async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/user-stats", {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) throw new Error("Failed to load stats");
                setStats(await res.json());
            } catch {
                setError("Could not load your statistics.");
            } finally {
                setLoading(false);
            }
        })();
    }, [authLoading, isAuthenticated, token, navigate]);

    if (authLoading || loading) {
        return (
            <>
                <Navbar />
                <div className="stats-page">
                    <div className="stats-loading">
                        <div className="stats-spinner" />
                        <p>Loading your stats…</p>
                    </div>
                </div>
            </>
        );
    }

    if (error || !stats) {
        return (
            <>
                <Navbar />
                <div className="stats-page">
                    <div className="stats-error">
                        <p>{error || "Something went wrong."}</p>
                        <button className="stats-btn" onClick={() => navigate("/profile")}>Back to Profile</button>
                    </div>
                </div>
            </>
        );
    }

    const hasData = stats.total_quizzes > 0;

    // Chart data
    const correctWrongData = [
        { name: "Correct", value: stats.total_correct },
        { name: "Wrong", value: stats.total_wrong },
    ];

    const quizTypeData = [
        { name: "MCQ", value: stats.mcq_quizzes },
        { name: "Coding", value: stats.coding_quizzes },
    ];

    const accuracyData = [
        { name: "Accuracy", value: stats.accuracy, fill: "#ff9500" },
    ];

    const formatDate = (iso: string | null) => {
        if (!iso) return "";
        const d = new Date(iso);
        return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    };

    return (
        <>
            <Navbar />
            <div className="stats-page">
                <div className="stats-container">
                    {/* Header */}
                    <div className="stats-header">
                        <button className="stats-back-btn" onClick={() => navigate("/profile")}>← Back</button>
                        <h1 className="stats-title">
                            {user?.first_name}'s Statistics
                        </h1>
                        <span className="stats-subtitle">Your performance at a glance</span>
                    </div>

                    {!hasData ? (
                        <div className="stats-empty">
                            <div className="stats-empty-icon"></div>
                            <h2>No stats yet</h2>
                            <p>Complete your first quiz and your statistics will appear here!</p>
                            <button className="stats-btn" onClick={() => navigate("/prompt")}>Take a Quiz</button>
                        </div>
                    ) : (
                        <>
                            {/* KPI Cards */}
                            <div className="stats-kpi-row">
                                <div className="stats-kpi-card">
                                    <span className="kpi-icon kpi-icon--quizzes">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>
                                            <path d="M9 17v1a3 3 0 0 0 6 0v-1"/>
                                            <path d="M8 14h8"/>
                                        </svg>
                                    </span>
                                    <span className="kpi-value">{stats.total_quizzes}</span>
                                    <span className="kpi-label">Quizzes Taken</span>
                                </div>
                                <div className="stats-kpi-card">
                                    <span className="kpi-icon kpi-icon--questions">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <circle cx="12" cy="12" r="10"/>
                                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                                            <circle cx="12" cy="17" r="0.5" fill="currentColor"/>
                                        </svg>
                                    </span>
                                    <span className="kpi-value">{stats.total_questions}</span>
                                    <span className="kpi-label">Questions Completed</span>
                                </div>
                                <div className="stats-kpi-card stats-kpi-card--correct">
                                    <span className="kpi-icon kpi-icon--correct">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="20 6 9 17 4 12"/>
                                        </svg>
                                    </span>
                                    <span className="kpi-value">{stats.total_correct}</span>
                                    <span className="kpi-label">Correct Answers</span>
                                </div>
                                <div className="stats-kpi-card stats-kpi-card--wrong">
                                    <span className="kpi-icon kpi-icon--wrong">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                            <line x1="18" y1="6" x2="6" y2="18"/>
                                            <line x1="6" y1="6" x2="18" y2="18"/>
                                        </svg>
                                    </span>
                                    <span className="kpi-value">{stats.total_wrong}</span>
                                    <span className="kpi-label">Wrong Answers</span>
                                </div>
                            </div>

                            {/* Charts Row 1 */}
                            <div className="stats-charts-row">
                                {/* Accuracy Gauge */}
                                <div className="stats-chart-card">
                                    <h3 className="chart-title">Accuracy</h3>
                                    <div className="chart-wrapper chart-wrapper--gauge">
                                        <ResponsiveContainer width="100%" height={200}>
                                            <RadialBarChart
                                                cx="50%" cy="50%"
                                                innerRadius="70%" outerRadius="90%"
                                                startAngle={180} endAngle={0}
                                                barSize={14}
                                                data={accuracyData}
                                            >
                                                <RadialBar
                                                    dataKey="value"
                                                    cornerRadius={8}
                                                    background={{ fill: "#3d3d3d" }}
                                                />
                                            </RadialBarChart>
                                        </ResponsiveContainer>
                                        <div className="gauge-label">
                                            <span className="gauge-value">{stats.accuracy}%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Correct vs Wrong donut */}
                                <div className="stats-chart-card">
                                    <h3 className="chart-title">Correct vs Wrong</h3>
                                    <div className="chart-wrapper">
                                        <ResponsiveContainer width="100%" height={220}>
                                            <PieChart>
                                                <Pie
                                                    data={correctWrongData}
                                                    cx="50%" cy="50%"
                                                    innerRadius={55} outerRadius={85}
                                                    paddingAngle={4}
                                                    dataKey="value"
                                                    stroke="none"
                                                >
                                                    <Cell fill="#4caf50" />
                                                    <Cell fill="#f44336" />
                                                </Pie>
                                                <Tooltip
                                                    contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }}
                                                    itemStyle={{ color: "#e0e0e0" }}
                                                />
                                            </PieChart>
                                        </ResponsiveContainer>
                                        <div className="pie-legend">
                                            <span className="legend-dot" style={{ background: "#4caf50" }} /> Correct
                                            <span className="legend-dot" style={{ background: "#f44336", marginLeft: 16 }} /> Wrong
                                        </div>
                                    </div>
                                </div>

                                {/* Quiz Type Split */}
                                <div className="stats-chart-card">
                                    <h3 className="chart-title">Quiz Types</h3>
                                    <div className="chart-wrapper">
                                        <ResponsiveContainer width="100%" height={220}>
                                            <PieChart>
                                                <Pie
                                                    data={quizTypeData}
                                                    cx="50%" cy="50%"
                                                    innerRadius={55} outerRadius={85}
                                                    paddingAngle={4}
                                                    dataKey="value"
                                                    stroke="none"
                                                >
                                                    {quizTypeData.map((_, i) => (
                                                        <Cell key={i} fill={PIE_COLORS[i]} />
                                                    ))}
                                                </Pie>
                                                <Tooltip
                                                    contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }}
                                                    itemStyle={{ color: "#e0e0e0" }}
                                                />
                                            </PieChart>
                                        </ResponsiveContainer>
                                        <div className="pie-legend">
                                            <span className="legend-dot" style={{ background: PIE_COLORS[0] }} /> MCQ
                                            <span className="legend-dot" style={{ background: PIE_COLORS[1], marginLeft: 16 }} /> Coding
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Charts Row 2 */}
                            <div className="stats-charts-row">
                                {/* Topic Tags Bar Chart */}
                                {stats.tags.length > 0 && (
                                    <div className="stats-chart-card stats-chart-card--wide">
                                        <h3 className="chart-title">Top Topics</h3>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={280}>
                                                <BarChart data={stats.tags} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#3d3d3d" />
                                                    <XAxis type="number" allowDecimals={false} tick={{ fill: "#888", fontFamily: "'Fira Code', monospace", fontSize: 12 }} />
                                                    <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#ccc", fontFamily: "'Fira Code', monospace", fontSize: 12 }} />
                                                    <Tooltip
                                                        contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }}
                                                        itemStyle={{ color: "#ff9500" }}
                                                        cursor={{ fill: "rgba(255,149,0,0.08)" }}
                                                    />
                                                    <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={18}>
                                                        {stats.tags.map((_, i) => (
                                                            <Cell key={i} fill={ORANGE_PALETTE[i % ORANGE_PALETTE.length]} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Languages Pie */}
                                {stats.languages.length > 0 && (
                                    <div className="stats-chart-card">
                                        <h3 className="chart-title">Preferred Languages</h3>
                                        <div className="chart-wrapper">
                                            <ResponsiveContainer width="100%" height={240}>
                                                <PieChart>
                                                    <Pie
                                                        data={stats.languages}
                                                        cx="50%" cy="50%"
                                                        innerRadius={50} outerRadius={80}
                                                        paddingAngle={3}
                                                        dataKey="count"
                                                        stroke="none"
                                                        label={({ name }) => name}
                                                    >
                                                        {stats.languages.map((_, i) => (
                                                            <Cell key={i} fill={ORANGE_PALETTE[i % ORANGE_PALETTE.length]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip
                                                        contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }}
                                                        itemStyle={{ color: "#e0e0e0" }}
                                                    />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Recent Activity */}
                            {stats.recent.length > 0 && (
                                <div className="stats-recent">
                                    <h3 className="chart-title">Recent Activity</h3>
                                    <div className="recent-list">
                                        {stats.recent.map((r, i) => (
                                            <div className="recent-item" key={i}>
                                                <div className={`recent-icon recent-icon--${r.quiz_type}`}>
                                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    {r.quiz_type === "mcq" ? (
                                                        <>
                                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                                            <polyline points="14 2 14 8 20 8"/>
                                                            <line x1="8" y1="13" x2="16" y2="13"/>
                                                            <line x1="8" y1="17" x2="12" y2="17"/>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <polyline points="16 18 22 12 16 6"/>
                                                            <polyline points="8 6 2 12 8 18"/>
                                                        </>
                                                    )}
                                                </svg>
                                            </div>
                                                <div className="recent-info">
                                                    <span className="recent-type">
                                                        {r.quiz_type === "mcq" ? "MCQ Quiz" : `Coding (${r.language})`}
                                                    </span>
                                                    <span className="recent-score">
                                                        {r.correct_answers}/{r.total_questions} correct
                                                    </span>
                                                    {r.prompt && (
                                                        <span className="recent-prompt">"{r.prompt}"</span>
                                                    )}
                                                </div>
                                                {r.tags.length > 0 && (
                                                    <div className="recent-tags">
                                                        {r.tags.slice(0, 3).map(t => (
                                                            <span key={t} className="recent-tag">{t}</span>
                                                        ))}
                                                    </div>
                                                )}
                                                <span className="recent-date">{formatDate(r.completed_at)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </>
    );
}

export default StatsPage;
