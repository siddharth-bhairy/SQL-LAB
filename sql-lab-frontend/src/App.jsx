import React, { useState } from 'react';
import './index.css';
import Visualizer from './Visualizer';

const App = () => {
  const [view, setView] = useState('hub');

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="logo" style={{fontWeight: '900', letterSpacing: '2px', cursor: 'pointer'}} onClick={() => setView('hub')}>
          SQL<span style={{color: 'var(--primary-red)'}}>LAB</span>
        </div>
        <div className="nav-group">
          <button className={`nav-btn ${view === 'checker' ? 'active' : ''}`} onClick={() => setView('checker')}>
            SYNTAX CHECKER
          </button>
          <button className={`nav-btn ${view === 'visualizer' ? 'active' : ''}`} onClick={() => setView('visualizer')}>
            VISUALIZER
          </button>
        </div>
      </nav>

      {view === 'hub' && <LandingPage onNavigate={setView} />}
      {view === 'checker' && <SyntaxChecker />}
      {view === 'visualizer' && <Visualizer/>}
    </div>
  );
};

const LandingPage = ({ onNavigate }) => (
  <div className="hub-container">
    <div className="hub-header">
      <h1 style={{ color: 'var(--deep-black)', fontSize: '3rem', fontWeight: '900' }}>
        WELCOME TO <span style={{ color: 'var(--primary-red)' }}>SQL LAB PRO</span>
      </h1>
      <p style={{ color: '#64748b', fontSize: '1.2rem' }}>
        Select a module to begin your database architecture journey.
      </p>
    </div>

    <div className="banner-grid">
      <div className="banner-card" onClick={() => onNavigate('checker')}>
        <div className="banner-img checker-bg">
          <div className="banner-overlay">LAUNCH CHECKER</div>
        </div>
        <div className="banner-content">
          <h2>Syntax Checker</h2>
          <p>Analyze queries, detect reserved word conflicts, and get AI-powered fixes.</p>
        </div>
      </div>
      
      <div className="banner-card" onClick={() => onNavigate('visualizer')}>
        <div className="banner-img visual-bg">
          <div className="banner-overlay">LAUNCH VISUALIZER</div>
        </div>
        <div className="banner-content">
          <h2>Schema Builder</h2>
          <p>Transform raw SQL into interactive ER diagrams with automated relationship detection.</p>
        </div>
      </div>
    </div>
  </div>
);

const SyntaxChecker = () => {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [aiHint, setAiHint] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  // MISSING FUNCTION ADDED HERE
  const checkSyntax = async () => {
    setResult(null); // Clear previous results
    setAiHint("");   // Clear previous AI hints
    try {
      const response = await fetch('http://127.0.0.1:8000/api/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setResult({ errors: ["Backend connection failed. Is the Django server running?"] });
    }
  };

  const getHint = async () => {
    setIsThinking(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/hint/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, errors: result.errors }),
      });
      const data = await response.json();
      setAiHint(data.hint);
    } catch (err) {
      setAiHint("Connection to AI lost.");
    }
    setIsThinking(false);
  };

  return (
    <div className="checker-layout">
      <div className="editor-section">
        <h2 style={{color: 'var(--deep-black)', borderLeft: '4px solid var(--primary-red)', paddingLeft: '10px'}}>SQL EDITOR</h2>
        <textarea 
          className="sql-input" 
          placeholder="-- Type your SQL query here..."
          value={query} 
          onChange={(e) => { setQuery(e.target.value); setAiHint(""); }} 
        />
        <button className="action-btn" onClick={checkSyntax}>Analyze Query</button>
      </div>

      <div className="result-section">
        <h2 style={{color: 'var(--pure-white)', borderLeft: '4px solid var(--primary-red)', paddingLeft: '10px'}}>ANALYSIS</h2>
        <div className="result-display">
          {result ? (
            result.errors ? (
              <div>
                <h4 style={{color: 'var(--primary-red)'}}>❌ ERRORS</h4>
                <ul style={{color: '#cbd5e1', fontSize: '14px', listStyle: 'none', padding: 0}}>
                  {result.errors.map((err, i) => (
                    <li key={i} style={{padding: '5px 0', borderBottom: '1px solid #334155'}}>{err}</li>
                  ))}
                </ul>
                
                <button 
                  className="action-btn" 
                  style={{fontSize: '12px', background: '#334155', marginTop: '15px'}} 
                  onClick={getHint}
                  disabled={isThinking}
                >
                  {isThinking ? "AI IS THINKING..." : "GET AI HINT"}
                </button>

                {aiHint && (
                  <div style={{marginTop: '20px', padding: '15px', border: '1px solid var(--primary-red)', background: '#000', borderRadius: '4px'}}>
                    <p style={{color: 'var(--primary-red)', fontWeight: 'bold', margin: '0 0 10px 0'}}>AI SUGGESTION:</p>
                    <pre style={{whiteSpace: 'pre-wrap', color: '#fff', fontSize: '13px', fontFamily: 'Consolas, monospace'}}>{aiHint}</pre>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <h4 style={{color: '#4ade80'}}>✅ SYNTAX IS PERFECT</h4>
              </div>
            )
          ) : (
            <p style={{color: '#64748b'}}>Run analysis to check for errors.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;