export default function Sidebar({ page, setPage, stats, isOpen, onClose }) {
  const xpForNext = (stats.level + 1) * 500;
  const xpProgress = ((stats.totalXp % 500) / 500) * 100;

  const nav = [
    { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
    { id: 'daily5', icon: '⚡', label: 'Daily 5', badge: '5' },
    { id: 'study', icon: '📚', label: 'The Forge' },
    { id: 'ats', icon: '📄', label: 'ATS Scanner' },
    { id: 'mission', icon: '🎯', label: 'Mission Mode' },
    { id: 'achievements', icon: '🏆', label: 'Achievements' },
  ];

  return (
    <div className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">⚒️</div>
          <h1>SkillForge</h1>
        </div>
      </div>

      <div className="sidebar-streak">
        <div className="streak-display">
          <span className="streak-flame">🔥</span>
          <div>
            <div className="streak-num">{stats.currentStreak}</div>
            <div className="streak-label">Day Streak</div>
          </div>
        </div>
      </div>

      <div className="sidebar-xp">
        <div className="xp-header">
          <span className="xp-level">Level {stats.level}</span>
          <span className="xp-amount">{stats.totalXp} XP</span>
        </div>
        <div className="xp-bar">
          <div className="xp-fill" style={{ width: `${xpProgress}%` }} />
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Main</div>
        {nav.map(item => (
          <div
            key={item.id}
            className={`nav-item ${page === item.id ? 'active' : ''}`}
            onClick={() => { setPage(item.id); onClose(); }}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </div>
        ))}
        <div className="nav-section-title">Admin</div>
        <div
          className={`nav-item ${page === 'admin' ? 'active' : ''}`}
          onClick={() => { setPage('admin'); onClose(); }}
        >
          <span className="nav-icon">⚙️</span>
          Admin Panel
        </div>
      </nav>
    </div>
  );
}
