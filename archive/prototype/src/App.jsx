import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './index.css';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './pages/Dashboard';
import StudyEngine from './pages/StudyEngine';
import Daily5 from './pages/Daily5';
import ATSScanner from './pages/ATSScanner';
import MissionMode from './pages/MissionMode';
import Achievements from './pages/Achievements';
import AdminPanel from './pages/AdminPanel';
import Landing from './pages/Landing';
import { MOCK_USER_STATS } from './data/cards';

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userStats, setUserStats] = useState(MOCK_USER_STATS);
  const [xpPopup, setXpPopup] = useState(null);

  const showXp = (amount) => {
    setXpPopup(`+${amount} XP`);
    setUserStats(s => ({ ...s, totalXp: s.totalXp + amount }));
    setTimeout(() => setXpPopup(null), 1200);
  };

  const goToCategory = (cat) => {
    setSelectedCategory(cat);
    setPage('study');
  };

  if (!isLoggedIn) return <Landing onLogin={() => setIsLoggedIn(true)} />;

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <Dashboard stats={userStats} onCategoryClick={goToCategory} onDaily5={() => setPage('daily5')} />;
      case 'study': return <StudyEngine category={selectedCategory} showXp={showXp} />;
      case 'daily5': return <Daily5 showXp={showXp} />;
      case 'ats': return <ATSScanner onStartMission={() => setPage('mission')} />;
      case 'mission': return <MissionMode showXp={showXp} />;
      case 'achievements': return <Achievements stats={userStats} />;
      case 'admin': return <AdminPanel />;
      default: return <Dashboard stats={userStats} onCategoryClick={goToCategory} onDaily5={() => setPage('daily5')} />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar page={page} setPage={setPage} stats={userStats} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-content">
        <TopBar onMenuClick={() => setSidebarOpen(!sidebarOpen)} onLanding={() => setIsLoggedIn(false)} />
        <AnimatePresence mode="wait">
          <motion.div 
            className="page-content" 
            key={page}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </div>
      {xpPopup && <div className="xp-popup">{xpPopup}</div>}
    </div>
  );
}
