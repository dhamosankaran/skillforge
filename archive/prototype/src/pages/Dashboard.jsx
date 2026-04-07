import { CATEGORIES, getTotalCards, getCategoryCount } from '../data/cards';

export default function Dashboard({ stats, onCategoryClick, onDaily5 }) {
  const categories = Object.entries(CATEGORIES);
  // Mock progress per category
  const progress = { 'Transformer Fundamentals': 80, 'Prompt Engineering': 65, 'RAG Architecture': 45, 'AI Agents & MCP': 30, 'Evaluation & Benchmarks': 55, 'Security & Guardrails': 20, 'LangChain & LangGraph': 70, 'MLOps & Serving': 35, 'Context Engineering': 40, 'System Design & Leadership': 60, 'Architecture Patterns': 50, 'Cloud & DevOps': 75, 'API & Security Patterns': 55, 'Design Patterns': 90 };

  // Heatmap
  const heatDays = [];
  const today = new Date();
  for (let i = 119; i >= 0; i--) {
    const d = new Date(today); d.setDate(d.getDate() - i);
    const key = d.toISOString().split('T')[0];
    const val = stats.dailyActivity[key] || 0;
    const level = val === 0 ? '' : val < 10 ? 'l1' : val < 20 ? 'l2' : val < 35 ? 'l3' : 'l4';
    heatDays.push({ key, val, level });
  }

  return (
    <div>
      <div className="dashboard-header">
        <div className="welcome-text">Welcome back, Kalai 👋</div>
        <div className="welcome-sub">You have 5 cards due for review today. Keep your streak alive!</div>
      </div>

      <div className="daily5-cta" onClick={onDaily5}>
        <div className="daily5-info">
          <h3>⚡ Daily 5 — Ready for Review</h3>
          <p>5 cards optimized by FSRS for your memory retention today</p>
        </div>
        <button className="daily5-btn">Start Review →</button>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Cards Mastered</div>
          <div className="stat-value">{stats.totalCardsMastered}</div>
          <div className="stat-change">↑ 6 this week</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Reviews</div>
          <div className="stat-value">{stats.totalReviews}</div>
          <div className="stat-change">↑ 23 this week</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Study Time</div>
          <div className="stat-value">{Math.floor(stats.totalStudyMinutes / 60)}h</div>
          <div className="stat-change">↑ 3.5h this week</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Categories</div>
          <div className="stat-value">{getCategoryCount()}</div>
          <div className="stat-change">{getTotalCards()} total cards</div>
        </div>
      </div>

      {/* Activity Heatmap */}
      <div className="heatmap-container">
        <div className="section-header" style={{ marginBottom: 16 }}>
          <span className="section-title">📊 Study Activity</span>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Last 120 days</span>
        </div>
        <div className="heatmap-grid">
          {heatDays.map(d => (
            <div key={d.key} className={`heatmap-cell ${d.level}`} title={`${d.key}: ${d.val} min`} />
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, justifyContent: 'flex-end' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Less</span>
          <div className="heatmap-cell" style={{ width: 10, height: 10 }} />
          <div className="heatmap-cell l1" style={{ width: 10, height: 10 }} />
          <div className="heatmap-cell l2" style={{ width: 10, height: 10 }} />
          <div className="heatmap-cell l3" style={{ width: 10, height: 10 }} />
          <div className="heatmap-cell l4" style={{ width: 10, height: 10 }} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>More</span>
        </div>
      </div>

      {/* Category Grid */}
      <div className="section-header">
        <span className="section-title">📚 Study Domains</span>
        <span className="section-action">View All →</span>
      </div>
      <div className="category-grid">
        {categories.map(([name, cat]) => {
          const pct = progress[name] || Math.floor(Math.random() * 80);
          return (
            <div key={name} className="category-card" onClick={() => onCategoryClick(name)}>
              <div className="category-card-header">
                <div className="category-icon-wrap" style={{ background: `${cat.color}20` }}>
                  {cat.icon}
                </div>
                <div>
                  <div className="category-card-name">{name}</div>
                  <div className="category-card-count">{cat.cards.length} card{cat.cards.length > 1 ? 's' : ''}</div>
                </div>
              </div>
              <div className="category-progress">
                <div className="category-progress-fill" style={{ width: `${pct}%`, background: cat.color }} />
              </div>
              <div className="category-progress-text">{pct}% mastered</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
