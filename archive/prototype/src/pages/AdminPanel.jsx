import { useState } from 'react';
import { CATEGORIES, getAllCards } from '../data/cards';

export default function AdminPanel() {
  const [tab, setTab] = useState('cards');
  const allCards = getAllCards();

  const tabs = [
    { id: 'cards', label: '📚 Cards', badge: allCards.length },
    { id: 'analytics', label: '📊 Analytics' },
    { id: 'feedback', label: '💬 Feedback', badge: '12' },
    { id: 'llm', label: '🤖 LLM Costs' },
  ];

  const mockFeedback = [
    { card: 'rag-1', type: 'confusing', comment: 'The chunking section needs more examples', date: '2h ago', status: 'new' },
    { card: 'sec-4', type: 'outdated', comment: 'Missing info about NHI Zero Trust updates', date: '5h ago', status: 'new' },
    { card: 'pe-1', type: 'too_basic', comment: 'Need more advanced DSPy examples', date: '1d ago', status: 'reviewed' },
    { card: 'ai-35', type: 'missing_info', comment: 'Please add A2A protocol comparison', date: '1d ago', status: 'new' },
  ];

  return (
    <div>
      <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>⚙️ Admin Panel</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Manage content, analytics, and user feedback</p>

      <div style={{ display: 'flex', gap: 4, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: 4, marginBottom: 32 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            flex: 1, padding: '10px 16px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 500, transition: 'all 0.2s',
            background: tab === t.id ? 'var(--bg-card)' : 'transparent', color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
            boxShadow: tab === t.id ? 'var(--shadow-sm)' : 'none',
          }}>
            {t.label} {t.badge && <span className="nav-badge" style={{ marginLeft: 6 }}>{t.badge}</span>}
          </button>
        ))}
      </div>

      {tab === 'cards' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <input placeholder="Search cards..." style={{ background: 'var(--bg-tertiary)', border: 'var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '8px 16px', color: 'var(--text-primary)', width: 300, fontSize: 14 }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-outline">📥 Import JSON</button>
              <button className="btn-outline">📤 Export</button>
              <button className="btn-primary">+ New Card</button>
            </div>
          </div>
          <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
            <table className="admin-table">
              <thead><tr><th>ID</th><th>Question</th><th>Category</th><th>Difficulty</th><th>Views</th><th>Mastery</th><th>Actions</th></tr></thead>
              <tbody>
                {allCards.slice(0, 10).map(c => (
                  <tr key={c.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>{c.id}</td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.q.slice(0, 60)}...</td>
                    <td>{c.category || c.tags?.[0]}</td>
                    <td><span className={`admin-badge`} style={{ background: c.difficulty === 'Hard' ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)', color: c.difficulty === 'Hard' ? 'var(--danger)' : 'var(--warning)' }}>{c.difficulty}</span></td>
                    <td>{Math.floor(Math.random() * 3000 + 500)}</td>
                    <td>{Math.floor(Math.random() * 80 + 20)}%</td>
                    <td><button className="btn-outline" style={{ padding: '4px 10px', fontSize: 12 }}>Edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'analytics' && (
        <div>
          <div className="stats-row" style={{ marginBottom: 32 }}>
            {[['DAU', '342', '↑ 8%'], ['WAU', '1,205', '↑ 12%'], ['MAU', '3,891', '↑ 15%'], ['MRR', '$24,500', '↑ 18%']].map(([l, v, c]) => (
              <div key={l} className="stat-card"><div className="stat-label">{l}</div><div className="stat-value">{v}</div><div className="stat-change">{c}</div></div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>📈 Conversion Funnel</h3>
              {[['Visitors', 12400, 100], ['Signups', 2480, 20], ['Free Users', 1860, 15], ['Pro Subscribers', 502, 4.1]].map(([label, num, pct]) => (
                <div key={label} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span>{label}</span><span style={{ color: 'var(--text-muted)' }}>{num.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div style={{ height: 8, background: 'var(--bg-tertiary)', borderRadius: 4 }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: 'var(--gradient-brand)', borderRadius: 4 }} />
                  </div>
                </div>
              ))}
            </div>
            <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>🏆 Top Cards (This Week)</h3>
              {[['pe-1', 'Prompt Engineering Techniques', 4521], ['rag-1', 'Production RAG Design', 3892], ['ai-35', 'MCP Architecture', 3104], ['sec-4', 'Five Imperatives', 2890], ['ev-3', 'AI Paradigm Shift', 2456]].map(([id, name, views]) => (
                <div key={id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: 'var(--border-subtle)', fontSize: 13 }}>
                  <span>{name}</span><span style={{ color: 'var(--text-muted)' }}>{views.toLocaleString()} views</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'feedback' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <div>
              <span style={{ fontSize: 14, fontWeight: 600 }}>NPS Score: </span>
              <span style={{ fontSize: 24, fontWeight: 800, color: 'var(--success)' }}>72</span>
              <span style={{ fontSize: 13, color: 'var(--text-muted)', marginLeft: 8 }}>Promoters: 45 · Passives: 30 · Detractors: 12</span>
            </div>
            <button className="btn-primary">🤖 Generate Weekly Digest</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {mockFeedback.map((fb, i) => (
              <div key={i} style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-md)', padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--brand-primary)' }}>{fb.card}</span>
                    <span className="admin-badge" style={{ background: 'rgba(245,158,11,0.12)', color: 'var(--warning)' }}>{fb.type}</span>
                    {fb.status === 'new' && <span className="admin-badge" style={{ background: 'rgba(239,68,68,0.12)', color: 'var(--danger)' }}>NEW</span>}
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fb.date}</span>
                </div>
                <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{fb.comment}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'llm' && (
        <div>
          <div className="stats-row" style={{ marginBottom: 32 }}>
            <div className="stat-card"><div className="stat-label">MTD Spend</div><div className="stat-value">$287</div><div className="stat-change">Budget: $500</div></div>
            <div className="stat-card"><div className="stat-label">Gemini 2.5 Pro</div><div className="stat-value">$198</div><div className="stat-change">Experience gen + ATS</div></div>
            <div className="stat-card"><div className="stat-label">Gemini Flash</div><div className="stat-value">$67</div><div className="stat-change">Parsing + feedback</div></div>
            <div className="stat-card"><div className="stat-label">Embeddings</div><div className="stat-value">$22</div><div className="stat-change">text-embedding-005</div></div>
          </div>
          <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Cost by Feature</h3>
            {[['Experience Generation', 142, 49], ['ATS Scoring', 68, 24], ['Resume Parsing', 34, 12], ['Admin AI Assist', 28, 10], ['Quiz Feedback', 15, 5]].map(([name, cost, pct]) => (
              <div key={name} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span>{name}</span><span style={{ color: 'var(--text-muted)' }}>${cost} ({pct}%)</span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-tertiary)', borderRadius: 4 }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: 'var(--gradient-sky)', borderRadius: 4 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
