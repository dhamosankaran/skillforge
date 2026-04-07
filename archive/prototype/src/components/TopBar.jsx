export default function TopBar({ onMenuClick, onLanding }) {
  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button className="topbar-btn" onClick={onMenuClick} style={{ display: 'none' }}>☰</button>
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input placeholder="Search cards, topics, concepts..." />
          <span className="search-shortcut">⌘K</span>
        </div>
      </div>
      <div className="topbar-actions">
        <button className="topbar-btn" onClick={onLanding}>🌐 Landing</button>
        <button className="topbar-btn">🔔</button>
        <div className="user-avatar" title="KD">KD</div>
      </div>
    </div>
  );
}
