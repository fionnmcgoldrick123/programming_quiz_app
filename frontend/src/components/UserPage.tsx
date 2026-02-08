import { useNavigate } from "react-router-dom";
import { useAuth } from "../utils/AuthContext";
import Navbar from "./Navbar";
import '../css-files/UserPage.css';

function UserPage() {
    const navigate = useNavigate();
    const { user, logout, isAuthenticated, isLoading } = useAuth();

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

    // XP is already per-level (resets on level-up), xp_required scales per level
    const expForNextLevel = user.xp_required ?? (100 * user.level);
    const progressPercent = (user.exp / expForNextLevel) * 100;

    return (
        <>
            <Navbar />
            <div className="user-page">
                <div className="profile-container">
                    <div className="profile-header">
                        <div className="avatar">
                            {user.first_name.charAt(0).toUpperCase()}
                            {user.second_name.charAt(0).toUpperCase()}
                        </div>
                        <h1 className="profile-name">{user.first_name} {user.second_name}</h1>
                        <p className="profile-email">{user.email}</p>
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

                    <button className="logout-btn" onClick={handleLogout}>
                        Logout
                    </button>
                </div>
            </div>
        </>
    );
}

export default UserPage;
