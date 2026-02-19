import { useState, useEffect } from "react";
import Navbar from "./Navbar";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../utils/AuthContext";
import '../css-files/LandingPage.css'

const phrases = [
    "Master coding challenges daily",
    "Improve your programming skills",
    "Learn with AI-powered feedback",
    "Practice makes perfect",
    "Build your coding confidence"
];

function LandingPage(){
    const navigate = useNavigate();
    const { user, isAuthenticated } = useAuth();
    const [displayedText, setDisplayedText] = useState("");
    const [currentPhrase, setCurrentPhrase] = useState(0);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        let timeout: ReturnType<typeof setTimeout>;
        const currentFullText = phrases[currentPhrase];
        const typingSpeed = isDeleting ? 50 : 80;
        const shouldDelete = displayedText === currentFullText && !isDeleting;
        const shouldSwitchPhrase = displayedText === "" && isDeleting;

        if (shouldDelete) {
            timeout = setTimeout(() => setIsDeleting(true), 1500);
        } else if (shouldSwitchPhrase) {
            setIsDeleting(false);
            setCurrentPhrase((prev) => (prev + 1) % phrases.length);
        } else {
            const nextText = isDeleting
                ? currentFullText.substring(0, displayedText.length - 1)
                : currentFullText.substring(0, displayedText.length + 1);

            timeout = setTimeout(() => setDisplayedText(nextText), typingSpeed);
        }

        return () => clearTimeout(timeout);
    }, [displayedText, isDeleting, currentPhrase]);

    return(
        <>
        <Navbar/>
        <div className="landing-page">
            <div className="landing-left">
                <div>
                    <h1 className="landing-title">
                        {isAuthenticated && user ? (
                            <>
                                Welcome back, <span className="highlight">{user.first_name}!</span>
                            </>
                        ) : (
                            <>
                                Welcome to <span className="highlight">CodeQuiz</span>
                            </>
                        )}
                    </h1>
                    <p className="landing-subtitle">
                        Test your programming knowledge with AI-powered quizzes and real-time feedback
                    </p>
                </div>

                <div className="typing-container">
                    <div className="typing-text">
                        {displayedText}
                        <span className="cursor"></span>
                    </div>
                </div>

                <button className="cta-button" onClick={() => navigate("/prompt")}>
                    Start Now
                </button>
            </div>

            <div className="landing-right">
                <div className="feature-card">
                    <h3>Features</h3>
                    <p>Everything you need to level up your coding skills</p>
                    <div className="feature-list">
                        <div className="feature-item">Smart AI Quiz Generation</div>
                        <div className="feature-item">Instant Feedback</div>
                        <div className="feature-item">Multiple Language Support</div>
                        <div className="feature-item">Track Your Progress</div>
                        <div className="feature-item">Challenge Yourself Daily</div>
                    </div>
                </div>
            </div>
        </div>
        </>
    )
}

export default LandingPage;