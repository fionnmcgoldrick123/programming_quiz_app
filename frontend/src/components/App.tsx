import PromptPage from './PromptPage'
import '../css-files/App.css'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "../utils/AuthContext";
import LandingPage from './LandingPage';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import QuizPage from './QuizPage';
import UserPage from './UserPage';
import CodeSandboxPage from './CodeSandboxPage';
import AboutPage from './AboutPage';
import StatsPage from './StatsPage';

function App() {
  return(
    <>
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/prompt" element = {<PromptPage />} />
          <Route path="/login" element = {<LoginPage />} />
          <Route path="/register" element = {<RegisterPage />} />
          <Route path="/profile" element = {<UserPage/>} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="/code-sandbox" element={<CodeSandboxPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/stats" element={<StatsPage />} />
        </Routes>
      </AuthProvider>
    </Router>
    </>
  )
}

export default App
