import { useState } from 'react';
import { getAllCards } from '../data/cards';

export default function MissionMode({ showXp }) {
  const missionCards = getAllCards().slice(0, 8);
  const [masteredIds, setMasteredIds] = useState(['tf-1', 'pe-1', 'rag-1']);
  const [activeCard, setActiveCard] = useState(null);
  const total = missionCards.length;
  const done = masteredIds.length;
  const pct = Math.round((done / total) * 100);

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="mission-banner">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 24 }}>
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>🎯 Active Mission</div>
            <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>Capital One — AI Architect</h2>
            <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Interview: April 20, 2026</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="mission-countdown">14</div>
            <div className="mission-countdown-label">Days Left</div>
          </div>
        </div>
        <div className="mission-progress-bar">
          <div className="mission-progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span style={{ color: 'var(--text-secondary)' }}>{done} of {total} cards mastered</span>
          <span style={{ color: 'var(--warning)', fontWeight: 600 }}>{pct}%</span>
        </div>
        <div style={{ display: 'flex', gap: 24, marginTop: 20 }}>
          <div style={{ background: 'rgba(239,68,68,0.1)', borderRadius: 'var(--radius-md)', padding: '12px 20px', flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--danger)' }}>62%</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Initial ATS</div>
          </div>
          <div style={{ background: 'rgba(16,185,129,0.1)', borderRadius: 'var(--radius-md)', padding: '12px 20px', flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--success)' }}>74%</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Current ATS</div>
          </div>
          <div style={{ background: 'rgba(99,102,241,0.1)', borderRadius: 'var(--radius-md)', padding: '12px 20px', flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--brand-primary)' }}>+12%</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Improvement</div>
          </div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Mission Cards</span>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Focus on red items first</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {missionCards.map(card => {
          const isMastered = masteredIds.includes(card.id);
          return (
            <div key={card.id} onClick={() => setActiveCard(activeCard === card.id ? null : card.id)} style={{
              background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-md)',
              padding: '16px 20px', cursor: 'pointer', transition: 'all 0.2s',
              borderLeft: `3px solid ${isMastered ? 'var(--success)' : 'var(--danger)'}`,
              opacity: isMastered ? 0.7 : 1,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 18 }}>{card.categoryIcon || '📝'}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, textDecoration: isMastered ? 'line-through' : 'none' }}>{card.q.slice(0, 70)}...</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{card.category || 'General'} · {card.difficulty}</div>
                  </div>
                </div>
                {isMastered
                  ? <span style={{ color: 'var(--success)', fontWeight: 600, fontSize: 13 }}>✅ Mastered</span>
                  : <button className="btn-primary" style={{ padding: '6px 16px', fontSize: 12 }} onClick={e => {
                      e.stopPropagation();
                      setMasteredIds(m => [...m, card.id]);
                      showXp(25);
                    }}>Study →</button>
                }
              </div>
              {activeCard === card.id && (
                <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>👤 Your Experience (AI-Generated):</div>
                  {card.aiRefExp || 'Experience will be generated from your resume using Gemini 2.5 Pro reasoning model.'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
