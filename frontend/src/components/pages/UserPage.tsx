import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../utils/AuthContext";
import Navbar from "../layout/Navbar";
import '../../css-files/pages/UserPage.css';

function UserPage() {
    const navigate = useNavigate();
    const { user, token, logout, updateUser, isAuthenticated, isLoading } = useAuth();
    const [friendCount, setFriendCount] = useState<number | null>(null);
    const [pendingCount, setPendingCount] = useState(0);

    // Edit profile state
    const [editOpen, setEditOpen] = useState(false);
    const [editDisplayName, setEditDisplayName] = useState("");
    const [editBio, setEditBio] = useState("");
    const [editAvatarPreview, setEditAvatarPreview] = useState<string | null>(null);
    const [editAvatarData, setEditAvatarData] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState("");
    const [saveSuccess, setSaveSuccess] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!token) return;
        fetch("http://127.0.0.1:8000/friends/count", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data) setFriendCount(data.friend_count); })
            .catch(() => {});

        fetch("http://127.0.0.1:8000/friends/requests/count", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data) setPendingCount(data.pending_count); })
            .catch(() => {});
    }, [token]);

    function openEdit() {
        if (!user) return;
        setEditDisplayName(user.display_name ?? "");
        setEditBio(user.bio ?? "");
        setEditAvatarPreview(user.avatar_url ?? null);
        setEditAvatarData(null);
        setSaveError("");
        setSaveSuccess(false);
        setEditOpen(true);
    }

    function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            setSaveError("Image must be under 2 MB");
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            const result = ev.target?.result as string;
            setEditAvatarPreview(result);
            setEditAvatarData(result);
        };
        reader.readAsDataURL(file);
    }

    async function handleSaveProfile() {
        setSaveError("");
        const displayNameTrimmed = editDisplayName.trim();
        if (displayNameTrimmed && (displayNameTrimmed.length < 3 || displayNameTrimmed.length > 30)) {
            setSaveError("Display name must be 3–30 characters");
            return;
        }
        if (editBio.length > 300) {
            setSaveError("Bio must be 300 characters or fewer");
            return;
        }
        setSaving(true);
        try {
            const body: Record<string, string> = {};
            if (displayNameTrimmed) body.display_name = displayNameTrimmed;
            else if (user?.display_name) body.display_name = "";  // clear by sending empty isn't supported; skip if empty
            body.bio = editBio;
            if (editAvatarData) body.avatar_url = editAvatarData;

            // If display name is empty, remove it so we don't send a too-short value
            if (!body.display_name) delete body.display_name;

            const res = await fetch("http://127.0.0.1:8000/me/profile", {
                method: "PATCH",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify(body),
            });
            if (res.ok) {
                const updated = await res.json();
                updateUser(updated);
                setSaveSuccess(true);
                setTimeout(() => { setEditOpen(false); setSaveSuccess(false); }, 1200);
            } else {
                const err = await res.json();
                setSaveError(err.detail ?? "Failed to save");
            }
        } catch {
            setSaveError("Network error");
        } finally {
            setSaving(false);
        }
    }

    if (isLoading) {
        return (
            <>
                <Navbar />
                <div className="user-page">
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </>
        );
    }

    if (!isAuthenticated || !user) {
        return (
            <>
                <Navbar />
                <div className="user-page">
                    <div className="not-logged-in">
                        <h2>Not Logged In</h2>
                        <p>Please log in to view your profile</p>
                        <button className="login-btn" onClick={() => navigate("/login")}>
                            Go to Login
                        </button>
                    </div>
                </div>
            </>
        );
    }

    const handleLogout = () => {
        logout();
        navigate("/");
    };

    const formatDate = (dateString: string | null) => {
        if (!dateString) return "N/A";
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    const expForNextLevel = user.xp_required ?? (100 * user.level);
    const progressPercent = (user.exp / expForNextLevel) * 100;
    const displayLabel = user.display_name ?? `${user.first_name} ${user.second_name}`;

    return (
        <>
            <Navbar />
            <div className="user-page">
                <div className="profile-container">
                    <div className="profile-header">
                        <div className="avatar">
                            {user.avatar_url
                                ? <img src={user.avatar_url} alt="avatar" className="avatar-img" />
                                : <>{user.first_name.charAt(0).toUpperCase()}{user.second_name.charAt(0).toUpperCase()}</>
                            }
                        </div>
                        <h1 className="profile-name">{displayLabel}</h1>
                        {user.display_name && (
                            <p className="profile-realname">{user.first_name} {user.second_name}</p>
                        )}
                        <p className="profile-email">{user.email}</p>
                        {user.bio && <p className="profile-bio">{user.bio}</p>}
                        <button className="edit-profile-btn" onClick={openEdit}>Edit Profile</button>
                    </div>

                    <div className="stats-grid">
                        <div className="stat-card">
                            <div className="stat-icon"></div>
                            <div className="stat-info">
                                <span className="stat-value">{user.level}</span>
                                <span className="stat-label">Level</span>
                            </div>
                        </div>
                        
                        <div className="stat-card">
                            <div className="stat-icon"></div>
                            <div className="stat-info">
                                <span className="stat-value">{user.exp}/{expForNextLevel}</span>
                                <span className="stat-label">XP to Next Level</span>
                            </div>
                        </div>

                        <div className="stat-card stat-card--friends" onClick={() => navigate("/social")}>
                            <div className="stat-icon"></div>
                            <div className="stat-info">
                                <span className="stat-value">{friendCount ?? "–"}</span>
                                <span className="stat-label">Friends</span>
                            </div>
                        </div>
                    </div>

                    <div className="progress-section">
                        <div className="progress-header">
                            <span>Progress to Level {user.level + 1}</span>
                            <span>{user.exp}/{expForNextLevel} XP</span>
                        </div>
                        <div className="progress-bar">
                            <div 
                                className="progress-fill" 
                                style={{ width: `${progressPercent}%` }}
                            ></div>
                        </div>
                    </div>

                    <div className="info-section">
                        <h3>Account Details</h3>
                        <div className="info-grid">
                            <div className="info-item">
                                <span className="info-label">First Name</span>
                                <span className="info-value">{user.first_name}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Last Name</span>
                                <span className="info-value">{user.second_name}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Email</span>
                                <span className="info-value">{user.email}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Member Since</span>
                                <span className="info-value">{formatDate(user.created_at)}</span>
                            </div>
                        </div>
                    </div>

                    <button className="social-page-btn" onClick={() => navigate("/social")}>
                        <span className="social-page-btn__icon">👥</span>
                        Friends & Social
                        {pendingCount > 0 && <span className="social-page-btn__badge">{pendingCount}</span>}
                        <span className="social-page-btn__arrow">→</span>
                    </button>

                    <button className="stats-page-btn" onClick={() => navigate("/stats")}>
                        <span className="stats-page-btn__bar"></span>
                        View Statistics
                        <span className="stats-page-btn__arrow">→</span>
                    </button>

                    <button className="logout-btn" onClick={handleLogout}>
                        Logout
                    </button>
                </div>
            </div>

            {/* Edit Profile Modal */}
            {editOpen && (
                <div className="edit-modal-overlay" onClick={() => setEditOpen(false)}>
                    <div className="edit-modal" onClick={e => e.stopPropagation()}>
                        <h2 className="edit-modal__title">Edit Profile</h2>

                        <div className="edit-modal__avatar-row">
                            <div className="edit-modal__avatar-preview">
                                {editAvatarPreview
                                    ? <img src={editAvatarPreview} alt="preview" className="avatar-img" />
                                    : <>{user.first_name.charAt(0).toUpperCase()}{user.second_name.charAt(0).toUpperCase()}</>
                                }
                            </div>
                            <div className="edit-modal__avatar-actions">
                                <button className="edit-modal__upload-btn" onClick={() => fileInputRef.current?.click()}>
                                    Upload Photo
                                </button>
                                {editAvatarPreview && (
                                    <button className="edit-modal__remove-btn" onClick={() => { setEditAvatarPreview(null); setEditAvatarData(""); }}>
                                        Remove
                                    </button>
                                )}
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    style={{ display: "none" }}
                                    onChange={handleAvatarChange}
                                />
                                <p className="edit-modal__avatar-hint">Max 2 MB · JPG, PNG, GIF</p>
                            </div>
                        </div>

                        <label className="edit-modal__label">
                            Display Name
                            <span className="edit-modal__sublabel"> (3–30 chars, shown instead of your real name)</span>
                        </label>
                        <input
                            className="edit-modal__input"
                            type="text"
                            maxLength={30}
                            placeholder="e.g. coder42"
                            value={editDisplayName}
                            onChange={e => setEditDisplayName(e.target.value)}
                        />

                        <label className="edit-modal__label">
                            Bio
                            <span className="edit-modal__sublabel"> ({editBio.length}/300)</span>
                        </label>
                        <textarea
                            className="edit-modal__textarea"
                            maxLength={300}
                            placeholder="Tell others a bit about yourself..."
                            value={editBio}
                            onChange={e => setEditBio(e.target.value)}
                            rows={4}
                        />

                        {saveError && <p className="edit-modal__error">{saveError}</p>}
                        {saveSuccess && <p className="edit-modal__success">Saved!</p>}

                        <div className="edit-modal__actions">
                            <button className="edit-modal__cancel" onClick={() => setEditOpen(false)}>Cancel</button>
                            <button className="edit-modal__save" onClick={handleSaveProfile} disabled={saving}>
                                {saving ? "Saving..." : "Save Changes"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default UserPage;
