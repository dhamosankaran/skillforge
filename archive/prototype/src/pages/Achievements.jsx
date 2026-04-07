import { BADGES } from '../data/cards';

export default function Achievements({ stats }) {
  const earned = BADGES.filter(b => b.earned);
  const locked = BADGES.filter(b => !b.earned);

  // Radar chart data (mock)
  const skills = [
    { name: 'RAG', pct: 45 }, { name: 'Agents', pct: 30 }, { name: 'Prompt Eng', pct: 65 },
    { name: 'Security', pct: 20 }, { name: 'MLOps', pct: 35 }, { name: 'Eval', pct: 55 },
    { name: 'LangChain', pct: 70 }, { name: 'Architecture', pct: 60 },
  ];

  return (
    <div>
      <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>🏆 Achievements</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 32 }}>Track your mastery and earn badges across domains</p>

      {/* Stats Overview */}
      <div className="stats-row" style={{ marginBottom: 32 }}>
        <div className="stat-card">
          <div className="stat-label">Total XP</div>
          <div className="stat-value" style={{ color: 'var(--brand-primary)' }}>{stats.totalXp.toLocaleString()}</div>
          <div className="stat-change">Level {stats.level}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Current Streak</div>
          <div className="stat-value" style={{ color: '#F59E0B' }}>🔥 {stats.currentStreak}</div>
          <div className="stat-change">Best: {stats.longestStreak} days</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Badges Earned</div>
          <div className="stat-value">{earned.length}/{BADGES.length}</div>
          <div className="stat-change">{BADGES.length - earned.length} remaining</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Study Hours</div>
          <div className="stat-value">{Math.floor(stats.totalStudyMinutes / 60)}</div>
          <div className="stat-change">{stats.totalStudyMinutes} minutes total</div>
        </div>
      </div>

      {/* Skill Radar (simplified visual) */}
      <div className="radar-container" style={{ marginBottom: 32 }}>
        <div className="section-header" style={{ marginBottom: 20 }}>
          <span className="section-title">📡 Skill Radar</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
          {skills.map(s => (
            <div key={s.name} style={{ background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</span>
                <span style={{ fontSize: 13, color: s.pct >= 60 ? 'var(--success)' : s.pct >= 40 ? 'var(--warning)' : 'var(--danger)' }}>{s.pct}%</span>
              </div>
              <div style={{ height: 6, background: 'var(--bg-primary)', borderRadius: 3 }}>
                <div style={{
                  height: '100%', borderRadius: 3, width: `${s.pct}%`, transition: 'width 1s',
                  background: s.pct >= 60 ? 'var(--gradient-emerald)' : s.pct >= 40 ? 'var(--gradient-gold)' : 'linear-gradient(135deg, var(--danger), #F97316)'
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Earned Badges */}
      <div className="section-header"><span className="section-title">🏅 Earned</span></div>
      <div className="badge-grid" style={{ marginBottom: 32 }}>
        {earned.map(b => (
          <div key={b.id} className="badge-card earned">
            <span className="badge-icon">{b.icon}</span>
            <div className="badge-name">{b.name}</div>
            <div className="badge-desc">{b.description}</div>
          </div>
        ))}
      </div>

      {/* Locked Badges */}
      <div className="section-header"><span className="section-title">🔒 Locked</span></div>
      <div className="badge-grid">
        {locked.map(b => (
          <div key={b.id} className="badge-card locked">
            <span className="badge-icon">{b.icon}</span>
            <div className="badge-name">{b.name}</div>
            <div className="badge-desc">{b.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
