import Navbar from "../layout/Navbar";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../utils/AuthContext";
import '../../css-files/pages/AboutPage.css';

function AboutPage() {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuth();

    return (
        <div className="about-page-wrapper">
            <Navbar />

            {/* HERO */}
            <section className="about-hero">
                <div className="about-hero-content">
                    <span className="about-tag">// about the platform</span>
                    <h1 className="about-hero-title">
                        Built to make you a <span className="about-highlight">better developer</span>
                    </h1>
                    <p className="about-hero-sub">
                        CodeQuiz is an AI-powered learning platform that generates personalised coding
                        quizzes and challenges. Whether you are a student picking up your first language
                        or an experienced engineer sharpening your skills, CodeQuiz adapts to your level
                        and keeps you progressing.
                    </p>
                </div>
            </section>

            {/* PLATFORM FEATURES */}
            <section className="about-section about-section-alt">
                <div className="about-section-inner">
                    <div className="about-section-header">
                        <h2>What the platform offers</h2>
                        <p>Two complementary ways to practise and grow</p>
                    </div>

                    <div className="about-offer-grid">
                        <div className="about-offer-card">
                            <div className="about-offer-icon">
                                <span className="about-icon-bracket">[</span>
                                MCQ
                                <span className="about-icon-bracket">]</span>
                            </div>
                            <h3>Multiple-Choice Quizzes</h3>
                            <p>
                                Instantly generated quizzes covering language syntax, data structures,
                                algorithms, and design patterns. Each quiz is created on the fly by
                                an AI model so you never see the same questions twice. After submitting,
                                you receive a detailed score alongside per-question explanations so you
                                understand exactly where you went right or wrong.
                            </p>
                        </div>

                        <div className="about-offer-card">
                            <div className="about-offer-icon">
                                <span className="about-icon-bracket">{"{"}</span>
                                CODE
                                <span className="about-icon-bracket">{"}"}</span>
                            </div>
                            <h3>Coding Challenges</h3>
                            <p>
                                Solve real programming problems inside a full in-browser code editor
                                powered by Monaco (the same editor that runs VS Code). The AI generates
                                a problem statement, a starter code stub, and automated test cases. Run
                                your solution against the test suite and see which cases pass or fail
                                in real time — no local setup required.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* HOW THE AI WORKS */}
            <section className="about-section">
                <div className="about-section-inner">
                    <div className="about-section-header">
                        <h2>How the AI works</h2>
                        <p>Intelligent generation and adaptive difficulty</p>
                    </div>

                    <div className="about-ai-grid">
                        <div className="about-ai-card">
                            <div className="about-ai-number">01</div>
                            <h3>You set the parameters</h3>
                            <p>
                                Choose your programming language, describe the topic you want to focus on,
                                pick the number of questions, and select a difficulty range. The platform
                                supports over 12 languages including Python, JavaScript, TypeScript, Java,
                                C++, C#, Go, Rust, Ruby, and PHP.
                            </p>
                        </div>

                        <div className="about-ai-card">
                            <div className="about-ai-number">02</div>
                            <h3>The AI generates content</h3>
                            <p>
                                Your prompt is sent to one of the supported AI models — OpenAI GPT or a
                                locally hosted Llama 3.1 (8B) model. The model produces unique, contextually
                                relevant questions or coding challenges tailored to your request, and a
                                machine-learning difficulty classifier validates the predicted difficulty
                                before the content reaches you.
                            </p>
                        </div>

                        <div className="about-ai-card">
                            <div className="about-ai-number">03</div>
                            <h3>You practise and get feedback</h3>
                            <p>
                                Complete the quiz or coding challenge. Answers and code submissions are
                                evaluated immediately. For coding problems your code runs securely in a
                                sandboxed execution environment and results are returned test case by test case.
                            </p>
                        </div>

                        <div className="about-ai-card">
                            <div className="about-ai-number">04</div>
                            <h3>Your progress is tracked</h3>
                            <p>
                                Every completed session updates your profile. Earn XP, level up, and
                                review your historical performance over time. The platform uses your
                                past results to surface personalised statistics so you can focus on
                                the areas that matter most.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* TECH STACK */}
            <section className="about-section about-section-alt">
                <div className="about-section-inner">
                    <div className="about-section-header">
                        <h2>Under the hood</h2>
                        <p>A modern, end-to-end stack</p>
                    </div>

                    <div className="about-tech-grid">
                        <div className="about-tech-card">
                            <span className="about-tech-label">Frontend</span>
                            <ul>
                                <li>React 18 + TypeScript</li>
                                <li>Vite</li>
                                <li>Monaco Editor (VS Code engine)</li>
                                <li>React Router</li>
                            </ul>
                        </div>

                        <div className="about-tech-card">
                            <span className="about-tech-label">Backend</span>
                            <ul>
                                <li>FastAPI (Python)</li>
                                <li>SQLAlchemy + PostgreSQL</li>
                                <li>JWT authentication</li>
                                <li>Sandboxed code execution</li>
                            </ul>
                        </div>

                        <div className="about-tech-card">
                            <span className="about-tech-label">AI / ML</span>
                            <ul>
                                <li>OpenAI GPT API</li>
                                <li>Llama 3.1 8B (Ollama)</li>
                                <li>ML difficulty classifier</li>
                                <li>Topic classifier</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="about-cta-section">
                <div className="about-cta-inner">
                    <h2>Ready to start coding?</h2>
                    <p>Join CodeQuiz and turn practice sessions into real progress.</p>
                    <button
                        className="about-cta-button"
                        onClick={() => navigate(isAuthenticated ? "/prompt" : "/register")}
                    >
                        {isAuthenticated ? "Go to Quiz" : "Get Started Free"}
                    </button>
                </div>
            </section>
        </div>
    );
}

export default AboutPage;
