import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAllCards } from '../data/cards';

export default function Daily5({ showXp }) {
  const allCards = getAllCards();
  const daily = allCards.slice(0, 5);
  const [current, setCurrent] = useState(0);
  const [completed, setCompleted] = useState([]);
  const [flipped, setFlipped] = useState(false);

  const card = daily[current];
  const done = completed.length === 5;

  const markDone = () => {
    setCompleted(c => [...c, current]);
    showXp(20);
    if (current < 4) {
      setTimeout(() => { setCurrent(current + 1); setFlipped(false); }, 500);
    }
  };

  if (done) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
      <div style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Daily 5 Complete!</div>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>+100 XP earned · Streak extended to Day 24</div>
      <div style={{ fontSize: 48, marginTop: 16 }}>🔥</div>
    </div>
  );

  return (
    <div className="card-viewer">
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>⚡ Daily 5 Review</h2>
        <p style={{ color: 'var(--text-secondary)' }}>FSRS-optimized cards scheduled for review today</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
          {daily.map((_, i) => (
            <div key={i} style={{
              width: 40, height: 6, borderRadius: 3,
              background: completed.includes(i) ? 'var(--success)' : i === current ? 'var(--brand-primary)' : 'var(--bg-tertiary)'
            }} />
          ))}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>{completed.length} of 5 complete</div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div 
          key={current} 
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
          >
            <div className="flip-card-front">
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                {card.categoryIcon} {card.category}
              </div>
              <span className={`card-difficulty ${card.difficulty}`}>{card.difficulty}</span>
              <div className="card-question">{card.q}</div>
              <div className="card-hint">Click to reveal answer</div>
            </div>
            <div className="flip-card-back" onClick={e => e.stopPropagation()}>
              <div className="card-answer">{card.a}</div>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>

      {flipped && (
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24 }}>
          <button className="nav-btn" onClick={() => { setFlipped(false); }}>🔄 Again</button>
          <button className="mastery-btn" onClick={markDone}>✅ Got it (+20 XP)</button>
        </div>
      )}
    </div>
  );
}
