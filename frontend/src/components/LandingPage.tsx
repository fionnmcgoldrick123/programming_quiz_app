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
    "Build your coding confidence",
    "Code smarter, not harder"
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

    const handleGetStarted = () => {
        if (isAuthenticated) {
            navigate("/prompt");
        } else {
            navigate("/register");
        }
    };

    return (
        <div className="landing-page-wrapper">
            <Navbar />

            {/* HERO SECTION */}
            <section className="hero-section">
                <div className="hero-content">
                    <div className="hero-left">
                        <h1 className="hero-title">
                            {isAuthenticated && user ? (
                                <>
                                    Welcome back,{" "}
                                    <span className="highlight">{user.first_name}!</span>
                                </>
                            ) : (
                                <>
                                    Master Coding with{" "}
                                    <span className="highlight">AI-Powered</span> Quizzes
                                </>
                            )}
                        </h1>
                        <p className="hero-subtitle">
                            Learn and improve your programming skills through intelligent, adaptive quizzes powered by cutting-edge AI. Get instant feedback and track your progress in real-time.
                        </p>

                        <div className="typing-container">
                            <div className="typing-text">
                                {displayedText}
                                <span className="cursor"></span>
                            </div>
                        </div>

                        <div className="cta-buttons">
                            <button className="cta-button primary" onClick={handleGetStarted}>
                                {isAuthenticated ? "Start Quiz" : "Get Started Free"}
                            </button>
                            {!isAuthenticated && (
                                <button className="cta-button secondary" onClick={() => navigate("/login")}>
                                    Login
                                </button>
                            )}
                        </div>

                        <div className="hero-stats">
                            <div className="stat">
                                <span className="stat-number">10K+</span>
                                <span className="stat-label">Active Users</span>
                            </div>
                            <div className="stat-divider"></div>
                            <div className="stat">
                                <span className="stat-number">50+</span>
                                <span className="stat-label">Languages</span>
                            </div>
                            <div className="stat-divider"></div>
                            <div className="stat">
                                <span className="stat-number">100K+</span>
                                <span className="stat-label">Quizzes Taken</span>
                            </div>
                        </div>
                    </div>

                    <div className="hero-right">
                        <div className="floating-card card-1">
                            <h3>AI-Powered</h3>
                            <p>Intelligent quiz generation</p>
                        </div>
                        <div className="floating-card card-2">
                            <h3>Instant Feedback</h3>
                            <p>Real-time evaluation</p>
                        </div>
                        <div className="floating-card card-3">
                            <h3>Track Progress</h3>
                            <p>Visualize your growth</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* FEATURES SECTION */}
            <section className="features-section">
                <div className="section-header">
                    <h2>Why Choose CodeQuiz?</h2>
                    <p>Everything you need to master programming</p>
                </div>

                <div className="features-grid">
                    <div className="feature-card">
                        <h3>Smart AI Generation</h3>
                        <p>Our AI creates customized quizzes based on your selected language and topic, adapting to your skill level.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Adaptive Difficulty</h3>
                        <p>Questions automatically adjust based on your performance, keeping you challenged but not overwhelmed.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Multiple Languages</h3>
                        <p>Learn JavaScript, Python, Java, C++, and more. Coverage across all major programming languages.</p>
                    </div>
                    <div className="feature-card">
                        <h3>AI Feedback</h3>
                        <p>Receive detailed explanations and suggestions to understand not just what you got wrong, but why.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Progress Tracking</h3>
                        <p>Visualize your learning journey with detailed statistics, achievements, and personalized insights.</p>
                    </div>
                    <div className="feature-card">
                        <h3>Gamified Experience</h3>
                        <p>Earn achievements, build streaks, and compete with yourself. Make learning fun and engaging.</p>
                    </div>
                </div>
            </section>

            {/* HOW IT WORKS SECTION */}
            <section className="how-it-works-section">
                <div className="section-header">
                    <h2>How It Works</h2>
                    <p>Get started in 3 simple steps</p>
                </div>

                <div className="steps-container">
                    <div className="step">
                        <div className="step-number">1</div>
                        <h3>Choose Your Topic</h3>
                        <p>Select a programming language and topic you want to master. From beginner to advanced level.</p>
                    </div>

                    <div className="step-connector"></div>

                    <div className="step">
                        <div className="step-number">2</div>
                        <h3>Take the Quiz</h3>
                        <p>Answer AI-generated questions tailored to your skill level with real-time difficulty adjustment.</p>
                    </div>

                    <div className="step-connector"></div>

                    <div className="step">
                        <div className="step-number">3</div>
                        <h3>Get Feedback &amp; Improve</h3>
                        <p>Receive instant AI-powered feedback, track your progress, and identify areas for improvement.</p>
                    </div>
                </div>
            </section>

            {/* LANGUAGES SECTION */}
            <section className="languages-section">
                <div className="section-header">
                    <h2>Language Support</h2>
                    <p>Master the languages you need, when you need them</p>
                </div>

                <div className="languages-grid">
                    <div className="language-badge">JavaScript</div>
                    <div className="language-badge">Python</div>
                    <div className="language-badge">Java</div>
                    <div className="language-badge">C++</div>
                    <div className="language-badge">C#</div>
                    <div className="language-badge">Go</div>
                    <div className="language-badge">Rust</div>
                    <div className="language-badge">TypeScript</div>
                    <div className="language-badge">Ruby</div>
                    <div className="language-badge">PHP</div>
                    <div className="language-badge">Swift</div>
                    <div className="language-badge">Kotlin</div>
                </div>
            </section>

            {/* BENEFITS SECTION */}
            <section className="benefits-section">
                <div className="section-header">
                    <h2>Transform Your Skills</h2>
                    <p>Join thousands of developers improving their craft</p>
                </div>

                <div className="benefits-container">
                    <div className="benefit-item">
                        <div className="benefit-check">&#x2713;</div>
                        <h3>Learn Faster</h3>
                        <p>AI-personalized learning paths adapted to your pace and style</p>
                    </div>
                    <div className="benefit-item">
                        <div className="benefit-check">&#x2713;</div>
                        <h3>Stay Motivated</h3>
                        <p>Gamified experience with achievements, streaks, and rewards</p>
                    </div>
                    <div className="benefit-item">
                        <div className="benefit-check">&#x2713;</div>
                        <h3>Get Better Feedback</h3>
                        <p>Understand your mistakes with detailed AI explanations</p>
                    </div>
                    <div className="benefit-item">
                        <div className="benefit-check">&#x2713;</div>
                        <h3>Track Progress</h3>
                        <p>Comprehensive analytics to monitor your improvement</p>
                    </div>
                </div>
            </section>

            {/* CTA SECTION */}
            <section className="final-cta-section">
                <div className="cta-content">
                    <h2>Ready to Level Up Your Coding?</h2>
                    <p>Join thousands of developers already improving their skills with CodeQuiz</p>
                    <button className="cta-button primary large" onClick={handleGetStarted}>
                        {isAuthenticated ? "Start Your First Quiz" : "Start Learning for Free"}
                    </button>
                    {!isAuthenticated && (
                        <p className="cta-subtext">No credit card required &bull; Instant access</p>
                    )}
                </div>
            </section>

            {/* FOOTER */}
            <footer className="landing-footer">
                <div className="footer-content">
                    <div className="footer-section">
                        <h4>CodeQuiz</h4>
                        <p>AI-powered programming quizzes for developers everywhere.</p>
                    </div>
                    <div className="footer-section">
                        <h4>Platform</h4>
                        <ul>
                            <li><a href="#features">Features</a></li>
                            <li><a href="#how-it-works">How It Works</a></li>
                            <li><a href="#languages">Languages</a></li>
                        </ul>
                    </div>
                    <div className="footer-section">
                        <h4>Account</h4>
                        <ul>
                            <li><a href="#" onClick={() => navigate("/register")}>Register</a></li>
                            <li><a href="#" onClick={() => navigate("/login")}>Login</a></li>
                            {isAuthenticated && (
                                <li><a href="#" onClick={() => navigate("/user")}>Profile</a></li>
                            )}
                        </ul>
                    </div>
                </div>
                <div className="footer-bottom">
                    <p>&copy; 2026 CodeQuiz. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}

export default LandingPage;