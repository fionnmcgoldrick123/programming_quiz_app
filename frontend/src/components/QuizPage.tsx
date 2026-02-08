import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import Navbar from "./Navbar";
import { useAuth } from "../utils/AuthContext";

const XP_PER_CORRECT = 10;

const quizStyles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#1a1a1a',
        padding: '0',
    },
    content: {
        maxWidth: '800px',
        margin: '0 auto',
        padding: '2rem',
    },
    card: {
        backgroundColor: '#2d2d2d',
        borderRadius: '16px',
        padding: '2rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        border: '1px solid #3d3d3d',
    },
    progressBar: {
        backgroundColor: '#3d3d3d',
        borderRadius: '8px',
        height: '8px',
        marginBottom: '1.5rem',
        overflow: 'hidden' as const,
    },
    progressFill: (progress: number) => ({
        backgroundColor: '#ff9500',
        height: '100%',
        width: `${progress}%`,
        transition: 'width 0.3s ease',
        borderRadius: '8px',
    }),
    progressText: {
        color: '#808080',
        fontSize: '0.9rem',
        marginBottom: '0.5rem',
        fontFamily: "'Fira Code', monospace",
    },
    title: {
        color: '#ff9500',
        fontSize: '1.5rem',
        marginBottom: '1rem',
        fontFamily: "'Fira Code', monospace",
        fontWeight: 600,
    },
    question: {
        color: '#ffffff',
        fontSize: '1.25rem',
        marginBottom: '2rem',
        fontFamily: "'Fira Code', monospace",
        lineHeight: 1.6,
    },
    optionsContainer: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '1rem',
    },
    optionButton: {
        backgroundColor: '#3d3d3d',
        color: '#e0e0e0',
        border: '2px solid #4d4d4d',
        borderRadius: '12px',
        padding: '1rem 1.5rem',
        fontSize: '1rem',
        fontFamily: "'Fira Code', monospace",
        cursor: 'pointer',
        textAlign: 'left' as const,
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
    },
    optionLetter: {
        backgroundColor: '#ff9500',
        color: '#1a1a1a',
        width: '32px',
        height: '32px',
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        flexShrink: 0,
    },
    emptyState: {
        textAlign: 'center' as const,
        padding: '4rem 2rem',
    },
    emptyText: {
        color: '#808080',
        fontSize: '1.1rem',
        marginBottom: '1.5rem',
        fontFamily: "'Fira Code', monospace",
    },
    backButton: {
        backgroundColor: '#ff9500',
        color: '#1a1a1a',
        border: 'none',
        borderRadius: '8px',
        padding: '0.75rem 2rem',
        fontSize: '1rem',
        fontFamily: "'Fira Code', monospace",
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
    },
    completeContainer: {
        textAlign: 'center' as const,
        padding: '3rem',
    },
    completeEmoji: {
        fontSize: '4rem',
        marginBottom: '1rem',
    },
    completeTitle: {
        color: '#ff9500',
        fontSize: '2rem',
        marginBottom: '1rem',
        fontFamily: "'Fira Code', monospace",
        fontWeight: 700,
    },
    completeText: {
        color: '#e0e0e0',
        fontSize: '1.1rem',
        marginBottom: '2rem',
        fontFamily: "'Fira Code', monospace",
    },
};

function QuizPage() {
    const location = useLocation();
    const quiz = location.state?.quizData ?? [];
    const { token, updateUser, user } = useAuth();

    const navigate = useNavigate();

    const [currentIndex, setCurrentIndex] = useState(0);
    const [finished, setFinished] = useState(false);
    const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
    const [showXpAnimation, setShowXpAnimation] = useState(false);
    const [totalXpEarned, setTotalXpEarned] = useState(0);
    const [levelUpInfo, setLevelUpInfo] = useState<{ show: boolean; newLevel: number | null }>({ show: false, newLevel: null });

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
                // Update user in auth context (strip extra fields)
                const { xp_gained, leveled_up, new_level, ...updatedUser } = data;
                updateUser(updatedUser);

                if (leveled_up && new_level) {
                    setLevelUpInfo({ show: true, newLevel: new_level });
                    // Auto-hide after 3 seconds
                    setTimeout(() => setLevelUpInfo({ show: false, newLevel: null }), 3000);
                }
            }
        } catch (error) {
            console.error("Error adding XP:", error);
        }
    }

    if (!quiz.length) {
        return (
            <div style={quizStyles.container}>
                <Navbar />
                <div style={quizStyles.content}>
                    <div style={{ ...quizStyles.card, ...quizStyles.emptyState }}>
                        <p style={quizStyles.emptyText}>No quiz data found. Go back and generate a quiz first.</p>
                        <button 
                            style={quizStyles.backButton} 
                            onClick={() => navigate('/prompt')}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.transform = 'translateY(-2px)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 149, 0, 0.4)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                        >
                            Back to Prompt
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const currentQ = quiz[currentIndex];
    const progress = ((currentIndex) / quiz.length) * 100;

    function handleAnswer(option: string, index: number) {
        console.log("Selected option:", option);

        const letterFromIndex = ["A", "B", "C", "D"][index];
        const isCorrect = letterFromIndex === currentQ.correct_answer;

        if (!isCorrect) {
            setFeedbackMessage("Incorrect! Try again.");
            setTimeout(() => setFeedbackMessage(null), 1500);
            return;
        }

        // Show XP animation
        setShowXpAnimation(true);
        setTotalXpEarned(prev => prev + XP_PER_CORRECT);
        
        // Add XP to user account
        addXpToUser();

        setFeedbackMessage("Correct!");
        setTimeout(() => {
            setFeedbackMessage(null);
            setShowXpAnimation(false);
            if (currentIndex + 1 < quiz.length) {
                setCurrentIndex(currentIndex + 1);
            } else {
                setFinished(true);
            }
        }, 800);
    }

    if (finished) {
        return (
            <div style={quizStyles.container}>
                <Navbar />
                <div style={quizStyles.content}>
                    <div style={{ ...quizStyles.card, ...quizStyles.completeContainer }}>
                        <div style={{
                            width: '80px',
                            height: '80px',
                            margin: '0 auto 24px',
                            background: 'linear-gradient(135deg, #ff9500 0%, #ff7700 100%)',
                            borderRadius: '50%',
                            position: 'relative' as const,
                            boxShadow: '0 8px 32px rgba(255, 149, 0, 0.4)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <span style={{ 
                                color: '#1a1a1a', 
                                fontSize: '2rem', 
                                fontWeight: 700 
                            }}>✓</span>
                        </div>
                        <h1 style={quizStyles.completeTitle}>Quiz Complete!</h1>
                        <p style={quizStyles.completeText}>Great job! You've completed all {quiz.length} questions.</p>
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(255, 149, 0, 0.15) 0%, rgba(255, 119, 0, 0.1) 100%)',
                            border: '1px solid rgba(255, 149, 0, 0.3)',
                            borderRadius: '12px',
                            padding: '16px 24px',
                            marginBottom: '24px',
                        }}>
                            <p style={{
                                color: '#ff9500',
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                margin: 0,
                                fontFamily: "'Fira Code', monospace",
                            }}>+{totalXpEarned} XP Earned!</p>
                        </div>
                        <button 
                            style={quizStyles.backButton} 
                            onClick={() => navigate('/prompt')}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.transform = 'translateY(-2px)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 149, 0, 0.4)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                        >
                            Create Another Quiz
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!currentQ) {
        return <p style={{ color: '#808080', textAlign: 'center', padding: '2rem' }}>No quiz data found</p>;
    }

    return (
        <div style={quizStyles.container}>
            <Navbar />
            <div style={quizStyles.content}>
                <div style={quizStyles.card}>
                    {/* XP Status Bar */}
                    {user && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            padding: '10px 14px',
                            marginBottom: '1.25rem',
                            backgroundColor: '#252525',
                            borderRadius: '10px',
                            border: '1px solid #3d3d3d',
                        }}>
                            <span style={{
                                color: '#ff9500',
                                fontWeight: 700,
                                fontFamily: "'Fira Code', monospace",
                                fontSize: '0.85rem',
                                whiteSpace: 'nowrap' as const,
                            }}>LVL {user.level}</span>
                            <div style={{
                                flex: 1,
                                backgroundColor: '#3d3d3d',
                                borderRadius: '6px',
                                height: '10px',
                                overflow: 'hidden',
                            }}>
                                <div style={{
                                    width: `${(user.exp / (user.xp_required ?? 100)) * 100}%`,
                                    height: '100%',
                                    background: 'linear-gradient(90deg, #ff9500, #ffb347)',
                                    borderRadius: '6px',
                                    transition: 'width 0.4s ease',
                                }} />
                            </div>
                            <span style={{
                                color: '#808080',
                                fontFamily: "'Fira Code', monospace",
                                fontSize: '0.8rem',
                                whiteSpace: 'nowrap' as const,
                            }}>{user.exp}/{user.xp_required ?? 100} XP</span>
                        </div>
                    )}

                    <p style={quizStyles.progressText}>Question {currentIndex + 1} of {quiz.length}</p>
                    <div style={quizStyles.progressBar}>
                        <div style={quizStyles.progressFill(progress)}></div>
                    </div>

                    <h2 style={quizStyles.title}>{currentQ.title}</h2>
                    <h3 style={quizStyles.question}>{currentQ.question}</h3>

                    {/* Level Up Banner */}
                    {levelUpInfo.show && (
                        <div style={{
                            padding: '1rem 1.5rem',
                            borderRadius: '12px',
                            marginBottom: '1rem',
                            background: 'linear-gradient(135deg, rgba(255, 215, 0, 0.25) 0%, rgba(255, 149, 0, 0.2) 100%)',
                            border: '2px solid rgba(255, 215, 0, 0.6)',
                            textAlign: 'center' as const,
                            animation: 'levelUpPulse 0.6s ease-out',
                        }}>
                            <span style={{
                                color: '#ffd700',
                                fontSize: '1.2rem',
                                fontWeight: 700,
                                fontFamily: "'Fira Code', monospace",
                            }}>
                                Level Up! You're now Level {levelUpInfo.newLevel}!
                            </span>
                        </div>
                    )}

                    {feedbackMessage && (
                        <div style={{
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            marginBottom: '1rem',
                            backgroundColor: feedbackMessage.includes('Correct') ? 'rgba(76, 175, 80, 0.2)' : 'rgba(244, 67, 54, 0.2)',
                            color: feedbackMessage.includes('Correct') ? '#4caf50' : '#f44336',
                            fontFamily: "'Fira Code', monospace",
                            textAlign: 'center' as const,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '12px',
                        }}>
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

                    <style>{`
                        @keyframes xpFloat {
                            0% {
                                opacity: 0;
                                transform: translateY(10px) scale(0.8);
                            }
                            50% {
                                opacity: 1;
                                transform: translateY(-5px) scale(1.1);
                            }
                            100% {
                                opacity: 1;
                                transform: translateY(0) scale(1);
                            }
                        }
                        @keyframes levelUpPulse {
                            0% {
                                opacity: 0;
                                transform: scale(0.8);
                            }
                            50% {
                                transform: scale(1.05);
                            }
                            100% {
                                opacity: 1;
                                transform: scale(1);
                            }
                        }
                    `}</style>

                    <div style={quizStyles.optionsContainer}>
                        {currentQ.options.map((opt: string, i: number) => (
                            <button 
                                key={i}
                                style={quizStyles.optionButton}
                                onClick={() => handleAnswer(opt, i)}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = '#ff9500';
                                    e.currentTarget.style.backgroundColor = '#454545';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = '#4d4d4d';
                                    e.currentTarget.style.backgroundColor = '#3d3d3d';
                                }}
                            >
                                <span style={quizStyles.optionLetter}>
                                    {["A", "B", "C", "D"][i]}
                                </span>
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default QuizPage;
