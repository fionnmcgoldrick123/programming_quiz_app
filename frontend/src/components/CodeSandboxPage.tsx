import { useLocation, useNavigate } from "react-router-dom";
import { useState, useMemo } from "react";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Navbar from "./Navbar";
import { useAuth } from "../utils/AuthContext";
import '../css-files/CodeSandboxPage.css';

interface CodeQuestion {
    question: string;
    starter_code: string;
    test_cases: string[];
    hints?: string[];
}

function CodeSandboxPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user } = useAuth();
    
    const questions: CodeQuestion[] = location.state?.quizData ?? [];
    const language: string = location.state?.language ?? "javascript";
    
    const [currentIndex, setCurrentIndex] = useState(0);
    const [code, setCode] = useState(questions[0]?.starter_code ?? "// Start coding here...");
    const [output, setOutput] = useState<string>("");
    const [finished, setFinished] = useState(false);

    const languageMap: { [key: string]: string } = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "java": "java",
        "c++": "cpp",
        "c#": "csharp",
        "go": "go",
        "rust": "rust",
    };

    if (!questions.length) {
        return (
            <div className="sandbox-container">
                <Navbar />
                <div className="sandbox-content">
                    <div className="sandbox-empty-state">
                        <p className="sandbox-empty-text">No coding challenge data found. Go back and generate a quiz first.</p>
                        <button 
                            className="sandbox-back-button"
                            onClick={() => navigate('/prompt')}
                        >
                            Back to Prompt
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const currentQ = questions[currentIndex];
    const progress = ((currentIndex) / questions.length) * 100;

    // Normalise the AI markdown so ReactMarkdown parses bold/italic/code properly.
    // - Ensure blank lines around headings and fenced code blocks.
    // - Trim each non-code line so JSX indentation doesn't create <pre> blocks.
    const questionMarkdown = useMemo(() => {
        let md = currentQ.question ?? "";
        // Ensure blank line before headings
        md = md.replace(/([^\n])\n(#{1,3} )/g, "$1\n\n$2");
        // Ensure blank line before fenced code blocks
        md = md.replace(/([^\n])\n```/g, "$1\n\n```");
        // Ensure blank line after closing fenced code blocks
        md = md.replace(/```\n([^\n])/g, "```\n\n$1");
        return md;
    }, [currentQ.question]);

    function handleNextQuestion() {
        if (currentIndex + 1 < questions.length) {
            setCurrentIndex(currentIndex + 1);
            setCode(questions[currentIndex + 1]?.starter_code ?? "");
            setOutput("");
        } else {
            setFinished(true);
        }
    }

    function handleRunCode() {
        // Placeholder for code execution
        setOutput("[Running] Code execution coming soon...\n\nYour code:\n" + code);
    }

    function handleSubmit() {
        // Placeholder for submission logic
        setOutput("[Success] Submitted! Moving to next question...");
        setTimeout(() => {
            handleNextQuestion();
        }, 1500);
    }

    if (finished) {
        return (
            <div className="sandbox-container">
                <Navbar />
                <div className="sandbox-content">
                    <div className="sandbox-complete">
                        <div className="sandbox-complete-icon"></div>
                        <h2 className="sandbox-complete-title">Challenge Complete!</h2>
                        <p className="sandbox-complete-text">
                            Great job! You've completed all the coding challenges.
                        </p>
                        <button 
                            className="sandbox-back-button"
                            onClick={() => navigate('/prompt')}
                        >
                            Start New Challenge
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="sandbox-container">
            <Navbar />
            <div className="sandbox-main">
                {/* Left Panel - Editor */}
                <div className="sandbox-editor-panel">
                    <div className="sandbox-editor-header">
                        <span className="sandbox-language-badge">{language.toUpperCase()}</span>
                    </div>
                    
                    <div className="sandbox-editor-wrapper">
                        <Editor
                            height="60vh"
                            language={languageMap[language.toLowerCase()] || "javascript"}
                            value={code}
                            onChange={(value) => setCode(value ?? "")}
                            theme="vs-dark"
                            options={{
                                fontSize: 14,
                                fontFamily: "'Fira Code', monospace",
                                minimap: { enabled: false },
                                scrollBeyondLastLine: false,
                                padding: { top: 16, bottom: 16 },
                                lineNumbers: "on",
                                roundedSelection: true,
                                automaticLayout: true,
                            }}
                        />
                    </div>

                    <div className="sandbox-output-section">
                        <h3 className="sandbox-output-title">Output</h3>
                        <div className="sandbox-output-box">
                            <pre>{output || "Run your code to see output..."}</pre>
                        </div>
                    </div>

                    <div className="sandbox-button-group">
                        <button 
                            className="sandbox-run-button"
                            onClick={handleRunCode}
                        >
                            Run Code
                        </button>
                        <button 
                            className="sandbox-submit-button"
                            onClick={handleSubmit}
                        >
                            Submit Solution
                        </button>
                    </div>
                </div>

                {/* Right Panel - Question */}
                <div className="sandbox-question-panel">
                    {/* XP Status Bar */}
                    {user && (
                        <div className="sandbox-xp-bar">
                            <span className="sandbox-xp-level">LVL {user.level}</span>
                            <div className="sandbox-xp-track">
                                <div
                                    className="sandbox-xp-fill"
                                    style={{ width: `${(user.exp / (user.xp_required ?? 100)) * 100}%` }}
                                />
                            </div>
                            <span className="sandbox-xp-text">{user.exp}/{user.xp_required ?? 100} XP</span>
                        </div>
                    )}

                    <div className="sandbox-progress-section">
                        <p className="sandbox-progress-text">
                            Question {currentIndex + 1} of {questions.length}
                        </p>
                        <div className="sandbox-progress-bar">
                            <div 
                                className="sandbox-progress-fill"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>

                    <div className="sandbox-question-content">
                        <h2 className="sandbox-question-title">Challenge</h2>
                        <div className="sandbox-markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {questionMarkdown}
                            </ReactMarkdown>
                        </div>

                        {currentQ.test_cases && currentQ.test_cases.length > 0 && (
                            <div className="sandbox-test-cases">
                                <h3 className="sandbox-section-title">Test Cases</h3>
                                {currentQ.test_cases.map((testCase, idx) => (
                                    <div key={idx} className="sandbox-test-case">
                                        <code>{testCase}</code>
                                    </div>
                                ))}
                            </div>
                        )}

                        {currentQ.hints && currentQ.hints.length > 0 && (
                            <div className="sandbox-hints">
                                <h3 className="sandbox-section-title">Hints</h3>
                                <ul>
                                    {currentQ.hints.map((hint, idx) => (
                                        <li key={idx}>{hint}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default CodeSandboxPage;
