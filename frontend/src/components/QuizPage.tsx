import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import Navbar from "./Navbar";
import { useAuth } from "../utils/AuthContext";
import { useHint } from "../hooks/useHint"; 

const XP_PER_CORRECT = 10;

interface QuizQuestion {
    title: string;
    question: string;
    options: string[];
    correct_answer: string;
}

/* ── responsive CSS injected once ── */
const quizCss = `
.quiz-page {
    min-height: 100vh;
    background-color: #1a1a1a;
    display: flex;
    flex-direction: column;
}

/* ── top header strip ── */
.quiz-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 2.5rem;
    background: #232323;
    border-bottom: 1px solid #2f2f2f;
    flex-wrap: wrap;
}
.quiz-header__xp {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}
.quiz-header__xp-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #ff9500, #ff7700);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 700; color: #1a1a1a;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(255,149,0,.35);
}
.quiz-header__xp-text {
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
    color: #ccc;
    white-space: nowrap;
}
.quiz-header__xp-text strong {
    color: #ff9500;
    font-size: 0.95rem;
}
.quiz-header__level {
    font-family: 'Fira Code', monospace;
    font-weight: 700;
    font-size: 0.8rem;
    color: #1a1a1a;
    background: #ff9500;
    padding: 2px 10px;
    border-radius: 6px;
}
.quiz-header__xp-bar-wrap {
    width: 110px;
    height: 7px;
    background: #3d3d3d;
    border-radius: 6px;
    overflow: hidden;
}
.quiz-header__xp-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #ff9500, #ffb347);
    border-radius: 6px;
    transition: width .4s ease;
}
.quiz-header__progress {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1 1 auto;
    justify-content: center;
    min-width: 180px;
}
.quiz-header__progress-label {
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
    color: #999;
    white-space: nowrap;
}
.quiz-header__progress-bar {
    flex: 1;
    max-width: 260px;
    height: 8px;
    background: #3d3d3d;
    border-radius: 8px;
    overflow: hidden;
}
.quiz-header__progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #ff9500, #ff7700);
    border-radius: 8px;
    transition: width .35s ease;
}
.quiz-header__quit {
    font-family: 'Fira Code', monospace;
    font-size: 0.82rem;
    font-weight: 600;
    color: #ff4d4d;
    background: rgba(255,77,77,.1);
    border: 1px solid rgba(255,77,77,.35);
    border-radius: 8px;
    padding: 6px 18px;
    cursor: pointer;
    transition: all .2s ease;
    white-space: nowrap;
}
.quiz-header__quit:hover {
    background: rgba(255,77,77,.22);
    border-color: #ff4d4d;
    transform: translateY(-1px);
}

/* ── main content area ── */
.quiz-body {
    flex: 1;
    display: flex;
    align-items: stretch;
    justify-content: center;
    padding: 0.5rem 0.5rem 1rem;
    min-height: 0;
}
.quiz-card {
    width: 100%;
    max-width: 1100px;
    background: #2d2d2d;
    border-radius: 18px;
    padding: 4rem 4rem 3rem 4rem;
    box-shadow: 0 10px 40px rgba(0,0,0,.35);
    border: 1px solid #3d3d3d;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 70vh;
}

/* ── question ── */
.quiz-card__title {
    color: #ff9500;
    font-size: 1.35rem;
    margin: 0 0 0.75rem;
    font-family: 'Fira Code', monospace;
    font-weight: 600;
}
.quiz-card__question {
    color: #fff;
    font-size: 2.2rem;
    margin: 2.5rem 0 2.5rem 0;
    font-family: 'Fira Code', monospace;
    line-height: 1.4;
    text-align: center;
    font-weight: 700;
    flex: 1 1 auto;
    word-break: break-word;
}

/* ── hint button & panel ── */       /* ← ADDED */
.quiz-hint-row {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
}
.quiz-hint-btn {
    background: transparent;
    border: 1px solid #4d4d4d;
    border-radius: 8px;
    color: #aaa;
    font-family: 'Fira Code', monospace;
    font-size: 0.82rem;
    padding: 5px 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all .2s ease;
}
.quiz-hint-btn:hover {
    border-color: #ff9500;
    color: #ff9500;
}
.quiz-hint-panel {
    background: rgba(255,149,0,.07);
    border: 1px solid rgba(255,149,0,.25);
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 1rem;
}
.quiz-hint-panel ul {
    margin: 0;
    padding-left: 1.2rem;
}
.quiz-hint-panel li {
    color: #ffb347;
    font-family: 'Fira Code', monospace;
    font-size: 0.88rem;
    line-height: 1.6;
}

/* ── options ── */
.quiz-options {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.quiz-option {
    background: #3d3d3d;
    color: #e0e0e0;
    border: 2px solid #4d4d4d;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    font-size: 1rem;
    font-family: 'Fira Code', monospace;
    cursor: pointer;
    text-align: left;
    transition: all .2s ease;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.quiz-option:hover:not(.quiz-option--disabled) {
    border-color: #ff9500;
    background: #454545;
    transform: translateX(4px);
}
.quiz-option--disabled {
    cursor: not-allowed;
    opacity: 0.6;
}
.quiz-option--correct {
    background: rgba(76,175,80,.2);
    border-color: #4caf50;
    color: #4caf50;
}
.quiz-option--incorrect {
    background: rgba(244,67,54,.2);
    border-color: #f44336;
    color: #f44336;
}
.quiz-option__letter {
    background: #ff9500;
    color: #1a1a1a;
    width: 34px; height: 34px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
    font-size: 0.95rem;
}

/* ── feedback ── */
.quiz-feedback {
    padding: 0.75rem 1rem;
    border-radius: 10px;
    margin-bottom: 1.25rem;
    font-family: 'Fira Code', monospace;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
}
.quiz-feedback--correct {
    background: rgba(76,175,80,.15);
    color: #4caf50;
    border: 1px solid rgba(76,175,80,.3);
}
.quiz-feedback--incorrect {
    background: rgba(244,67,54,.15);
    color: #f44336;
    border: 1px solid rgba(244,67,54,.3);
}

/* ── level up ── */
.quiz-levelup {
    padding: 1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.25rem;
    background: linear-gradient(135deg, rgba(255,215,0,.2), rgba(255,149,0,.15));
    border: 2px solid rgba(255,215,0,.5);
    text-align: center;
    animation: levelUpPulse .6s ease-out;
}
.quiz-levelup span {
    color: #ffd700;
    font-size: 1.15rem;
    font-weight: 700;
    font-family: 'Fira Code', monospace;
}

/* ── completion screen ── */
.quiz-complete {
    text-align: center;
    padding: 3rem 2rem;
}
.quiz-complete__badge {
    width: 88px; height: 88px;
    margin: 0 auto 28px;
    background: linear-gradient(135deg, #ff9500, #ff7700);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 36px rgba(255,149,0,.45);
    font-size: 2.2rem; color: #1a1a1a; font-weight: 700;
}
.quiz-complete__title {
    color: #ff9500;
    font-size: 2rem;
    margin: 0 0 .75rem;
    font-family: 'Fira Code', monospace;
    font-weight: 700;
}
.quiz-complete__text {
    color: #e0e0e0;
    font-size: 1.1rem;
    margin: 0 0 1.75rem;
    font-family: 'Fira Code', monospace;
}
.quiz-complete__xp-box {
    background: linear-gradient(135deg, rgba(255,149,0,.15), rgba(255,119,0,.1));
    border: 1px solid rgba(255,149,0,.3);
    border-radius: 12px;
    padding: 18px 28px;
    margin-bottom: 28px;
    display: inline-block;
}
.quiz-complete__xp-box span {
    color: #ff9500;
    font-size: 1.5rem;
    font-weight: 700;
    font-family: 'Fira Code', monospace;
}
.quiz-btn-primary {
    background: #ff9500;
    color: #1a1a1a;
    border: none;
    border-radius: 8px;
    padding: .8rem 2.4rem;
    font-size: 1rem;
    font-family: 'Fira Code', monospace;
    font-weight: 600;
    cursor: pointer;
    transition: all .2s ease;
}
.quiz-btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(255,149,0,.45);
}

/* ── empty state ── */
.quiz-empty {
    text-align: center;
    padding: 4rem 2rem;
}
.quiz-empty p {
    color: #808080;
    font-size: 1.1rem;
    margin-bottom: 1.5rem;
    font-family: 'Fira Code', monospace;
}

/* ── animations ── */
@keyframes xpFloat {
    0%   { opacity: 0; transform: translateY(10px) scale(.8); }
    50%  { opacity: 1; transform: translateY(-5px) scale(1.1); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes levelUpPulse {
    0%   { opacity: 0; transform: scale(.85); }
    50%  { transform: scale(1.04); }
    100% { opacity: 1; transform: scale(1); }
}

/* ── responsive ── */
@media (max-width: 768px) {
    .quiz-header { padding: 0.6rem 1rem; gap: 0.6rem; }
    .quiz-header__progress { min-width: 0; }
    .quiz-header__progress-bar { max-width: 120px; }
    .quiz-header__xp-bar-wrap { width: 70px; }
    .quiz-body { padding: 1.5rem 1rem 2rem; }
    .quiz-card { padding: 1.5rem 1.25rem; border-radius: 14px; }
    .quiz-card__question { font-size: 1.05rem; }
    .quiz-option { padding: 0.85rem 1rem; font-size: 0.92rem; }
}
@media (max-width: 480px) {
    .quiz-header { flex-direction: column; align-items: stretch; }
    .quiz-header__progress { justify-content: flex-start; }
    .quiz-header__quit { align-self: flex-end; }
    .quiz-card { padding: 1.25rem 1rem; }
    .quiz-card__title { font-size: 1.1rem; }
    .quiz-card__question { font-size: 0.98rem; }
}
`;

const quizSessionKey = (userId: number) => `quizPageSession_${userId}`;

function QuizPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { token, updateUser, user } = useAuth();

    const { hints, loading: hintLoading, fetchMcqHint, clearHints } = useHint();

    const QUIZ_SESSION_KEY = user ? quizSessionKey(user.id) : null;

    const savedSession = (() => {
        try {
            if (!QUIZ_SESSION_KEY) return null;
            const raw = sessionStorage.getItem(QUIZ_SESSION_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    })();

    const isFreshQuiz = Boolean(
        location.state?.quizData?.length &&
        (!savedSession || savedSession.sessionId !== location.state.sessionId)
    );

    const [quiz] = useState<QuizQuestion[]>(() => {
        if (isFreshQuiz) return location.state.quizData;
        return savedSession?.quiz ?? location.state?.quizData ?? [];
    });

    const [sessionId] = useState<number>(() => {
        if (isFreshQuiz) return location.state.sessionId ?? Date.now();
        return savedSession?.sessionId ?? location.state?.sessionId ?? Date.now();
    });

    const [currentIndex, setCurrentIndex] = useState<number>(() => {
        if (isFreshQuiz) return 0;
        return savedSession?.currentIndex ?? 0;
    });

    const [finished, setFinished] = useState<boolean>(() => {
        if (isFreshQuiz) return false;
        return savedSession?.finished ?? false;
    });

    const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
    const [showXpAnimation, setShowXpAnimation] = useState(false);

    const [totalXpEarned, setTotalXpEarned] = useState<number>(() => {
        if (isFreshQuiz) return 0;
        return savedSession?.totalXpEarned ?? 0;
    });

    const [answered, setAnswered] = useState(false);
    const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
    const [correctAnswerIndex, setCorrectAnswerIndex] = useState<number | null>(null);

    const [levelUpInfo, setLevelUpInfo] = useState<{ show: boolean; newLevel: number | null }>({ show: false, newLevel: null });

    useEffect(() => {
        if (quiz.length && QUIZ_SESSION_KEY) {
            sessionStorage.setItem(QUIZ_SESSION_KEY, JSON.stringify({
                sessionId,
                quiz,
                currentIndex,
                finished,
                totalXpEarned,
            }));
        }
    }, [sessionId, quiz, currentIndex, finished, totalXpEarned, QUIZ_SESSION_KEY]);

    useEffect(() => {
        setAnswered(false);
        setSelectedAnswer(null);
        setCorrectAnswerIndex(null);
        clearHints();
    }, [currentIndex]);

    async function addXpToUser() {
        if (!token) return;
        try {
            const response = await fetch('http://127.0.0.1:8000/add-xp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ xp_amount: XP_PER_CORRECT })
            });

            if (response.ok) {
                const data = await response.json();
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const { xp_gained, leveled_up, new_level, ...updatedUser } = data;
                updateUser(updatedUser);

                if (leveled_up && new_level) {
                    setLevelUpInfo({ show: true, newLevel: new_level });
                    setTimeout(() => setLevelUpInfo({ show: false, newLevel: null }), 3000);
                }
            }
        } catch (error) {
            console.error("Error adding XP:", error);
        }
    }

    function handleQuitQuiz() {
        if (QUIZ_SESSION_KEY) sessionStorage.removeItem(QUIZ_SESSION_KEY);
        navigate('/prompt');
    }

    const currentQ = quiz[currentIndex];
    const progress = quiz.length > 0 ? ((currentIndex) / quiz.length) * 100 : 0;

    if (!quiz.length) {
        return (
            <>
                <style>{quizCss}</style>
                <div className="quiz-page">
                    <Navbar />
                    <div className="quiz-body">
                        <div className="quiz-card quiz-empty">
                            <p>No quiz data found. Go back and generate a quiz first.</p>
                            <button className="quiz-btn-primary" onClick={handleQuitQuiz}>
                                Back to Prompt
                            </button>
                        </div>
                    </div>
                </div>
            </>
        );
    }

    function handleAnswer(_option: string, index: number) {
        if (answered) return;

        const letterFromIndex = ["A", "B", "C", "D"][index];
        const isCorrect = letterFromIndex === currentQ.correct_answer;
        const correctIdx = ["A", "B", "C", "D"].indexOf(currentQ.correct_answer);

        setAnswered(true);
        setSelectedAnswer(index);
        setCorrectAnswerIndex(correctIdx);

        if (isCorrect) {
            setShowXpAnimation(true);
            setTotalXpEarned(prev => prev + XP_PER_CORRECT);
            addXpToUser();
            setFeedbackMessage("Correct!");
        } else {
            setFeedbackMessage(`Incorrect! The correct answer was ${currentQ.correct_answer}.`);
        }

        setTimeout(() => {
            setFeedbackMessage(null);
            setShowXpAnimation(false);
            if (currentIndex + 1 < quiz.length) {
                setCurrentIndex(currentIndex + 1);
            } else {
                setFinished(true);
            }
        }, 2000);
    }

    const headerBar = (
        <div className="quiz-header">
            <div className="quiz-header__xp">
                <span className="quiz-header__xp-icon">⚡</span>
                {user && (
                    <>
                        <span className="quiz-header__level">LVL {user.level}</span>
                        <div className="quiz-header__xp-bar-wrap">
                            <div
                                className="quiz-header__xp-bar-fill"
                                style={{ width: `${(user.exp / (user.xp_required ?? 100)) * 100}%` }}
                            />
                        </div>
                        <span className="quiz-header__xp-text">
                            <strong>{user.exp}</strong>/{user.xp_required ?? 100} XP
                        </span>
                    </>
                )}
            </div>

            {!finished && (
                <div className="quiz-header__progress">
                    <span className="quiz-header__progress-label">
                        Question {currentIndex + 1}/{quiz.length}
                    </span>
                    <div className="quiz-header__progress-bar">
                        <div
                            className="quiz-header__progress-fill"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            )}

            <button className="quiz-header__quit" onClick={handleQuitQuiz}>
                ✕ Quit Quiz
            </button>
        </div>
    );

    if (finished) {
        return (
            <>
                <style>{quizCss}</style>
                <div className="quiz-page">
                    <Navbar />
                    {headerBar}
                    <div className="quiz-body">
                        <div className="quiz-card quiz-complete">
                            <div className="quiz-complete__badge">✓</div>
                            <h1 className="quiz-complete__title">Quiz Complete!</h1>
                            <p className="quiz-complete__text">
                                Great job! You've completed all {quiz.length} questions.
                            </p>
                            <div className="quiz-complete__xp-box">
                                <span>+{totalXpEarned} XP Earned!</span>
                            </div>
                            <br />
                            <button className="quiz-btn-primary" onClick={handleQuitQuiz}>
                                Create Another Quiz
                            </button>
                        </div>
                    </div>
                </div>
            </>
        );
    }

    if (!currentQ) {
        return <p style={{ color: '#808080', textAlign: 'center', padding: '2rem' }}>No quiz data found</p>;
    }

    /* ── Active quiz screen ── */
    return (
        <>
            <style>{quizCss}</style>
            <div className="quiz-page">
                <Navbar />
                {headerBar}

                <div className="quiz-body">
                    <div className="quiz-card">
                        <h2 className="quiz-card__title">{currentQ.title}</h2>
                        <h3 className="quiz-card__question">{currentQ.question}</h3>

                        {/* Level Up Banner */}
                        {levelUpInfo.show && (
                            <div className="quiz-levelup">
                                <span>🎉 Level Up! You're now Level {levelUpInfo.newLevel}!</span>
                            </div>
                        )}

                        {/* Feedback */}
                        {feedbackMessage && (
                            <div className={`quiz-feedback ${feedbackMessage.includes('Correct') ? 'quiz-feedback--correct' : 'quiz-feedback--incorrect'}`}>
                                <span>{feedbackMessage}</span>
                                {showXpAnimation && (
                                    <span style={{
                                        color: '#ff9500',
                                        fontWeight: 700,
                                        animation: 'xpFloat 0.8s ease-out forwards',
                                    }}>
                                        +{XP_PER_CORRECT} XP
                                    </span>
                                )}
                            </div>
                        )}

                        {/* ── Hint button & panel ── */}
                        {!answered && (
                            <div className="quiz-hint-row">
                                <button
                                    className="quiz-hint-btn"
                                    onClick={() =>
                                        hints.length
                                            ? clearHints()
                                            : fetchMcqHint(currentQ.question, currentQ.options)
                                    }
                                    title={hints.length ? "Hide hints" : "Get a hint"}
                                >
                                    {hintLoading ? "..." : hints.length ? "💡 Hide Hints" : "💡 Hint"}
                                </button>
                            </div>
                        )}

                        {hints.length > 0 && !answered && (
                            <div className="quiz-hint-panel">
                                <ul>
                                    {hints.map((hint, i) => (
                                        <li key={i}>{hint}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {/* ── END hint ── */}

                        {/* Options */}
                        <div className="quiz-options">
                            {currentQ.options.map((opt: string, i: number) => {
                                let optionClass = "quiz-option";

                                if (answered) {
                                    optionClass += " quiz-option--disabled";
                                    if (i === correctAnswerIndex) {
                                        optionClass += " quiz-option--correct";
                                    } else if (i === selectedAnswer) {
                                        optionClass += " quiz-option--incorrect";
                                    }
                                }

                                return (
                                    <button
                                        key={i}
                                        className={optionClass}
                                        onClick={() => handleAnswer(opt, i)}
                                        disabled={answered}
                                    >
                                        <span className="quiz-option__letter">
                                            {["A", "B", "C", "D"][i]}
                                        </span>
                                        {opt}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default QuizPage;