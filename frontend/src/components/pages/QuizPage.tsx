import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import Navbar from "../layout/Navbar";
import { useAuth } from "../../utils/AuthContext";
import '../../css-files/pages/QuizPage.css'

const XP_PER_MCQ_DIFFICULTY: Record<string, number> = {
    easy: 15,
    medium: 25,
    hard: 40,
};

interface QuizQuestion {
    title: string;
    question: string;
    options: string[];
    correct_answer: string;
    difficulty?: string;
    topic_tags?: string[];
}

interface QuestionResult {
    question: string;
    options: string[];
    correct_answer: string;
    userAnswer: string | null;
    isCorrect: boolean;
}

const quizSessionKey = (userId: number) => `quizPageSession_${userId}`;

function QuizPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { token, updateUser, user } = useAuth();

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

    const [quizPrompt] = useState<string>(() => {
        if (isFreshQuiz) return location.state?.prompt ?? "";
        return savedSession?.quizPrompt ?? location.state?.prompt ?? "";
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

    const correctCountRef = useRef(isFreshQuiz ? 0 : (savedSession?.correctCount ?? 0));
    const startTimeRef = useRef<number>(isFreshQuiz ? Date.now() : (savedSession?.startTime ?? Date.now()));
    const questionResultsRef = useRef<QuestionResult[]>(isFreshQuiz ? [] : (savedSession?.questionResults ?? []));

    useEffect(() => {
        if (quiz.length && QUIZ_SESSION_KEY) {
            sessionStorage.setItem(QUIZ_SESSION_KEY, JSON.stringify({
                sessionId,
                quiz,
                currentIndex,
                finished,
                totalXpEarned,
                correctCount: correctCountRef.current,
                quizPrompt,
                startTime: startTimeRef.current,
                questionResults: questionResultsRef.current,
            }));
        }
    }, [sessionId, quiz, currentIndex, finished, totalXpEarned, QUIZ_SESSION_KEY, quizPrompt]);

    useEffect(() => {
        setAnswered(false);
        setSelectedAnswer(null);
        setCorrectAnswerIndex(null);
    }, [currentIndex]);

    // Save quiz result to backend when finished
    useEffect(() => {
        if (!finished || !token || !quiz.length) return;
        const allTags = [...new Set(quiz.flatMap(q => q.topic_tags ?? []))];
        fetch('http://127.0.0.1:8000/save-quiz-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({
                quiz_type: 'mcq',
                total_questions: quiz.length,
                correct_answers: correctCountRef.current,
                tags: allTags,
                prompt: quizPrompt || undefined,
            }),
        }).catch(err => console.error('Error saving quiz result:', err));
    }, [finished, token, quiz, quizPrompt]);

    async function addXpToUser(xp: number) {
        if (!token) return;
        try {
            const response = await fetch('http://127.0.0.1:8000/add-xp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ xp_amount: xp })
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

        // Track question result
        questionResultsRef.current.push({
            question: currentQ.question,
            options: currentQ.options,
            correct_answer: currentQ.correct_answer,
            userAnswer: letterFromIndex,
            isCorrect: isCorrect,
        });

        if (isCorrect) {
            correctCountRef.current += 1;
            const difficulty = currentQ.difficulty ?? "easy";
            const xpEarned = XP_PER_MCQ_DIFFICULTY[difficulty] ?? XP_PER_MCQ_DIFFICULTY.easy;
            setShowXpAnimation(true);
            setTotalXpEarned(prev => prev + xpEarned);
            addXpToUser(xpEarned);
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
        const timeTakenMs = Date.now() - startTimeRef.current;
        const timeTakenSecs = Math.floor(timeTakenMs / 1000);
        const minutes = Math.floor(timeTakenSecs / 60);
        const seconds = timeTakenSecs % 60;
        const timeString = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
        const accuracy = quiz.length > 0 ? Math.round((correctCountRef.current / quiz.length) * 100) : 0;

        return (
            <>
                <div className="quiz-page">
                    <Navbar />
                    {headerBar}
                    <div className="quiz-body">
                        {/* Summary Card */}
                        <div className="quiz-card quiz-complete">
                            <div className="quiz-complete__badge">✓</div>
                            <h1 className="quiz-complete__title">Quiz Complete!</h1>
                            
                            {/* Summary Stats */}
                            <div className="quiz-results__summary">
                                <div className="quiz-results__stat">
                                    <span className="quiz-results__stat-label">Score</span>
                                    <span className="quiz-results__stat-value">
                                        {correctCountRef.current}/{quiz.length}
                                    </span>
                                </div>
                                <div className="quiz-results__stat">
                                    <span className="quiz-results__stat-label">Accuracy</span>
                                    <span className="quiz-results__stat-value">{accuracy}%</span>
                                </div>
                                <div className="quiz-results__stat">
                                    <span className="quiz-results__stat-label">Time Taken</span>
                                    <span className="quiz-results__stat-value">{timeString}</span>
                                </div>
                            </div>

                            <div className="quiz-complete__xp-box">
                                <span>+{totalXpEarned} XP Earned!</span>
                            </div>
                            <br />
                            <button className="quiz-btn-primary" onClick={handleQuitQuiz}>
                                Create Another Quiz
                            </button>
                        </div>

                        {/* Per-Question Review */}
                        <div className="quiz-results__review">
                            <h2 className="quiz-results__review-title">Review</h2>
                            {questionResultsRef.current.map((result, i) => (
                                <div 
                                    key={i} 
                                    className={`quiz-results__question ${
                                        result.isCorrect ? 'quiz-results__question--correct' : 'quiz-results__question--incorrect'
                                    }`}
                                >
                                    <div className="quiz-results__question-header">
                                        <span className="quiz-results__question-number">
                                            Question {i + 1}
                                        </span>
                                        <span className={`quiz-results__question-badge ${
                                            result.isCorrect ? 'quiz-results__question-badge--correct' : 'quiz-results__question-badge--incorrect'
                                        }`}>
                                            {result.isCorrect ? '✓ Correct' : '✗ Incorrect'}
                                        </span>
                                    </div>
                                    <p className="quiz-results__question-text">{result.question}</p>
                                    <div className="quiz-results__options">
                                        {result.options.map((opt, optIdx) => {
                                            const letter = ["A", "B", "C", "D"][optIdx];
                                            let optClass = "quiz-results__option";
                                            
                                            if (letter === result.correct_answer) {
                                                optClass += " quiz-results__option--correct-answer";
                                            } else if (letter === result.userAnswer && !result.isCorrect) {
                                                optClass += " quiz-results__option--wrong-answer";
                                            }

                                            return (
                                                <div key={optIdx} className={optClass}>
                                                    <span className="quiz-results__option-letter">{letter}</span>
                                                    <span>{opt}</span>
                                                    {letter === result.correct_answer && (
                                                        <span className="quiz-results__option-label"> (Correct)</span>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
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
            <div className="quiz-page">
                <Navbar />
                {headerBar}

                <div className="quiz-body">
                    <div className="quiz-card">
                        <h2 className="quiz-card__title">{currentQ.title}</h2>

                        {/* Difficulty badge */}
                        {currentQ.difficulty && (
                            <div className={`quiz-difficulty-badge quiz-difficulty-${currentQ.difficulty}`}>
                                {currentQ.difficulty}
                            </div>
                        )}

                        <h3 className="quiz-card__question">{currentQ.question}</h3>

                        {/* Topic Tags */}
                        {currentQ.topic_tags && currentQ.topic_tags.length > 0 && (
                            <div className="quiz-meta-tags">
                                {currentQ.topic_tags.map((tag) => (
                                    <span key={tag} className="quiz-meta-tag">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        )}

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
                                        +{XP_PER_MCQ_DIFFICULTY[currentQ?.difficulty ?? 'easy'] ?? XP_PER_MCQ_DIFFICULTY.easy} XP
                                    </span>
                                )}
                            </div>
                        )}

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