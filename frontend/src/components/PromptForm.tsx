import '../css-files/PromptForm.css'
import { useState } from 'react'
// import ClipLoader from "react-spinners/ClipLoader";
import { useNavigate } from "react-router-dom";

type QuizType = "mcq" | "coding";

interface PromptFormProps {
    selectedModel: string;
    quizType: QuizType;
    selectedLanguage: string;
}

function PromptForm({ selectedModel, quizType, selectedLanguage }: PromptFormProps){

    const [prompt, setPrompt] = useState("")
    const [error, setError] = useState("")
    const navigate = useNavigate()
    // const [loading, setLoading] = useState(false);

    async function handleSubmit(){
        setError("");

        if (!selectedModel) {
            setError("Please select a model before submitting.");
            return;
        }

        if (!prompt.trim()) {
            setError("Please enter a prompt.");
            return;
        }

        if (quizType === 'coding' && !selectedLanguage) {
            setError("Please select a programming language for the coding sandbox.");
            return;
        }

        const currentPrompt = prompt;
        setPrompt("")
        // setLoading(true);

        let response;

        try{
            response = await fetch('http://127.0.0.1:8000/prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    prompt: currentPrompt,
                    quiz_type: quizType,
                    language: selectedLanguage
                })
            })
        }
        catch(error){
            console.error("Error submitting prompt:", error)
            setError("Failed to submit prompt. Please try again.");
            return;
        }

        
        const quiz = await response.json();
        console.log("Quiz from backend:", quiz);
        
        if (quizType === 'coding') {
            navigate('/code-sandbox', { state: { quizData: quiz, language: selectedLanguage, sessionId: Date.now() } });
        } else {
            navigate('/quiz', { state: { quizData: quiz, sessionId: Date.now() } });
        }

         // setLoading(false);
        
    }

    return(
        <>
            <div className='prompt-form'>
                {error && <div className='error-message'>{error}</div>}
                <textarea className='prompt-text-area'
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)} 
                placeholder={quizType === 'coding' 
                    ? 'Describe the coding challenges you want... (e.g., "Create 3 array manipulation problems")'
                    : 'Enter your prompt here...'
                }
                >

                </textarea>

                <br></br>

                <button 
                    onClick={handleSubmit} 
                    className='submit-button'
                    disabled={!selectedModel || (quizType === 'coding' && !selectedLanguage)}
                    title={!selectedModel ? "Please select a model first" : (quizType === 'coding' && !selectedLanguage) ? "Please select a language" : ""}
                >
                    {quizType === 'coding' ? 'Generate Coding Challenge' : 'Submit'}
                </button>
            </div>
        </>
    )
}

export default PromptForm