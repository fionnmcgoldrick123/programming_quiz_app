import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../utils/AuthContext";
import Navbar from "../layout/Navbar";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    RadialBarChart, RadialBar,
} from "recharts";
import "../../css-files/pages/PublicProfilePage.css";

interface ProfileData {
    id: number;
    first_name: string;
    second_name: string;
    email: string;
    level: number;
    exp: number;
    xp_required: number;
    created_at: string | null;
    friendship_status: "none" | "friends" | "request_sent" | "request_received";
    friend_count: number;
    display_name: string | null;
    bio: string | null;
    avatar_url: string | null;
}

interface TagStat { name: string; count: number; }
interface LangStat { name: string; count: number; }
interface RecentQuiz {
    quiz_type: string;
    total_questions: number;
    correct_answers: number;
    tags: string[];
    language: string | null;
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

function PublicProfilePage() {
    const { userId } = useParams<{ userId: string }>();
    const navigate = useNavigate();
    const { user: currentUser, token, isAuthenticated, isLoading: authLoading } = useAuth();

    const [profile, setProfile] = useState<ProfileData | null>(null);
    const [stats, setStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [friendAction, setFriendAction] = useState("");
    const [showStats, setShowStats] = useState(false);

    const headers = { Authorization: `Bearer ${token}` };

    useEffect(() => {
        if (authLoading) return;
        if (!isAuthenticated || !token) { navigate("/login"); return; }

        // Redirect to own profile if viewing self
        if (currentUser && String(currentUser.id) === userId) {
            navigate("/profile");
            return;
        }

        fetchProfile();
    }, [authLoading, isAuthenticated, token, userId]);

    async function fetchProfile() {
        setLoading(true);
        try {
            const [profileRes, statsRes] = await Promise.all([
                fetch(`http://127.0.0.1:8000/users/${userId}/profile`, { headers }),
                fetch(`http://127.0.0.1:8000/users/${userId}/stats`, { headers }),
            ]);

            if (profileRes.ok) setProfile(await profileRes.json());
            if (statsRes.ok) setStats(await statsRes.json());
        } catch { /* network error */ }
        finally { setLoading(false); }
    }

    async function handleAddFriend() {
        try {
            const res = await fetch(`http://127.0.0.1:8000/friends/request/${userId}`, {
                method: "POST",
                headers,
            });
            if (res.ok) {
                const data = await res.json();
                setFriendAction(data.message);
                fetchProfile();
            } else {
                const err = await res.json();
                setFriendAction(err.detail || "Failed to send request");
            }
        } catch { setFriendAction("Network error"); }
        setTimeout(() => setFriendAction(""), 3000);
    }

    async function handleRemoveFriend() {
        try {
            const res = await fetch(`http://127.0.0.1:8000/friends/${userId}`, {
                method: "DELETE",
                headers,
            });
            if (res.ok) {
                setFriendAction("Friend removed");
                fetchProfile();
            }
        } catch { /* network error */ }
        setTimeout(() => setFriendAction(""), 3000);
    }

    function formatDate(iso: string | null) {
        if (!iso) return "N/A";
        return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
    }

    function formatDateShort(iso: string | null) {
        if (!iso) return "";
        return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    }

    if (authLoading || loading) {
        return (
            <>
                <Navbar />
                <div className="pub-profile-page">
                    <div className="pub-loading"><div className="pub-spinner" /><p>Loading profile...</p></div>
                </div>
            </>
        );
    }

    if (!profile) {
        return (
            <>
                <Navbar />
                <div className="pub-profile-page">
                    <div className="pub-error">
                        <p>User not found</p>
                        <button className="pub-btn" onClick={() => navigate("/social")}>Back to Social</button>
                    </div>
                </div>
            </>
        );
    }

    const progressPercent = (profile.exp / profile.xp_required) * 100;

    const correctWrongData = stats ? [
        { name: "Correct", value: stats.total_correct },
        { name: "Wrong", value: stats.total_wrong },
    ] : [];

    const quizTypeData = stats ? [
        { name: "MCQ", value: stats.mcq_quizzes },
        { name: "Coding", value: stats.coding_quizzes },
    ] : [];

    const accuracyData = stats ? [{ name: "Accuracy", value: stats.accuracy, fill: "#ff9500" }] : [];

    const friendBtn = () => {
        switch (profile.friendship_status) {
            case "friends":
                return <button className="pub-friend-btn pub-friend-btn--remove" onClick={handleRemoveFriend}>Remove Friend</button>;
            case "request_sent":
                return <button className="pub-friend-btn pub-friend-btn--pending" disabled>Request Sent</button>;
            case "request_received":
                return <button className="pub-friend-btn pub-friend-btn--accept" onClick={handleAddFriend}>Accept Request</button>;
            default:
                return <button className="pub-friend-btn pub-friend-btn--add" onClick={handleAddFriend}>Add Friend</button>;
        }
    };

    return (
        <>
            <Navbar />
            <div className="pub-profile-page">
                <div className="pub-container">
                    <button className="pub-back-btn" onClick={() => navigate("/social")}>← Back to Social</button>

                    {friendAction && <div className="pub-toast">{friendAction}</div>}

                    {/* Profile Card */}
                    <div className="pub-profile-card">
                        <div className="pub-avatar">
                            {profile.avatar_url
                                ? <img src={profile.avatar_url} alt="avatar" className="pub-avatar-img" />
                                : <>{profile.first_name.charAt(0).toUpperCase()}{profile.second_name.charAt(0).toUpperCase()}</>
                            }
                        </div>
                        <h1 className="pub-name">
                            {profile.display_name ?? `${profile.first_name} ${profile.second_name}`}
                        </h1>
                        {profile.display_name && (
                            <p className="pub-realname">{profile.first_name} {profile.second_name}</p>
                        )}
                        {profile.friendship_status === "friends" && (
                            <p className="pub-email">{profile.email}</p>
                        )}
                        {profile.bio && <p className="pub-bio">{profile.bio}</p>}

                        <div className="pub-meta-row">
                            <div className="pub-meta-item">
                                <span className="pub-meta-value">{profile.level}</span>
                                <span className="pub-meta-label">Level</span>
                            </div>
                            <div className="pub-meta-item">
                                <span className="pub-meta-value">{profile.friend_count}</span>
                                <span className="pub-meta-label">Friends</span>
                            </div>
                            <div className="pub-meta-item">
                                <span className="pub-meta-value">{stats?.total_quizzes ?? 0}</span>
                                <span className="pub-meta-label">Quizzes</span>
                            </div>
                        </div>

                        <div className="pub-progress-section">
                            <div className="pub-progress-header">
                                <span>Level {profile.level} Progress</span>
                                <span>{profile.exp}/{profile.xp_required} XP</span>
                            </div>
                            <div className="pub-progress-bar">
                                <div className="pub-progress-fill" style={{ width: `${progressPercent}%` }} />
                            </div>
                        </div>

                        {profile.friendship_status === "friends" ? (
                            <div className="pub-details">
                                <div className="pub-detail-item">
                                    <span className="pub-detail-label">Member Since</span>
                                    <span className="pub-detail-value">{formatDate(profile.created_at)}</span>
                                </div>
                            </div>
                        ) : (
                            <div className="pub-details pub-details--locked">
                                <span className="pub-locked-icon">🔒</span>
                                <span className="pub-locked-text">Add as friend to see full details &amp; stats</span>
                            </div>
                        )}

                        <div className="pub-actions">
                            {friendBtn()}
                        </div>
                    </div>

                    {/* Stats Toggle — friends only */}
                    {profile.friendship_status === "friends" && stats && stats.total_quizzes > 0 && (
                        <>
                            <button
                                className="pub-stats-toggle"
                                onClick={() => setShowStats(!showStats)}
                            >
                                {showStats ? "Hide" : "View"} Statistics
                                <span className={`pub-toggle-arrow ${showStats ? "pub-toggle-arrow--open" : ""}`}>▼</span>
                            </button>

                            {showStats && (
                                <div className="pub-stats-section">
                                    {/* KPI Cards */}
                                    <div className="pub-kpi-row">
                                        <div className="pub-kpi-card">
                                            <span className="pub-kpi-value">{stats.total_quizzes}</span>
                                            <span className="pub-kpi-label">Quizzes</span>
                                        </div>
                                        <div className="pub-kpi-card">
                                            <span className="pub-kpi-value">{stats.total_questions}</span>
                                            <span className="pub-kpi-label">Questions</span>
                                        </div>
                                        <div className="pub-kpi-card pub-kpi-card--correct">
                                            <span className="pub-kpi-value">{stats.total_correct}</span>
                                            <span className="pub-kpi-label">Correct</span>
                                        </div>
                                        <div className="pub-kpi-card pub-kpi-card--wrong">
                                            <span className="pub-kpi-value">{stats.total_wrong}</span>
                                            <span className="pub-kpi-label">Wrong</span>
                                        </div>
                                    </div>

                                    {/* Charts */}
                                    <div className="pub-charts-row">
                                        <div className="pub-chart-card">
                                            <h3 className="pub-chart-title">Accuracy</h3>
                                            <div className="pub-chart-wrapper pub-chart-wrapper--gauge">
                                                <ResponsiveContainer width="100%" height={180}>
                                                    <RadialBarChart
                                                        cx="50%" cy="50%"
                                                        innerRadius="70%" outerRadius="90%"
                                                        startAngle={180} endAngle={0}
                                                        barSize={14} data={accuracyData}
                                                    >
                                                        <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "#3d3d3d" }} />
                                                    </RadialBarChart>
                                                </ResponsiveContainer>
                                                <div className="pub-gauge-label">
                                                    <span className="pub-gauge-value">{stats.accuracy}%</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="pub-chart-card">
                                            <h3 className="pub-chart-title">Correct vs Wrong</h3>
                                            <div className="pub-chart-wrapper">
                                                <ResponsiveContainer width="100%" height={200}>
                                                    <PieChart>
                                                        <Pie data={correctWrongData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value" stroke="none">
                                                            <Cell fill="#4caf50" />
                                                            <Cell fill="#f44336" />
                                                        </Pie>
                                                        <Tooltip contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }} itemStyle={{ color: "#e0e0e0" }} />
                                                    </PieChart>
                                                </ResponsiveContainer>
                                                <div className="pub-pie-legend">
                                                    <span className="pub-legend-dot" style={{ background: "#4caf50" }} /> Correct
                                                    <span className="pub-legend-dot" style={{ background: "#f44336", marginLeft: 16 }} /> Wrong
                                                </div>
                                            </div>
                                        </div>

                                        <div className="pub-chart-card">
                                            <h3 className="pub-chart-title">Quiz Types</h3>
                                            <div className="pub-chart-wrapper">
                                                <ResponsiveContainer width="100%" height={200}>
                                                    <PieChart>
                                                        <Pie data={quizTypeData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value" stroke="none">
                                                            {quizTypeData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                                                        </Pie>
                                                        <Tooltip contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }} itemStyle={{ color: "#e0e0e0" }} />
                                                    </PieChart>
                                                </ResponsiveContainer>
                                                <div className="pub-pie-legend">
                                                    <span className="pub-legend-dot" style={{ background: PIE_COLORS[0] }} /> MCQ
                                                    <span className="pub-legend-dot" style={{ background: PIE_COLORS[1], marginLeft: 16 }} /> Coding
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Topics Bar Chart */}
                                    {stats.tags.length > 0 && (
                                        <div className="pub-chart-card pub-chart-card--wide">
                                            <h3 className="pub-chart-title">Top Topics</h3>
                                            <div className="pub-chart-wrapper">
                                                <ResponsiveContainer width="100%" height={260}>
                                                    <BarChart data={stats.tags} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="#3d3d3d" />
                                                        <XAxis type="number" allowDecimals={false} tick={{ fill: "#888", fontFamily: "'Fira Code', monospace", fontSize: 12 }} />
                                                        <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#ccc", fontFamily: "'Fira Code', monospace", fontSize: 12 }} />
                                                        <Tooltip contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }} itemStyle={{ color: "#ff9500" }} cursor={{ fill: "rgba(255,149,0,0.08)" }} />
                                                        <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16}>
                                                            {stats.tags.map((_, i) => <Cell key={i} fill={ORANGE_PALETTE[i % ORANGE_PALETTE.length]} />)}
                                                        </Bar>
                                                    </BarChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    )}

                                    {/* Languages */}
                                    {stats.languages.length > 0 && (
                                        <div className="pub-chart-card">
                                            <h3 className="pub-chart-title">Languages</h3>
                                            <div className="pub-chart-wrapper">
                                                <ResponsiveContainer width="100%" height={220}>
                                                    <PieChart>
                                                        <Pie data={stats.languages} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={3} dataKey="count" stroke="none" label={({ name }) => name}>
                                                            {stats.languages.map((_, i) => <Cell key={i} fill={ORANGE_PALETTE[i % ORANGE_PALETTE.length]} />)}
                                                        </Pie>
                                                        <Tooltip contentStyle={{ background: "#2d2d2d", border: "1px solid #404040", borderRadius: 8, fontFamily: "'Fira Code', monospace", fontSize: "0.85rem" }} itemStyle={{ color: "#e0e0e0" }} />
                                                    </PieChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    )}

                                    {/* Recent Activity */}
                                    {stats.recent.length > 0 && (
                                        <div className="pub-recent">
                                            <h3 className="pub-chart-title">Recent Activity</h3>
                                            <div className="pub-recent-list">
                                                {stats.recent.map((r, i) => (
                                                    <div className="pub-recent-item" key={i}>
                                                        <div className={`pub-recent-icon pub-recent-icon--${r.quiz_type}`}>
                                                            {r.quiz_type === "mcq" ? "Q" : "</>"}
                                                        </div>
                                                        <div className="pub-recent-info">
                                                            <span className="pub-recent-type">
                                                                {r.quiz_type === "mcq" ? "MCQ Quiz" : `Coding (${r.language})`}
                                                            </span>
                                                            <span className="pub-recent-score">{r.correct_answers}/{r.total_questions} correct</span>
                                                        </div>
                                                        {r.tags.length > 0 && (
                                                            <div className="pub-recent-tags">
                                                                {r.tags.slice(0, 3).map(t => <span key={t} className="pub-recent-tag">{t}</span>)}
                                                            </div>
                                                        )}
                                                        <span className="pub-recent-date">{formatDateShort(r.completed_at)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </>
    );
}

export default PublicProfilePage;
