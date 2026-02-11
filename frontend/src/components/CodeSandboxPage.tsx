import { useLocation, useNavigate } from "react-router-dom";
import { useState, useMemo, useEffect } from "react";
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

const codeSessionKey = (userId: number) => `codeSandboxSession_${userId}`;

function CodeSandboxPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user } = useAuth();

    const CODE_SESSION_KEY = user ? codeSessionKey(user.id) : null;

    function getDefaultStub(lang: string): string {
        const lower = lang.toLowerCase();
        if (lower === "python") return "# Write your solution here\n\n";
        if (lower === "java") return "// Write your solution here\n\npublic class Solution {\n    \n}\n";
        if (lower === "c++" || lower === "cpp") return "// Write your solution here\n#include <iostream>\nusing namespace std;\n\n";
        if (lower === "c#" || lower === "csharp") return "// Write your solution here\nusing System;\n\n";
        if (lower === "go") return "package main\n\n// Write your solution here\n\n";
        if (lower === "rust") return "// Write your solution here\n\nfn main() {\n    \n}\n";
        return "// Write your solution here\n\n";
    }

    // Parse saved session once for use in state initializers
    const savedSession = (() => {
        try {
            if (!CODE_SESSION_KEY) return null;
            const raw = sessionStorage.getItem(CODE_SESSION_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) { return null; }
    })();

    const isFreshQuiz = Boolean(
        location.state?.quizData?.length &&
        (!savedSession || savedSession.sessionId !== location.state.sessionId)
    );

    const [questions] = useState<CodeQuestion[]>(() => {
        if (isFreshQuiz) return location.state.quizData;
        return savedSession?.questions ?? location.state?.quizData ?? [];
    });

    const [language] = useState<string>(() => {
        if (isFreshQuiz) return location.state?.language ?? "javascript";
        return savedSession?.language ?? location.state?.language ?? "javascript";
    });

    const [sessionId] = useState<number>(() => {
        if (isFreshQuiz) return location.state.sessionId ?? Date.now();
        return savedSession?.sessionId ?? location.state?.sessionId ?? Date.now();
    });

    const [currentIndex, setCurrentIndex] = useState<number>(() => {
        if (isFreshQuiz) return 0;
        return savedSession?.currentIndex ?? 0;
    });

    const [code, setCode] = useState<string>(() => {
        if (isFreshQuiz) {
            return location.state.quizData[0]?.starter_code || getDefaultStub(location.state?.language ?? "javascript");
        }
        if (savedSession?.code != null) return savedSession.code;
        const qs = savedSession?.questions ?? [];
        const idx = savedSession?.currentIndex ?? 0;
        const lang = savedSession?.language ?? "javascript";
        return qs[idx]?.starter_code || getDefaultStub(lang);
    });

    const [output, setOutput] = useState<string>("");
    const [isRunning, setIsRunning] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const [finished, setFinished] = useState<boolean>(() => {
        if (isFreshQuiz) return false;
        return savedSession?.finished ?? false;
    });

    // Persist session to sessionStorage whenever progress changes
    useEffect(() => {
        if (questions.length && CODE_SESSION_KEY) {
            sessionStorage.setItem(CODE_SESSION_KEY, JSON.stringify({
                sessionId,
                questions,
                language,
                currentIndex,
                code,
                finished,
            }));
        }
    }, [sessionId, questions, language, currentIndex, code, finished, CODE_SESSION_KEY]);

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
                            onClick={() => { if (CODE_SESSION_KEY) sessionStorage.removeItem(CODE_SESSION_KEY); navigate('/prompt'); }}
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
            setCode(questions[currentIndex + 1]?.starter_code || getDefaultStub(language));
            setOutput("");
        } else {
            setFinished(true);
        }
    }

    async function handleRunCode() {
        setIsRunning(true);
        setOutput("Running code...");
        
        try {
            const response = await fetch("http://127.0.0.1:8000/run-code", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    code: code,
                    language: language
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                setOutput(`✓ Execution successful\n\nOutput:\n${result.output || '(no output)'}`);
            } else {
                setOutput(`✗ Execution failed\n\nError:\n${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            setOutput(`✗ Failed to execute code\n\nError: ${error}`);
        } finally {
            setIsRunning(false);
        }
    }

    async function handleSubmit() {
        setIsSubmitting(true);
        setOutput("Running tests...");
        
        try {
            const response = await fetch("http://127.0.0.1:8000/submit-code", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    code: code,
                    language: language,
                    test_cases: currentQ.test_cases
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                let outputText = "✓ All tests passed!\n\n";
                result.test_results.forEach((test: any) => {
                    outputText += `Test ${test.test_number}: ✓ PASSED\n`;
                    outputText += `  Input: ${JSON.stringify(test.input)}\n`;
                    outputText += `  Expected: ${JSON.stringify(test.expected)}\n`;
                    outputText += `  Got: ${JSON.stringify(test.actual)}\n\n`;
                });
                setOutput(outputText);
                
                // Move to next question after a short delay
                setTimeout(() => {
                    handleNextQuestion();
                }, 2000);
            } else {
                let outputText = "✗ Some tests failed\n\n";
                result.test_results.forEach((test: any) => {
                    const status = test.passed ? "✓ PASSED" : "✗ FAILED";
                    outputText += `Test ${test.test_number}: ${status}\n`;
                    outputText += `  Input: ${JSON.stringify(test.input)}\n`;
                    outputText += `  Expected: ${JSON.stringify(test.expected)}\n`;
                    outputText += `  Got: ${JSON.stringify(test.actual)}\n`;
                    if (test.error) {
                        outputText += `  Error: ${test.error}\n`;
                    }
                    outputText += `\n`;
                });
                setOutput(outputText);
            }
        } catch (error) {
            setOutput(`✗ Failed to submit code\n\nError: ${error}`);
        } finally {
            setIsSubmitting(false);
        }
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
                            onClick={() => { if (CODE_SESSION_KEY) sessionStorage.removeItem(CODE_SESSION_KEY); navigate('/prompt'); }}
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
                            disabled={isRunning || isSubmitting}
                        >
                            {isRunning ? "Running..." : "Run Code"}
                        </button>
                        <button 
                            className="sandbox-submit-button"
                            onClick={handleSubmit}
                            disabled={isRunning || isSubmitting}
                        >
                            {isSubmitting ? "Submitting..." : "Submit Solution"}
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
