import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CATEGORIES, getAllCards } from '../data/cards';

export default function StudyEngine({ category, showXp }) {
  const allCards = category ? (CATEGORIES[category]?.cards || []) : getAllCards();
  const catInfo = category ? CATEGORIES[category] : null;
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [expTab, setExpTab] = useState('expert');
  const [mastered, setMastered] = useState({});
  const [quizAnswer, setQuizAnswer] = useState(null);
  const [feedback, setFeedback] = useState({});
  const [bookmarked, setBookmarked] = useState({});

  if (allCards.length === 0) return <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Select a category from the Dashboard</div>;

  const card = allCards[idx];
  const cardId = card.id;

  const next = () => { setIdx(i => Math.min(i + 1, allCards.length - 1)); setFlipped(false); setQuizAnswer(null); };
  const prev = () => { setIdx(i => Math.max(i - 1, 0)); setFlipped(false); setQuizAnswer(null); };

  const toggleMastery = () => {
    const was = mastered[cardId];
    setMastered(m => ({ ...m, [cardId]: !was }));
    if (!was) showXp(25);
  };

  const handleQuiz = (i) => {
    if (quizAnswer !== null) return;
    setQuizAnswer(i);
    if (i === card.quiz.correct) showXp(15);
  };

  const expContent = {
    expert: { text: card.expertExp, source: '⭐ Expert — Production experience from a Principal Architect' },
    ai: { text: card.aiRefExp, source: '🤖 AI Reference — Gemini-synthesized from industry best practices' },
    mine: { text: '📎 Upload your resume in the ATS Scanner to generate a personalized experience based on YOUR background. This will use Gemini 2.5 Pro reasoning to map your resume bullets to this card.', source: '👤 My Experience — Generated from your resume' },
    community: { text: '👥 Community experiences will appear here as users opt-in to share their anonymized responses. Coming in Phase 2.', source: '👥 Community — Anonymized, user-shared' },
  };

  return (
    <div className="card-viewer">
      {catInfo && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <span style={{ fontSize: 28 }}>{catInfo.icon}</span>
          <span style={{ fontSize: 20, fontWeight: 700 }}>{category}</span>
        </div>
      )}
      <div className="card-nav-top">
        <div className="card-counter">Card {idx + 1} of {allCards.length}</div>
        <div className="card-nav-actions">
          <button className={`card-action-btn ${bookmarked[cardId] ? 'active' : ''}`} onClick={() => setBookmarked(b => ({ ...b, [cardId]: !b[cardId] }))}>
            {bookmarked[cardId] ? '★' : '☆'} Bookmark
          </button>
          <button className="card-action-btn">{card.difficulty}</button>
        </div>
      </div>

      {/* Flip Card */}
      <AnimatePresence mode="wait">
        <motion.div 
          key={cardId} 
          initial={{ opacity: 0, x: 50 }} 
          animate={{ opacity: 1, x: 0 }} 
          exit={{ opacity: 0, x: -50 }} 
          transition={{ duration: 0.3 }}
          className="flip-card-container" 
          onClick={() => setFlipped(f => !f)}
        >
          <motion.div 
            className="flip-card" 
            initial={false}
            animate={{ rotateY: flipped ? 180 : 0 }}
            transition={{ duration: 0.6, type: 'spring', stiffness: 260, damping: 20 }}
            style={{ minHeight: flipped ? 'auto' : 400 }}
          >
            <div className="flip-card-front">
              <span className={`card-difficulty ${card.difficulty}`}>{card.difficulty}</span>
              <div className="card-question">{card.q}</div>
              <div className="card-hint">Click to flip →</div>
            </div>
            <div className="flip-card-back" onClick={e => e.stopPropagation()}>
              <div className="card-answer">{card.a}</div>
              <div className="card-tags">
                {card.tags.map(t => <span key={t} className="tag">{t}</span>)}
              </div>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>

      {/* Experience Tabs */}
      <div className="exp-tabs">
        {[['expert', '⭐ Expert'], ['ai', '🤖 AI Ref'], ['mine', '👤 Mine'], ['community', '👥 Community']].map(([key, label]) => (
          <button key={key} className={`exp-tab ${expTab === key ? 'active' : ''}`} onClick={() => setExpTab(key)}>{label}</button>
        ))}
      </div>
      <div className="exp-content">
        <div>{expContent[expTab].text}</div>
        <div className="exp-source">{expContent[expTab].source}</div>
      </div>

      {/* Quiz */}
      {card.quiz && (
        <div className="quiz-section" style={{ marginTop: 24 }}>
          <div className="quiz-question">🧪 {card.quiz.question}</div>
          <div className="quiz-options">
            {card.quiz.options.map((opt, i) => {
              let cls = 'quiz-option';
              if (quizAnswer !== null) {
                if (i === card.quiz.correct) cls += ' correct';
                else if (i === quizAnswer) cls += ' wrong';
              } else if (i === quizAnswer) cls += ' selected';
              return (
                <div key={i} className={cls} onClick={() => handleQuiz(i)}>
                  <span className="quiz-letter">{String.fromCharCode(65 + i)}</span>
                  {opt}
                </div>
              );
            })}
          </div>
          {quizAnswer !== null && (
            <div className="quiz-explanation">
              {quizAnswer === card.quiz.correct ? '✅ Correct! ' : '❌ Incorrect. '}
              {card.quiz.explanation}
            </div>
          )}
        </div>
      )}

      {/* Feedback */}
      <div className="card-feedback">
        <span>Was this helpful?</span>
        <button className={`feedback-btn ${feedback[cardId] === 'up' ? 'liked' : ''}`} onClick={() => setFeedback(f => ({ ...f, [cardId]: 'up' }))}>👍</button>
        <button className={`feedback-btn ${feedback[cardId] === 'down' ? 'disliked' : ''}`} onClick={() => setFeedback(f => ({ ...f, [cardId]: 'down' }))}>👎</button>
      </div>

      {/* Navigation */}
      <div className="card-nav-bottom">
        <button className="nav-btn" onClick={prev} disabled={idx === 0}>← Previous</button>
        <button className={`mastery-btn ${mastered[cardId] ? 'mastered' : ''}`} onClick={toggleMastery}>
          {mastered[cardId] ? '✅ Mastered' : '🎯 Mark Mastered'}
        </button>
        <button className="nav-btn" onClick={next} disabled={idx === allCards.length - 1}>Next →</button>
      </div>
    </div>
  );
}
