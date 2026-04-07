import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../utils/AuthContext";
import Navbar from "../layout/Navbar";
import "../../css-files/pages/SocialPage.css";

interface UserResult {
    id: number;
    first_name: string;
    second_name: string;
    email: string;
    level: number;
    exp: number;
    display_name: string | null;
    avatar_url: string | null;
    created_at: string | null;
}

interface FriendRequest {
    friendship_id: number;
    user_id: number;
    first_name: string;
    second_name: string;
    email: string;
    level: number;
    exp: number;
    sent_at: string | null;
}

interface Friend {
    id: number;
    first_name: string;
    second_name: string;
    email: string;
    level: number;
    exp: number;
    created_at: string | null;
    friends_since: string | null;
}

type Tab = "search" | "friends" | "requests";

function SocialPage() {
    const navigate = useNavigate();
    const { token, isAuthenticated, isLoading: authLoading } = useAuth();

    const [activeTab, setActiveTab] = useState<Tab>("search");
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<UserResult[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);

    const [friends, setFriends] = useState<Friend[]>([]);
    const [friendsLoading, setFriendsLoading] = useState(false);

    const [requests, setRequests] = useState<FriendRequest[]>([]);
    const [requestsLoading, setRequestsLoading] = useState(false);
    const [requestCount, setRequestCount] = useState(0);

    const [actionMsg, setActionMsg] = useState("");

    useEffect(() => {
        if (authLoading) return;
        if (!isAuthenticated || !token) { navigate("/login"); return; }
        fetchRequestCount();
    }, [authLoading, isAuthenticated, token, navigate]);

    useEffect(() => {
        if (!token) return;
        if (activeTab === "friends") fetchFriends();
        if (activeTab === "requests") fetchRequests();
    }, [activeTab, token]);

    const headers = { Authorization: `Bearer ${token}` };

    async function fetchRequestCount() {
        try {
            const res = await fetch("http://127.0.0.1:8000/friends/requests/count", { headers });
            if (res.ok) {
                const data = await res.json();
                setRequestCount(data.pending_count);
            }
        } catch { /* non-critical */ }
    }

    async function handleSearch() {
        if (!searchQuery.trim()) return;
        setSearchLoading(true);
        setHasSearched(true);
        try {
            const res = await fetch(
                `http://127.0.0.1:8000/users/search?q=${encodeURIComponent(searchQuery.trim())}`,
                { headers }
            );
            if (res.ok) setSearchResults(await res.json());
        } catch { /* network error */ }
        finally { setSearchLoading(false); }
    }

    async function fetchFriends() {
        setFriendsLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/friends", { headers });
            if (res.ok) setFriends(await res.json());
        } catch { /* network error */ }
        finally { setFriendsLoading(false); }
    }

    async function fetchRequests() {
        setRequestsLoading(true);
        try {
            const res = await fetch("http://127.0.0.1:8000/friends/requests", { headers });
            if (res.ok) {
                const data = await res.json();
                setRequests(data);
                setRequestCount(data.length);
            }
        } catch { /* network error */ }
        finally { setRequestsLoading(false); }
    }

    async function handleRespond(friendshipId: number, action: "accept" | "reject") {
        try {
            const res = await fetch("http://127.0.0.1:8000/friends/respond", {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ friendship_id: friendshipId, action }),
            });
            if (res.ok) {
                const data = await res.json();
                showAction(data.message);
                fetchRequests();
                if (action === "accept") fetchFriends();
            }
        } catch { /* network error */ }
    }

    async function handleRemoveFriend(friendId: number) {
        try {
            const res = await fetch(`http://127.0.0.1:8000/friends/${friendId}`, {
                method: "DELETE",
                headers,
            });
            if (res.ok) {
                showAction("Friend removed");
                fetchFriends();
            }
        } catch { /* network error */ }
    }

    function showAction(msg: string) {
        setActionMsg(msg);
        setTimeout(() => setActionMsg(""), 3000);
    }

    function formatDate(iso: string | null) {
        if (!iso) return "";
        return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
    }

    if (authLoading) {
        return (
            <>
                <Navbar />
                <div className="social-page">
                    <div className="social-loading">
                        <div className="social-spinner" />
                        <p>Loading...</p>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <Navbar />
            <div className="social-page">
                <div className="social-container">
                    <div className="social-header">
                        <h1 className="social-title">Social</h1>
                        <p className="social-subtitle">Find friends and track progress together</p>
                    </div>

                    {actionMsg && <div className="social-toast">{actionMsg}</div>}

                    <div className="social-tabs">
                        <button
                            className={`social-tab ${activeTab === "search" ? "social-tab--active" : ""}`}
                            onClick={() => setActiveTab("search")}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                            Search Users
                        </button>
                        <button
                            className={`social-tab ${activeTab === "friends" ? "social-tab--active" : ""}`}
                            onClick={() => setActiveTab("friends")}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                                <circle cx="9" cy="7" r="4" />
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                            </svg>
                            Friends
                        </button>
                        <button
                            className={`social-tab ${activeTab === "requests" ? "social-tab--active" : ""}`}
                            onClick={() => setActiveTab("requests")}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                                <circle cx="8.5" cy="7" r="4" />
                                <line x1="20" y1="8" x2="20" y2="14" />
                                <line x1="23" y1="11" x2="17" y2="11" />
                            </svg>
                            Requests
                            {requestCount > 0 && <span className="social-badge">{requestCount}</span>}
                        </button>
                    </div>

                    {/* Search Tab */}
                    {activeTab === "search" && (
                        <div className="social-panel">
                            <div className="social-search-bar">
                                <input
                                    type="text"
                                    placeholder="Search by name or email..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                                    className="social-search-input"
                                />
                                <button className="social-search-btn" onClick={handleSearch} disabled={searchLoading}>
                                    {searchLoading ? "Searching..." : "Search"}
                                </button>
                            </div>

                            {searchLoading && (
                                <div className="social-loading-inline">
                                    <div className="social-spinner" />
                                </div>
                            )}

                            {!searchLoading && hasSearched && searchResults.length === 0 && (
                                <div className="social-empty">No users found matching "{searchQuery}"</div>
                            )}

                            <div className="social-results">
                                {searchResults.map((u) => (
                                    <div key={u.id} className="social-user-card" onClick={() => navigate(`/user/${u.id}`)}>
                                        <div className="social-user-avatar">
                                            {u.avatar_url
                                                ? <img src={u.avatar_url} alt="avatar" className="social-avatar-img" />
                                                : <>{u.first_name.charAt(0).toUpperCase()}{u.second_name.charAt(0).toUpperCase()}</>
                                            }
                                        </div>
                                        <div className="social-user-info">
                                            <span className="social-user-name">{u.display_name ?? `${u.first_name} ${u.second_name}`}</span>
                                            {u.display_name && <span className="social-user-realname">{u.first_name} {u.second_name}</span>}
                                            <span className="social-user-meta">Level {u.level}</span>
                                        </div>
                                        <div className="social-user-arrow">→</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Friends Tab */}
                    {activeTab === "friends" && (
                        <div className="social-panel">
                            {friendsLoading ? (
                                <div className="social-loading-inline"><div className="social-spinner" /></div>
                            ) : friends.length === 0 ? (
                                <div className="social-empty">
                                    <p>No friends yet</p>
                                    <span className="social-empty-hint">Search for users to add them as friends!</span>
                                </div>
                            ) : (
                                <div className="social-results">
                                    {friends.map((f) => (
                                        <div key={f.id} className="social-user-card">
                                            <div className="social-user-avatar" onClick={() => navigate(`/user/${f.id}`)}>
                                                {f.first_name.charAt(0).toUpperCase()}
                                                {f.second_name.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="social-user-info" onClick={() => navigate(`/user/${f.id}`)}>
                                                <span className="social-user-name">{f.first_name} {f.second_name}</span>
                                                <span className="social-user-meta">
                                                    Level {f.level} · Friends since {formatDate(f.friends_since)}
                                                </span>
                                            </div>
                                            <button
                                                className="social-remove-btn"
                                                onClick={(e) => { e.stopPropagation(); handleRemoveFriend(f.id); }}
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Requests Tab */}
                    {activeTab === "requests" && (
                        <div className="social-panel">
                            {requestsLoading ? (
                                <div className="social-loading-inline"><div className="social-spinner" /></div>
                            ) : requests.length === 0 ? (
                                <div className="social-empty">No pending friend requests</div>
                            ) : (
                                <div className="social-results">
                                    {requests.map((r) => (
                                        <div key={r.friendship_id} className="social-user-card social-request-card">
                                            <div className="social-user-avatar" onClick={() => navigate(`/user/${r.user_id}`)}>
                                                {r.first_name.charAt(0).toUpperCase()}
                                                {r.second_name.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="social-user-info" onClick={() => navigate(`/user/${r.user_id}`)}>
                                                <span className="social-user-name">{r.first_name} {r.second_name}</span>
                                                <span className="social-user-meta">
                                                    Level {r.level} · Sent {formatDate(r.sent_at)}
                                                </span>
                                            </div>
                                            <div className="social-request-actions">
                                                <button
                                                    className="social-accept-btn"
                                                    onClick={() => handleRespond(r.friendship_id, "accept")}
                                                >
                                                    Accept
                                                </button>
                                                <button
                                                    className="social-reject-btn"
                                                    onClick={() => handleRespond(r.friendship_id, "reject")}
                                                >
                                                    Reject
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}

export default SocialPage;
