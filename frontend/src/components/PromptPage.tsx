import '../css-files/PromptPage.css'  
import Navbar from "./Navbar";
import { useState } from "react";
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
    const { isAuthenticated } = useAuth();
    const [selectedModel, setSelectedModel] = useState<string>("");
    const [quizType, setQuizType] = useState<QuizType | null>(null);
    const [selectedLanguage, setSelectedLanguage] = useState<string>("");
    const [prompt, setPrompt] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

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

        // For coding quizzes, use placeholder data for now
        if (quizType === 'coding') {
            const placeholderQuestions = [
                {
                    question: `Write a function called 'reverseString' that takes a string as input and returns the reversed string.\n\nExample:\nInput: "hello"\nOutput: "olleh"`,
                    starter_code: getStarterCode(selectedLanguage, 'reverseString'),
                    test_cases: [
                        'reverseString("hello") === "olleh"',
                        'reverseString("world") === "dlrow"',
                        'reverseString("") === ""'
                    ],
                    hints: ['Think about iterating from the end', 'You can use built-in methods']
                },
                {
                    question: `Write a function called 'isPalindrome' that checks if a given string is a palindrome (reads the same forwards and backwards).\n\nExample:\nInput: "racecar"\nOutput: true`,
                    starter_code: getStarterCode(selectedLanguage, 'isPalindrome'),
                    test_cases: [
                        'isPalindrome("racecar") === true',
                        'isPalindrome("hello") === false',
                        'isPalindrome("level") === true'
                    ],
                    hints: ['Compare characters from both ends', 'Consider using your reverseString function']
                },
                {
                    question: `Write a function called 'findMax' that takes an array of numbers and returns the largest number.\n\nExample:\nInput: [1, 5, 3, 9, 2]\nOutput: 9`,
                    starter_code: getStarterCode(selectedLanguage, 'findMax'),
                    test_cases: [
                        'findMax([1, 5, 3, 9, 2]) === 9',
                        'findMax([-1, -5, -3]) === -1',
                        'findMax([42]) === 42'
                    ],
                    hints: ['Keep track of the maximum as you iterate', 'Consider edge cases like negative numbers']
                }
            ];
            
            navigate('/code-sandbox', { state: { quizData: placeholderQuestions, language: selectedLanguage } });
            return;
        }

        // For MCQ, fetch from backend as usual
        try {
            const response = await fetch('http://127.0.0.1:8000/prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: prompt,
                    quiz_type: quizType,
                    language: selectedLanguage
                })
            });

            const quiz = await response.json();
            console.log("Quiz from backend:", quiz);
            
            navigate('/quiz', { state: { quizData: quiz } });
        } catch (error) {
            console.error("Error submitting prompt:", error);
            setError("Failed to generate quiz. Please try again.");
        }
    }

    // Helper function to get language-specific starter code
    function getStarterCode(language: string, functionName: string): string {
        const templates: { [key: string]: { [key: string]: string } } = {
            javascript: {
                reverseString: `function reverseString(str) {\n    // Your code here\n    \n}`,
                isPalindrome: `function isPalindrome(str) {\n    // Your code here\n    \n}`,
                findMax: `function findMax(arr) {\n    // Your code here\n    \n}`
            },
            typescript: {
                reverseString: `function reverseString(str: string): string {\n    // Your code here\n    \n}`,
                isPalindrome: `function isPalindrome(str: string): boolean {\n    // Your code here\n    \n}`,
                findMax: `function findMax(arr: number[]): number {\n    // Your code here\n    \n}`
            },
            python: {
                reverseString: `def reverse_string(s: str) -> str:\n    # Your code here\n    pass`,
                isPalindrome: `def is_palindrome(s: str) -> bool:\n    # Your code here\n    pass`,
                findMax: `def find_max(arr: list) -> int:\n    # Your code here\n    pass`
            },
            java: {
                reverseString: `public static String reverseString(String str) {\n    // Your code here\n    return "";\n}`,
                isPalindrome: `public static boolean isPalindrome(String str) {\n    // Your code here\n    return false;\n}`,
                findMax: `public static int findMax(int[] arr) {\n    // Your code here\n    return 0;\n}`
            },
            'c++': {
                reverseString: `string reverseString(string str) {\n    // Your code here\n    return "";\n}`,
                isPalindrome: `bool isPalindrome(string str) {\n    // Your code here\n    return false;\n}`,
                findMax: `int findMax(vector<int> arr) {\n    // Your code here\n    return 0;\n}`
            },
            'c#': {
                reverseString: `public static string ReverseString(string str) {\n    // Your code here\n    return "";\n}`,
                isPalindrome: `public static bool IsPalindrome(string str) {\n    // Your code here\n    return false;\n}`,
                findMax: `public static int FindMax(int[] arr) {\n    // Your code here\n    return 0;\n}`
            },
            go: {
                reverseString: `func reverseString(str string) string {\n    // Your code here\n    return ""\n}`,
                isPalindrome: `func isPalindrome(str string) bool {\n    // Your code here\n    return false\n}`,
                findMax: `func findMax(arr []int) int {\n    // Your code here\n    return 0\n}`
            },
            rust: {
                reverseString: `fn reverse_string(s: &str) -> String {\n    // Your code here\n    String::new()\n}`,
                isPalindrome: `fn is_palindrome(s: &str) -> bool {\n    // Your code here\n    false\n}`,
                findMax: `fn find_max(arr: &[i32]) -> i32 {\n    // Your code here\n    0\n}`
            },
            ruby: {
                reverseString: `def reverse_string(str)\n  # Your code here\n  \nend`,
                isPalindrome: `def is_palindrome(str)\n  # Your code here\n  \nend`,
                findMax: `def find_max(arr)\n  # Your code here\n  \nend`
            },
            php: {
                reverseString: `function reverseString($str) {\n    // Your code here\n    return "";\n}`,
                isPalindrome: `function isPalindrome($str) {\n    // Your code here\n    return false;\n}`,
                findMax: `function findMax($arr) {\n    // Your code here\n    return 0;\n}`
            }
        };

        const langTemplates = templates[language.toLowerCase()];
        if (langTemplates && langTemplates[functionName]) {
            return langTemplates[functionName];
        }
        
        // Default fallback
        return `// Write your ${functionName} function here\n\n`;
    }

    return(
        <>
        <Navbar />
        <div className="prompt-page">
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
                    disabled={!quizType || !selectedModel || !prompt.trim() || (quizType === 'coding' && !selectedLanguage)}
                >
                    <span className="button-text">Generate Quiz</span>
                    <span className="button-arrow">→</span>
                </button>
            </div>
        </div>
        </>
    )
}

export default PromptPage;