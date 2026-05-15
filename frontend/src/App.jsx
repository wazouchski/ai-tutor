import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

// Simple markdown renderer
function renderMarkdown(text) {
  if (!text) return null
  let html = text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*)\*/gim, '<em>$1</em>')
    .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
    .replace(/`(.*?)`/gim, '<code>$1</code>')
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/^\- (.*$)/gim, '<ul><li>$1</li></ul>')
    .replace(/^\d+\. (.*$)/gim, '<ol><li>$1</li></ol>')
    .replace(/\n/gim, '<br>')
  return { __html: html }
}

function MarkdownContent({ content }) {
  return <div className="markdown-content" dangerouslySetInnerHTML={renderMarkdown(content)} />
}

// Login Component
function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim()) return

    setLoading(true)
    try {
      const res = await axios.post(`${API_BASE}/login`, { username: username.trim() })
      onLogin(res.data)
    } catch (err) {
      alert('Error logging in: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>🤖 Jarvis</h1>
        <p className="subtitle">Your Personal AI Tutor</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter your name"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Loading...' : 'Start Learning'}
          </button>
        </form>
      </div>
    </div>
  )
}

// Topic Selection Component
function TopicSelection({ user, onStartTopic }) {
  const [topic, setTopic] = useState('')
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return

    setLoading(true)
    try {
      await axios.post(`${API_BASE}/start-onboarding`, {
        username: user.username,
        topic: topic.trim()
      })
      onStartTopic(topic.trim(), goal.trim())
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="topic-selection">
      <h2>What would you like to learn today?</h2>
      <form className="topic-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="e.g., IT Security, Python, AI Automation, Knitting..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          autoFocus
        />
        <textarea
          placeholder="What's your goal? (e.g., 'Pass Security+ certification', 'Build my first AI app', 'Learn the basics')"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Starting...' : 'Begin Assessment'}
        </button>
      </form>
    </div>
  )
}

// Onboarding Component
function Onboarding({ user, topic, onComplete }) {
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [showResult, setShowResult] = useState(false)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadQuestions()
  }, [])

  const loadQuestions = async () => {
    try {
      const res = await axios.post(`${API_BASE}/start-onboarding`, {
        username: user.username,
        topic
      })
      setQuestions(res.data.questions)
    } catch (err) {
      alert('Error loading questions: ' + err.message)
    }
  }

  const handleAnswer = async (option) => {
    if (showResult) return
    setSelectedAnswer(option)
    setShowResult(true)

    const question = questions[currentIndex]
    try {
      await axios.post(`${API_BASE}/onboarding/answer`, {
        username: user.username,
        topic,
        question_id: question.id,
        answer: option,
        question_text: question.question
      })
    } catch (err) {
      console.error('Error saving answer:', err)
    }

    setAnswers(prev => ({ ...prev, [question.id]: option }))

    // Auto advance after delay
    setTimeout(() => {
      if (currentIndex < questions.length - 1) {
        setCurrentIndex(prev => prev + 1)
        setSelectedAnswer(null)
        setShowResult(false)
      } else {
        completeOnboarding()
      }
    }, 1500)
  }

  const completeOnboarding = async () => {
    setLoading(true)
    try {
      const res = await axios.post(`${API_BASE}/onboarding/complete`, {
        username: user.username,
        topic
      })
      onComplete(res.data)
    } catch (err) {
      alert('Error completing assessment: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (questions.length === 0) {
    return <div className="loading"><div className="loading-spinner"></div>Loading questions...</div>
  }

  const question = questions[currentIndex]
  const progress = ((currentIndex) / questions.length) * 100

  return (
    <div className="onboarding-container">
      <div className="onboarding-header">
        <h2>Knowledge Assessment</h2>
        <p>Question {currentIndex + 1} of {questions.length}</p>
      </div>
      <div className="progress-bar">
        <div className="progress" style={{ width: `${progress}%` }}></div>
      </div>
      <div className="question-card">
        <h3>{question.question}</h3>
        <div className="options-list">
          {Object.entries(question.options).map(([key, value]) => {
            let className = 'option-btn'
            if (showResult) {
              if (key === question.correct_answer) {
                className += ' correct'
              } else if (key === selectedAnswer) {
                className += ' incorrect'
              }
            } else if (selectedAnswer === key) {
              className += ' selected'
            }
            return (
              <button
                key={key}
                className={className}
                onClick={() => handleAnswer(key)}
                disabled={showResult}
              >
                <strong>{key}.</strong> {value}
              </button>
            )
          })}
        </div>
      </div>
      {loading && (
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Analyzing results...</p>
        </div>
      )}
    </div>
  )
}

// Results Component
function Results({ assessment, onContinue }) {
  return (
    <div className="results-screen">
      <h2>Assessment Complete!</h2>
      <p>Here's what we found:</p>

      <div className="accuracy-display">
        {Math.round(assessment.accuracy * 100)}%
      </div>
      <p>{assessment.correct} of {assessment.total_questions} correct</p>

      <div className="areas-grid">
        {assessment.strong_areas.length > 0 && (
          <div className="area-card strong">
            <h4>✓ Strong Areas</h4>
            {assessment.strong_areas.map(area => (
              <p key={area}>{area}</p>
            ))}
          </div>
        )}
        {assessment.weak_areas.length > 0 && (
          <div className="area-card weak">
            <h4>📚 Focus Areas</h4>
            {assessment.weak_areas.map(area => (
              <p key={area}>{area}</p>
            ))}
          </div>
        )}
      </div>

      <div className="btn-group" style={{ justifyContent: 'center', marginTop: 30 }}>
        <button className="btn btn-primary" onClick={onContinue}>
          Generate My Lesson Plan
        </button>
      </div>
    </div>
  )
}

// Curriculum View Component
function CurriculumView({ user, topic, curriculum, onStartLearning }) {
  return (
    <div className="curriculum-container">
      <h2>Your Personalized Curriculum</h2>
      <MarkdownContent content={curriculum} />
      <div className="btn-group">
        <button className="btn btn-primary" onClick={onStartLearning}>
          Start Learning
        </button>
      </div>
    </div>
  )
}

// Lesson/Chat Component
function LessonView({ user, topic, curriculum, onCompleteModule }) {
  const [messages, setMessages] = useState([
    { role: 'jarvis', content: `Hi! I'm Jarvis, your AI tutor. Let's start learning about ${topic}. What would you like to know first?` }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/chat`, {
        username: user.username,
        message: userMessage,
        context: { topic, curriculum }
      })
      setMessages(prev => [...prev, { role: 'jarvis', content: res.data.response }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'jarvis',
        content: "I apologize, I'm having trouble connecting to the server. Please try again."
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-content">
              <MarkdownContent content={msg.content} />
            </div>
          </div>
        ))}
        {loading && (
          <div className="message jarvis">
            <div className="loading">
              <div className="loading-spinner"></div>
              <p>Jarvis is thinking...</p>
            </div>
          </div>
        )}
      </div>
      <div className="chat-input-area">
        <input
          type="text"
          placeholder="Ask a question about the lesson..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  )
}

// Quiz Component
function Quiz({ user, topic, module, onComplete }) {
  const [quiz, setQuiz] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadQuiz()
  }, [])

  const loadQuiz = async () => {
    try {
      const res = await axios.post(`${API_BASE}/quiz/generate`, {
        username: user.username,
        topic,
        module,
        question_count: 5
      })
      setQuiz(res.data.quiz)
    } catch (err) {
      alert('Error loading quiz: ' + err.message)
    }
  }

  const handleAnswer = async (option) => {
    if (showFeedback) return
    setSelectedAnswer(option)
    setShowFeedback(true)
    setLoading(true)

    const question = quiz[currentIndex]
    try {
      const res = await axios.post(`${API_BASE}/quiz/evaluate`, {
        username: user.username,
        topic,
        module,
        question_id: question.id,
        answer: option,
        is_quiz: true,
        context: { question }
      })
      setFeedback(res.data)
      if (res.data.is_correct) {
        setScore(prev => prev + 1)
      }
    } catch (err) {
      console.error('Error evaluating answer:', err)
    } finally {
      setLoading(false)
    }
  }

  const nextQuestion = () => {
    if (currentIndex < quiz.length - 1) {
      setCurrentIndex(prev => prev + 1)
      setSelectedAnswer(null)
      setShowFeedback(false)
      setFeedback(null)
    } else {
      onComplete(score + (feedback?.is_correct ? 0 : 0), quiz.length)
    }
  }

  if (quiz.length === 0) {
    return <div className="loading"><div className="loading-spinner"></div>Loading quiz...</div>
  }

  const question = quiz[currentIndex]

  return (
    <div className="quiz-container">
      <div className="quiz-header">
        <h2>Module Quiz</h2>
        <p>Question {currentIndex + 1} of {quiz.length}</p>
      </div>
      <div className="progress-bar">
        <div className="progress" style={{ width: `${((currentIndex + 1) / quiz.length) * 100}%` }}></div>
      </div>
      <div className="quiz-question">
        <h3>{question.question}</h3>
        <div className="options-list">
          {Object.entries(question.options).map(([key, value]) => {
            let className = 'option-btn'
            if (showFeedback) {
              if (key === question.correct_answer) {
                className += ' correct'
              } else if (key === selectedAnswer) {
                className += ' incorrect'
              }
            } else if (selectedAnswer === key) {
              className += ' selected'
            }
            return (
              <button
                key={key}
                className={className}
                onClick={() => handleAnswer(key)}
                disabled={showFeedback}
              >
                <strong>{key}.</strong> {value}
              </button>
            )
          })}
        </div>
      </div>
      {showFeedback && feedback && (
        <div className={`quiz-feedback ${feedback.is_correct ? 'correct' : 'incorrect'}`}>
          <h4>{feedback.is_correct ? '✓ Correct!' : '✗ Not quite right'}</h4>
          <MarkdownContent content={feedback.feedback} />
          <div className="btn-group">
            <button className="btn btn-primary" onClick={nextQuestion} disabled={loading}>
              {currentIndex < quiz.length - 1 ? 'Next Question' : 'See Results'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Quiz Results Component
function QuizResults({ score, total, onContinue, onRetake }) {
  const percentage = (score / total) * 100
  const passed = percentage >= 70

  return (
    <div className="results-screen">
      <h2>{passed ? '🎉 Module Complete!' : '📚 Keep Learning!'}</h2>
      <div className="accuracy-display">{Math.round(percentage)}%</div>
      <p>{score} of {total} correct</p>

      {passed ? (
        <p style={{ color: '#00ff88', marginTop: 20 }}>Great job! You've mastered this module.</p>
      ) : (
        <p style={{ color: '#ffcc00', marginTop: 20 }}>You need 70% to pass. Let's review and try again.</p>
      )}

      <div className="btn-group" style={{ justifyContent: 'center', marginTop: 30 }}>
        {!passed && (
          <button className="btn btn-secondary" onClick={onRetake}>
            Retake Quiz
          </button>
        )}
        <button className="btn btn-primary" onClick={onContinue}>
          {passed ? 'Continue to Next Module' : 'Review Material'}
        </button>
      </div>
    </div>
  )
}

// Main App Component
export default function App() {
  const [user, setUser] = useState(null)
  const [topic, setTopic] = useState(null)
  const [goal, setGoal] = useState('')
  const [assessment, setAssessment] = useState(null)
  const [curriculum, setCurriculum] = useState(null)
  const [view, setView] = useState('login') // login, topic, onboarding, results, curriculum, lesson, quiz

  const handleLogin = (userData) => {
    setUser(userData)
    setView(userData.is_new ? 'topic' : 'main')
  }

  const handleStartTopic = (t, g) => {
    setTopic(t)
    setGoal(g)
    setView('onboarding')
  }

  const handleOnboardingComplete = (result) => {
    setAssessment(result)
    setView('results')
  }

  const handleGenerateCurriculum = async () => {
    try {
      const res = await axios.post(`${API_BASE}/generate-curriculum`, {
        username: user.username,
        topic,
        goal
      })
      setCurriculum(res.data.curriculum)
      setView('curriculum')
    } catch (err) {
      alert('Error generating curriculum: ' + err.message)
    }
  }

  const handleQuizComplete = (score, total) => {
    // For now, just show results
    alert(`Quiz complete! Score: ${score}/${total}`)
    setView('main')
  }

  const handleLogout = () => {
    setUser(null)
    setTopic(null)
    setGoal('')
    setAssessment(null)
    setCurriculum(null)
    setView('login')
  }

  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="app">
      <div className="main-layout">
        <aside className="sidebar">
          <div className="user-info">
            <div className="username">👤 {user.username}</div>
            <div className="status">
              {topic ? `Learning: ${topic}` : 'Ready to learn'}
            </div>
          </div>
          <h3>Menu</h3>
          <ul className="nav-menu">
            <li className={view === 'main' ? 'active' : ''} onClick={() => setView('main')}>
              📚 My Learning
            </li>
            <li className={view === 'curriculum' ? 'active' : ''} onClick={() => setView('curriculum')}>
              📋 Curriculum
            </li>
            <li onClick={handleLogout}>🚪 Logout</li>
          </ul>
        </aside>

        <main className="content-area">
          {view === 'topic' && (
            <TopicSelection user={user} onStartTopic={handleStartTopic} />
          )}
          {view === 'onboarding' && (
            <Onboarding
              user={user}
              topic={topic}
              onComplete={handleOnboardingComplete}
            />
          )}
          {view === 'results' && (
            <Results assessment={assessment} onContinue={handleGenerateCurriculum} />
          )}
          {view === 'curriculum' && curriculum && (
            <CurriculumView
              user={user}
              topic={topic}
              curriculum={curriculum}
              onStartLearning={() => setView('lesson')}
            />
          )}
          {view === 'lesson' && (
            <LessonView
              user={user}
              topic={topic}
              curriculum={curriculum}
              onCompleteModule={() => setView('quiz')}
            />
          )}
          {view === 'quiz' && (
            <Quiz
              user={user}
              topic={topic}
              module="Current Module"
              onComplete={handleQuizComplete}
            />
          )}
          {view === 'main' && (
            <div className="topic-selection">
              <h2>Welcome back, {user.username}!</h2>
              <p style={{ color: '#888', marginBottom: 30 }}>
                {topic
                  ? `Continue learning ${topic} or start something new.`
                  : "What would you like to learn today?"}
              </p>
              {topic && (
                <div className="btn-group" style={{ justifyContent: 'center', marginBottom: 30 }}>
                  <button className="btn btn-primary" onClick={() => setView('curriculum')}>
                    📋 View Curriculum
                  </button>
                  <button className="btn btn-primary" onClick={() => setView('lesson')}>
                    📖 Continue Learning
                  </button>
                </div>
              )}
              <TopicSelection user={user} onStartTopic={handleStartTopic} />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
