import '../../css-files/layout/Navbar.css'
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../utils/AuthContext";

function Navbar(){

    const navigate = useNavigate()
    const location = useLocation()
    const { user, isAuthenticated } = useAuth()

    const isInActiveQuiz = (() => {
        if (location.pathname !== '/quiz' && location.pathname !== '/code-sandbox') return false;
        if (!user?.id) return true; // can't read session, assume active
        try {
            if (location.pathname === '/quiz') {
                const raw = sessionStorage.getItem(`quizPageSession_${user.id}`);
                if (!raw) return false;
                const s = JSON.parse(raw);
                return Boolean(s?.quiz?.length && !s.finished);
            }
            if (location.pathname === '/code-sandbox') {
                const raw = sessionStorage.getItem(`codeSandboxSession_${user.id}`);
                if (!raw) return false;
                const s = JSON.parse(raw);
                return Boolean(s?.questions?.length && !s.finished);
            }
        } catch { /* ignore */ }
        return true;
    })();

    function handleClick(path : string){
        navigate(path);
    }

    function handleQuizClick() {
        // Check for active (unfinished) quiz sessions for the current user
        const userId = user?.id;
        if (!userId) { navigate('/prompt'); return; }
        try {
            const mcqRaw = sessionStorage.getItem(`quizPageSession_${userId}`);
            if (mcqRaw) {
                const mcq = JSON.parse(mcqRaw);
                if (mcq?.quiz?.length && !mcq.finished) {
                    navigate('/quiz');
                    return;
                }
            }
            const codeRaw = sessionStorage.getItem(`codeSandboxSession_${userId}`);
            if (codeRaw) {
                const code = JSON.parse(codeRaw);
                if (code?.questions?.length && !code.finished) {
                    navigate('/code-sandbox');
                    return;
                }
            }
        } catch { /* sessionStorage parse failure — non-critical */ }
        navigate('/prompt');
    }

    return (
        <nav className="nav-container">
            <div className="nav-inner">
                <div className="nav-logo" onClick={() => handleClick("/")}>CodeQuiz</div>

                <div className="nav-links">
                    <button className="nav-button" onClick={() => handleClick("/")}>Home</button>
                    <button className="nav-button" onClick={handleQuizClick}>Quiz</button>
                    <button className="nav-button" onClick={() => handleClick("/about")}>About</button>
                    <button
                        className="nav-button"
                        onClick={() => !isInActiveQuiz && handleClick('/prompt')}
                        disabled={isInActiveQuiz}
                        title={isInActiveQuiz ? 'Finish or quit the current quiz first' : undefined}
                    >Prompts</button>
                    {isAuthenticated && (
                        <button className="nav-button" onClick={() => handleClick("/social")}>Social</button>
                    )}
                </div>

                <div className="nav-auth-buttons">
                    {isAuthenticated && user ? (
                        <div className="nav-user-info" onClick={() => handleClick("/profile")}>
                            <span className="nav-user-avatar">
                                {user.first_name.charAt(0).toUpperCase()}
                            </span>
                            <span className="nav-user-name">{user.first_name}</span>
                        </div>
                    ) : (
                        <>
                            <button className="nav-button nav-login" onClick={() => handleClick("/login")}>Login</button>
                            <button className="nav-button nav-register" onClick={() => handleClick("/register")}>Register</button>
                        </>
                    )}
                </div>
            </div>
        </nav>
    )
}

export default Navbar