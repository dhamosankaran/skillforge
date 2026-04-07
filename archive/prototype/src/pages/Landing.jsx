export default function Landing({ onLogin }) {
  return (
    <div style={{ background: 'var(--bg-primary)', minHeight: '100vh' }}>
      {/* Nav */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 40px', borderBottom: 'var(--border-subtle)' }}>
        <div className="logo">
          <div className="logo-icon">⚒️</div>
          <h1>SkillForge</h1>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn-outline" onClick={onLogin}>Sign In</button>
          <button className="btn-primary" onClick={onLogin}>Start Free →</button>
        </div>
      </div>

      {/* Hero */}
      <div className="landing-hero">
        <div className="hero-badge">🚀 AI-Powered Career Acceleration</div>
        <h1 className="hero-title">
          Master the <span className="gradient">Agentic AI</span> Stack.<br />
          Land Your Next Role.
        </h1>
        <p className="hero-sub">
          177+ expert-curated flashcards with real production experience, 
          AI-powered resume analysis, and personalized interview preparation 
          built by a Principal Architect.
        </p>
        <div className="hero-cta-row">
          <button className="btn-primary" style={{ padding: '16px 36px', fontSize: 16 }} onClick={onLogin}>
            🔍 Free ATS Scan
          </button>
          <button className="btn-outline" style={{ padding: '16px 36px', fontSize: 16 }} onClick={onLogin}>
            Explore Cards →
          </button>
        </div>
      </div>

      {/* Features */}
      <div style={{ padding: '60px 40px', maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <h2 style={{ fontSize: 36, fontWeight: 800, marginBottom: 12 }}>Two Engines. <span style={{ color: 'var(--brand-primary)' }}>One Platform.</span></h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 16, maxWidth: 600, margin: '0 auto' }}>Mission Mode gets you interview-ready. The Forge keeps you sharp for years.</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 60 }}>
          {[
            { icon: '🎯', title: 'Mission Mode', desc: 'Focused interview sprints with countdown timer, ATS tracking, and personalized experience generation from your resume.', color: 'var(--danger)' },
            { icon: '🔥', title: 'The Forge', desc: 'Daily spaced repetition, streaks, XP, skill badges, and deep-dive access to the full 177+ card library.', color: 'var(--success)' },
            { icon: '📄', title: 'ATS Resume Scanner', desc: 'AI-powered resume analysis against job descriptions. See your exact skill gaps and get card recommendations.', color: 'var(--info)' },
            { icon: '🤖', title: '4-Tier Experiences', desc: 'Expert production stories, AI-generated reference patterns, your resume-based experience, and community answers.', color: 'var(--brand-primary)' },
          ].map(f => (
            <div key={f.title} style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-xl)', padding: 32 }}>
              <div style={{ fontSize: 36, marginBottom: 16 }}>{f.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing */}
      <div style={{ padding: '0 40px 80px' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <h2 style={{ fontSize: 36, fontWeight: 800, marginBottom: 12 }}>Simple Pricing</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Start free. Upgrade when you're ready.</p>
        </div>
        <div className="pricing-grid">
          <div className="pricing-card">
            <div className="pricing-name">Free</div>
            <div className="pricing-price">$0<span>/month</span></div>
            <ul className="pricing-features">
              <li>Foundations category (15 cards)</li>
              <li>1 free ATS scan</li>
              <li>Basic progress tracking</li>
              <li>Quiz mode</li>
            </ul>
            <button className="btn-outline" style={{ width: '100%', marginTop: 24 }} onClick={onLogin}>Get Started</button>
          </div>
          <div className="pricing-card featured">
            <div className="pricing-name">Pro</div>
            <div className="pricing-price">$49<span>/month</span></div>
            <ul className="pricing-features">
              <li>All 177+ expert cards</li>
              <li>Unlimited ATS scans</li>
              <li>Mission Mode sprints</li>
              <li>AI experience generation</li>
              <li>FSRS Daily 5 reviews</li>
              <li>Streaks, XP, badges</li>
              <li>4-tier experiences</li>
            </ul>
            <button className="btn-primary" style={{ width: '100%', marginTop: 24 }} onClick={onLogin}>Start Pro Trial →</button>
          </div>
          <div className="pricing-card">
            <div className="pricing-name">Enterprise</div>
            <div className="pricing-price">$299<span>/seat/mo</span></div>
            <ul className="pricing-features">
              <li>Everything in Pro</li>
              <li>Team skill heatmaps</li>
              <li>Manager dashboards</li>
              <li>Custom company cards</li>
              <li>SSO / SAML</li>
              <li>Compliance reporting</li>
              <li>Dedicated support</li>
            </ul>
            <button className="btn-outline" style={{ width: '100%', marginTop: 24 }}>Contact Sales</button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ borderTop: 'var(--border-subtle)', padding: '24px 40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
        © 2026 SkillForge. Career Acceleration Platform for the Agentic AI Era.
      </div>
    </div>
  );
}
