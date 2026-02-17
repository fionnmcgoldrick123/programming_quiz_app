import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../utils/AuthContext";
import PasswordStrengthBar from "react-password-strength-bar";
import Navbar from "./Navbar";
import '../css-files/AuthPage.css';

function AuthPage() {
    const navigate = useNavigate();
    const { login } = useAuth();
    
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [firstName, setFirstName] = useState("");
    const [secondName, setSecondName] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const passwordRule = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{7,}$/;
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$/;

    async function handleLoginSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setError("");

        if (!email || !password) {
            setError("Please fill in all fields");
            return;
        }

        setIsLoading(true);
        
        const result = await login(email, password);
        
        if (result.success) {
            navigate("/");
        } else {
            setError(result.error || "Login failed");
        }
        
        setIsLoading(false);
    }

    async function handleRegisterSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setError("");

        if (!firstName || !secondName || !password || !email) {
            setError("All fields are required!");
            return;
        }

        if (!passwordRule.test(password)) {
            setError("Password must contain uppercase, lowercase, number, special character, and be at least 7 characters long.");
            return;
        }

        if (!emailRegex.test(email)) {
            setError("Invalid email format");
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch("http://127.0.0.1:8000/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    first_name: firstName,
                    second_name: secondName,
                    email: email,
                    password: password
                })
            });

            if (response.ok) {
                // Clear form
                setFirstName("");
                setSecondName("");
                setPassword("");
                setEmail("");
                // Switch to login
                setIsLogin(true);
                setError("Registration successful! Please login.");
            } else {
                const data = await response.json();
                setError(data.detail || "Registration failed");
            }
        } catch (err) {
            setError("An error occurred during registration");
        }

        setIsLoading(false);
    }

    const toggleMode = () => {
        setIsLogin(!isLogin);
        setError("");
        setEmail("");
        setPassword("");
        setFirstName("");
        setSecondName("");
    };

    return (
        <>
            <Navbar />
            <div className="auth-page">
                {/* Decorative floating elements */}
                <div className="floating-shapes">
                    <div className="shape shape-1"></div>
                    <div className="shape shape-2"></div>
                    <div className="shape shape-3"></div>
                    <div className="shape shape-4"></div>
                    <div className="shape shape-5"></div>
                    <div className="shape shape-6"></div>
                </div>

                {/* Animated gradient orbs */}
                <div className="gradient-orb orb-1"></div>
                <div className="gradient-orb orb-2"></div>
                <div className="gradient-orb orb-3"></div>

                <div className="auth-container">
                    <div className={`auth-card ${!isLogin ? 'register-mode' : ''}`}>
                        <div className="auth-header">
                            <h1>{isLogin ? 'Welcome Back' : 'Create Account'}</h1>
                            <p className="auth-subtitle">
                                {isLogin 
                                    ? 'Sign in to continue your coding journey' 
                                    : 'Join us and start learning today'}
                            </p>
                        </div>

                        {error && (
                            <div className={`error-message ${error.includes('successful') ? 'success-message' : ''}`}>
                                {error}
                            </div>
                        )}

                        {isLogin ? (
                            <form onSubmit={handleLoginSubmit} className="auth-form">
                                <div className="input-group">
                                    <label className="label">Email Address</label>
                                    <input 
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="your.email@example.com"
                                        disabled={isLoading}
                                    />
                                </div>

                                <div className="input-group">
                                    <label className="label">Password</label>
                                    <input 
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter your password"
                                        disabled={isLoading}
                                    />
                                </div>

                                <button type="submit" className="submit-button" disabled={isLoading}>
                                    {isLoading ? 'Logging in...' : 'Sign In'}
                                </button>
                            </form>
                        ) : (
                            <form onSubmit={handleRegisterSubmit} className="auth-form">
                                <div className="input-row">
                                    <div className="input-group">
                                        <label className="label">First Name</label>
                                        <input 
                                            type="text"
                                            value={firstName}
                                            onChange={(e) => setFirstName(e.target.value)}
                                            placeholder="John"
                                            disabled={isLoading}
                                        />
                                    </div>

                                    <div className="input-group">
                                        <label className="label">Last Name</label>
                                        <input 
                                            type="text"
                                            value={secondName}
                                            onChange={(e) => setSecondName(e.target.value)}
                                            placeholder="Doe"
                                            disabled={isLoading}
                                        />
                                    </div>
                                </div>

                                <div className="input-group">
                                    <label className="label">Email Address</label>
                                    <input 
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="your.email@example.com"
                                        disabled={isLoading}
                                    />
                                </div>

                                <div className="input-group">
                                    <label className="label">Password</label>
                                    <input 
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Create a strong password"
                                        disabled={isLoading}
                                    />
                                    <PasswordStrengthBar password={password} />
                                </div>

                                <button type="submit" className="submit-button" disabled={isLoading}>
                                    {isLoading ? 'Creating account...' : 'Create Account'}
                                </button>
                            </form>
                        )}

                        <div className="auth-switch">
                            <p>
                                {isLogin ? "Don't have an account?" : "Already have an account?"}
                                <span className="switch-link" onClick={toggleMode}>
                                    {isLogin ? ' Sign Up' : ' Sign In'}
                                </span>
                            </p>
                        </div>

                        {/* Decorative code snippets */}
                        <div className="code-decoration code-left">
                            <pre>{`function learn() {
  return success;
}`}</pre>
                        </div>
                        <div className="code-decoration code-right">
                            <pre>{`const skills = 
  knowledge++;`}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default AuthPage;
