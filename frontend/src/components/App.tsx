import PromptPage from './PromptPage'
import '../css-files/App.css'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "../utils/AuthContext";
import LandingPage from './LandingPage';
import AuthPage from './AuthPage';
import QuizPage from './QuizPage';
import UserPage from './UserPage';
import CodeSandboxPage from './CodeSandboxPage';

function App() {
  return(
    <>
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/prompt" element = {<PromptPage />} />
          <Route path="/register" element = {<AuthPage/>} />
          <Route path="/login" element = {<AuthPage/>} />
          <Route path="/profile" element = {<UserPage/>} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="/code-sandbox" element={<CodeSandboxPage />} />
        </Routes>
      </AuthProvider>
    </Router>
    </>
  )
}

export default App
