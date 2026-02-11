import '../css-files/PromptPage.css'  
import Navbar from "./Navbar";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../utils/AuthContext";
import mcqIcon from "../assets/imgs/test.png";
import codeIcon from "../assets/imgs/web-development.png";
import userIcon from "../assets/imgs/user.png";

type QuizType = "mcq" | "coding";

const programmingLanguages = [
    "JavaScript",
    "Python",
    "TypeScript",
    "Java",
    "C++",
    "C#",
    "Go",
    "Rust",
    "Ruby",
    "PHP",
];

const models = [
    { value: "openai", label: "OpenAI GPT" },
    { value: "llama3.1:8b", label: "Llama 3.1 (8B)" },
];

function PromptPage(){
    const { isAuthenticated, user } = useAuth();
    const [selectedModel, setSelectedModel] = useState<string>("");
    const [quizType, setQuizType] = useState<QuizType | null>(null);
    const [selectedLanguage, setSelectedLanguage] = useState<string>("");
    const [numQuestions, setNumQuestions] = useState<number>(5);
    const [prompt, setPrompt] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [loadingTip, setLoadingTip] = useState(0);
    const navigate = useNavigate();

    const mcqTips = [
        "Crafting challenging questions...",
        "Generating answer options...",
        "Validating correct answers...",
        "Polishing quiz content...",
        "Almost there...",
    ];

    const codingTips = [
        "Designing coding challenges...",
        "Generating starter code stubs...",
        "Building test cases...",
        "Crafting helpful hints...",
        "Finalising challenges...",
    ];

    const tips = quizType === 'coding' ? codingTips : mcqTips;

    useEffect(() => {
        if (!loading) return;
        setLoadingTip(0);
        const interval = setInterval(() => {
            setLoadingTip(prev => (prev + 1) % tips.length);
        }, 3500);
        return () => clearInterval(interval);
    }, [loading, tips.length]);

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return (
            <>
                <Navbar />
                <div className="prompt-page">
                    <div className="auth-required-container">
                        <div className="auth-required-card">
                            <div className="auth-required-icon">
                                <img src={userIcon} alt="Login Required" />
                            </div>
                            <h2 className="auth-required-title">Login Required</h2>
                            <p className="auth-required-text">
                                You need to be logged in to generate quizzes and track your progress.
                            </p>
                            <div className="auth-required-buttons">
                                <button 
                                    className="auth-login-button"
                                    onClick={() => navigate('/login')}
                                >
                                    Login
                                </button>
                                <button 
                                    className="auth-register-button"
                                    onClick={() => navigate('/register')}
                                >
                                    Register
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </>
        );
    }

    async function handleModelChange(model: string) {
        setSelectedModel(model);
        try {
            await fetch("http://127.0.0.1:8000/model", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model })
            });
        } catch (error) {
            console.error("Error setting model:", error);
        }
    }

    async function handleSubmit() {
        setError("");

        if (!quizType) {
            setError("Please select a quiz type.");
            return;
        }

        if (!selectedModel) {
            setError("Please select an AI model.");
            return;
        }

        if (!prompt.trim()) {
            setError("Please enter a prompt describing what you want to learn.");
            return;
        }

        if (quizType === 'coding' && !selectedLanguage) {
            setError("Please select a programming language.");
            return;
        }

        // Send prompt to backend for both MCQ and coding quizzes
        setLoading(true);
        try {
            const response = await fetch('http://127.0.0.1:8000/prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: prompt,
                    quiz_type: quizType,
                    language: selectedLanguage,
                    num_questions: numQuestions
                })
            });

            const quiz = await response.json();
            console.log("Quiz from backend:", quiz);
            
            if (quizType === 'coding') {
                navigate('/code-sandbox', { state: { quizData: quiz, language: selectedLanguage, sessionId: Date.now() } });
            } else {
                navigate('/quiz', { state: { quizData: quiz, sessionId: Date.now() } });
            }
        } catch (error) {
            console.error("Error submitting prompt:", error);
            setError("Failed to generate quiz. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    return(
        <>
        <Navbar />
        {loading && (
            <div className="loading-overlay">
                <div className="loading-card">
                    {/* Animated icon */}
                    <div className="loading-icon-wrapper">
                        {quizType === 'coding' ? (
                            <div className="loading-code-icon">
                                <span className="code-bracket">&lt;</span>
                                <span className="code-slash">/</span>
                                <span className="code-bracket">&gt;</span>
                            </div>
                        ) : (
                            <div className="loading-mcq-icon">
                                <span className="mcq-letter">A</span>
                                <span className="mcq-letter">B</span>
                                <span className="mcq-letter">C</span>
                                <span className="mcq-letter">D</span>
                            </div>
                        )}
                    </div>

                    <h2 className="loading-title">
                        {quizType === 'coding' ? 'Building Your Coding Challenges' : 'Generating Your Quiz'}
                    </h2>

                    {/* Progress bar */}
                    <div className="loading-progress-track">
                        <div className="loading-progress-bar" />
                    </div>

                    <p className="loading-tip" key={loadingTip}>{tips[loadingTip]}</p>

                    <p className="loading-subtext">This may take up to a minute depending on the model</p>
                </div>
            </div>
        )}
        <div className="prompt-page">
            {/* Resume Active Quiz Banner */}
            {(() => {
                const userId = user?.id;
                if (!userId) return null;
                try {
                    const mcqRaw = sessionStorage.getItem(`quizPageSession_${userId}`);
                    if (mcqRaw) {
                        const mcq = JSON.parse(mcqRaw);
                        if (mcq?.quiz?.length && !mcq.finished) {
                            return (
                                <div className="resume-banner">
                                    <div className="resume-banner-content">
                                        <div className="resume-banner-text">
                                            <span className="resume-banner-icon">&#9654;</span>
                                            <div>
                                                <strong>Quiz in progress</strong>
                                                <span className="resume-banner-detail">
                                                    Question {(mcq.currentIndex ?? 0) + 1} of {mcq.quiz.length}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="resume-banner-actions">
                                            <button className="resume-banner-btn" onClick={() => navigate('/quiz')}>Resume Quiz</button>
                                            <button className="resume-banner-dismiss" onClick={() => { sessionStorage.removeItem(`quizPageSession_${userId}`); navigate(0); }}>Discard</button>
                                        </div>
                                    </div>
                                </div>
                            );
                        }
                    }
                    const codeRaw = sessionStorage.getItem(`codeSandboxSession_${userId}`);
                    if (codeRaw) {
                        const code = JSON.parse(codeRaw);
                        if (code?.questions?.length && !code.finished) {
                            return (
                                <div className="resume-banner">
                                    <div className="resume-banner-content">
                                        <div className="resume-banner-text">
                                            <span className="resume-banner-icon">&#9654;</span>
                                            <div>
                                                <strong>Coding challenge in progress</strong>
                                                <span className="resume-banner-detail">
                                                    Challenge {(code.currentIndex ?? 0) + 1} of {code.questions.length} &middot; {(code.language ?? 'code').toUpperCase()}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="resume-banner-actions">
                                            <button className="resume-banner-btn" onClick={() => navigate('/code-sandbox')}>Resume Challenge</button>
                                            <button className="resume-banner-dismiss" onClick={() => { sessionStorage.removeItem(`codeSandboxSession_${userId}`); navigate(0); }}>Discard</button>
                                        </div>
                                    </div>
                                </div>
                            );
                        }
                    }
                } catch (e) { /* ignore */ }
                return null;
            })()}

            {/* Header Section */}
            <div className="prompt-header">
                <h1 className="prompt-page-title">Create Your Quiz</h1>
                <p className="prompt-page-subtitle">
                    Choose your quiz type, select a model, and describe what you want to learn
                </p>
            </div>

            {/* Main Content */}
            <div className="prompt-content">
                {/* Step 1: Quiz Type */}
                <div className="prompt-section">
                    <div className="section-header">
                        <span className="step-number">1</span>
                        <h2 className="section-title">Choose Quiz Type</h2>
                    </div>
                    <div className="quiz-type-cards">
                        <div 
                            className={`quiz-card ${quizType === 'mcq' ? 'selected' : ''}`}
                            onClick={() => setQuizType('mcq')}
                        >
                            <div className="quiz-card-icon">
                                <img src={mcqIcon} alt="MCQ Quiz" />
                            </div>
                            <div className="quiz-card-content">
                                <h3>Multiple Choice</h3>
                                <p>Test your knowledge with AI-generated questions and instant feedback</p>
                            </div>
                            <div className="quiz-card-check">
                                {quizType === 'mcq' && <span className="checkmark"></span>}
                            </div>
                        </div>
                        <div 
                            className={`quiz-card ${quizType === 'coding' ? 'selected' : ''}`}
                            onClick={() => setQuizType('coding')}
                        >
                            <div className="quiz-card-icon">
                                <img src={codeIcon} alt="Coding Quiz" />
                            </div>
                            <div className="quiz-card-content">
                                <h3>Coding Sandbox</h3>
                                <p>Solve programming challenges with a built-in code editor and test cases</p>
                            </div>
                            <div className="quiz-card-check">
                                {quizType === 'coding' && <span className="checkmark"></span>}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Step 2: Configuration Row */}
                <div className="prompt-section">
                    <div className="section-header">
                        <span className="step-number">2</span>
                        <h2 className="section-title">Configure Settings</h2>
                    </div>
                    <div className="config-row">
                        <div className="config-item">
                            <label className="config-label">AI Model</label>
                            <select 
                                className="config-select"
                                value={selectedModel}
                                onChange={(e) => handleModelChange(e.target.value)}
                            >
                                <option value="" disabled hidden>Select model...</option>
                                {models.map((model) => (
                                    <option key={model.value} value={model.value}>
                                        {model.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        
                        {quizType === 'coding' && (
                            <div className="config-item">
                                <label className="config-label">Language</label>
                                <select 
                                    className="config-select"
                                    value={selectedLanguage}
                                    onChange={(e) => setSelectedLanguage(e.target.value)}
                                >
                                    <option value="" disabled hidden>Select language...</option>
                                    {programmingLanguages.map((lang) => (
                                        <option key={lang} value={lang.toLowerCase()}>
                                            {lang}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="config-item">
                            <label className="config-label">Number of Questions</label>
                            <div className="question-count-control">
                                <button
                                    className="count-btn"
                                    onClick={() => setNumQuestions(prev => Math.max(1, prev - 1))}
                                    disabled={numQuestions <= 1}
                                    type="button"
                                >
                                    −
                                </button>
                                <span className="count-display">{numQuestions}</span>
                                <button
                                    className="count-btn"
                                    onClick={() => setNumQuestions(prev => Math.min(quizType === 'coding' ? 10 : 20, prev + 1))}
                                    disabled={numQuestions >= (quizType === 'coding' ? 10 : 20)}
                                    type="button"
                                >
                                    +
                                </button>
                            </div>
                            <span className="config-hint">Max: {quizType === 'coding' ? 10 : 20}</span>
                        </div>
                    </div>
                </div>

                {/* Step 3: Prompt */}
                <div className="prompt-section">
                    <div className="section-header">
                        <span className="step-number">3</span>
                        <h2 className="section-title">Describe Your Quiz</h2>
                    </div>
                    <div className="prompt-input-container">
                        <textarea 
                            className="prompt-textarea"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder={quizType === 'coding' 
                                ? "Describe the coding challenges you want... (e.g., 'Create 5 array manipulation problems focusing on sorting algorithms')"
                                : "What topic would you like to be quizzed on? (e.g., 'JavaScript async/await and promises')"
                            }
                        />
                        <div className="prompt-input-footer">
                            <span className="char-count">{prompt.length} characters</span>
                        </div>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="prompt-error">
                        <span className="error-icon">!</span>
                        {error}
                    </div>
                )}

                {/* Submit Button */}
                <button 
                    className="generate-button"
                    onClick={handleSubmit}
                    disabled={loading || !quizType || !selectedModel || !prompt.trim() || (quizType === 'coding' && !selectedLanguage)}
                >
                    <span className="button-text">{loading ? 'Generating...' : 'Generate Quiz'}</span>
                    {!loading && <span className="button-arrow">→</span>}
                </button>
            </div>
        </div>
        </>
    )
}

export default PromptPage;