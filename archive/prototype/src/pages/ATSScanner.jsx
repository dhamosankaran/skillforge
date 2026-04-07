import { useState } from 'react';
import { MOCK_ATS_REPORT } from '../data/cards';

export default function ATSScanner({ onStartMission }) {
  const [step, setStep] = useState('upload'); // upload, scanning, results
  const report = MOCK_ATS_REPORT;

  const startScan = () => {
    setStep('scanning');
    setTimeout(() => setStep('results'), 2500);
  };

  if (step === 'upload') return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>📄 ATS Resume Scanner</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 32 }}>Upload your resume and paste a job description to see your match score and skill gaps.</p>
      
      <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-xl)', padding: 40, textAlign: 'center', marginBottom: 24 }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>📎</div>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Drop your resume here</div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>PDF or DOCX, max 5MB</div>
        <button className="btn-outline">Browse Files</button>
      </div>

      <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-xl)', padding: 24, marginBottom: 24 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>📋 Job Description</div>
        <textarea 
          placeholder="Paste the full job description here..."
          style={{ width: '100%', minHeight: 150, background: 'var(--bg-tertiary)', border: 'var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: 16, color: 'var(--text-primary)', fontSize: 14, resize: 'vertical', fontFamily: 'inherit' }}
        />
      </div>

      <button className="btn-primary" style={{ width: '100%', padding: 16, fontSize: 16 }} onClick={startScan}>
        🔍 Analyze Match Score
      </button>
    </div>
  );

  if (step === 'scanning') return (
    <div style={{ textAlign: 'center', padding: 100 }}>
      <div style={{ fontSize: 48, animation: 'pulse-glow 2s infinite', marginBottom: 24 }}>🔍</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Analyzing your resume...</div>
      <div style={{ color: 'var(--text-secondary)' }}>Gemini 2.5 Pro is reasoning about your skill gaps</div>
      <div style={{ marginTop: 24, height: 4, background: 'var(--bg-tertiary)', borderRadius: 2, maxWidth: 300, margin: '24px auto' }}>
        <div style={{ height: '100%', background: 'var(--gradient-brand)', borderRadius: 2, width: '60%', animation: 'pulse-glow 1s infinite' }} />
      </div>
    </div>
  );

  // Results
  const scoreColor = report.overallScore >= 80 ? 'var(--success)' : report.overallScore >= 60 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 24 }}>📊 ATS Analysis Results</h2>

      {/* Score Ring */}
      <div className="ats-score-ring" style={{ background: `conic-gradient(${scoreColor} ${report.overallScore * 3.6}deg, var(--bg-tertiary) 0deg)` }}>
        <div style={{ width: 150, height: 150, borderRadius: '50%', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <div className="ats-score-num" style={{ color: scoreColor }}>{report.overallScore}%</div>
          <div className="ats-score-label">Match Score</div>
        </div>
      </div>

      {/* Keywords */}
      <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', padding: 24, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>🔑 Keyword Analysis</h3>
        <div style={{ marginBottom: 12, fontSize: 13, fontWeight: 600, color: 'var(--success)' }}>✅ Matched ({report.keywordMatch.matched.length})</div>
        <div className="ats-keywords">
          {report.keywordMatch.matched.map(k => <span key={k} className="ats-keyword matched">{k}</span>)}
        </div>
        <div style={{ marginTop: 16, marginBottom: 12, fontSize: 13, fontWeight: 600, color: 'var(--danger)' }}>❌ Missing ({report.keywordMatch.missing.length})</div>
        <div className="ats-keywords">
          {report.keywordMatch.missing.map(k => <span key={k} className="ats-keyword missing">{k}</span>)}
        </div>
        <div style={{ marginTop: 16, marginBottom: 12, fontSize: 13, fontWeight: 600, color: 'var(--warning)' }}>⚠️ Partial ({report.keywordMatch.partial.length})</div>
        <div className="ats-keywords">
          {report.keywordMatch.partial.map(k => <span key={k} className="ats-keyword partial">{k}</span>)}
        </div>
      </div>

      {/* Skill Gaps */}
      <div style={{ background: 'var(--bg-card)', border: 'var(--border-glass)', borderRadius: 'var(--radius-lg)', padding: 24, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>🎯 Skill Gaps → Recommended Cards</h3>
        <div className="gap-list">
          {report.skillGaps.map(gap => (
            <div key={gap.skill} className="gap-item">
              <div className="gap-skill">{gap.skill}</div>
              <span className={`gap-priority ${gap.priority}`}>{gap.priority}</span>
            </div>
          ))}
        </div>
      </div>

      <button className="btn-primary" style={{ width: '100%', padding: 16, fontSize: 16 }} onClick={onStartMission}>
        🎯 Start Interview Mission (14-day Sprint)
      </button>
    </div>
  );
}
