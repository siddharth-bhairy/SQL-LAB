import React, { useState, useCallback } from 'react';
import { ReactFlow, Background, Controls, applyNodeChanges } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import download from 'downloadjs';

const SQLVisualizer = () => {
  const [nodes, setNodes] = useState([]);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("Ready");
  const [isError, setIsError] = useState(false);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const handleVisualize = async () => {
    setMessage("Validating...");
    setIsError(false);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const data = await response.json();
      console.log("Backend Data:", data);

      // ✅ FIX: check for errors first, then check type in lowercase
      if (data.errors) {
        setIsError(true);
        setMessage(`Error: ${data.errors.join(' | ')}`);
        return;
      }

      if (data.type === 'create') {
        const newNode = {
          id: `node-${data.tableName}-${Date.now()}`,
          data: {
            label: (
              <div className="table-node">
                <div className="table-header">{data.tableName}</div>
                {data.columns && data.columns.map((col, i) => (
                  <div key={i} className="column-row">
                    <span>{col.name}</span>
                    <span style={{ color: '#94a3b8' }}>
                      {col.type}{col.length ? `(${col.length})` : ''}
                    </span>
                  </div>
                ))}
              </div>
            ),
          },
          position: { x: Math.random() * 300, y: Math.random() * 300 },
        };
        setNodes((nds) => [...nds, newNode]);
        setMessage(`✓ Table '${data.tableName}' added successfully`);
      } else {
        // Non-CREATE statements validated but not visualised yet
        setMessage(`✓ Valid ${data.type.toUpperCase()} query`);
      }

    } catch (err) {
      console.error("Fetch Error:", err);
      setIsError(true);
      setMessage(`Connection Error: ${err.message}`);
    }
  };

  const exportImage = () => {
    toPng(document.querySelector('.react-flow'))
      .then((dataUrl) => download(dataUrl, 'schema.png'));
  };

  return (
    <div className="app-container">
      <nav className="navbar">
        <div style={{ fontWeight: 'bold', fontSize: '20px' }}>SQL LAB VISUALIZER</div>
      </nav>

      <div className="main-content">
        <aside className="sidebar">
          <label style={{ fontSize: '14px', fontWeight: 'bold' }}>SQL Editor</label>
          <textarea
            className="sql-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="CREATE TABLE example (id INT, val TEXT);"
          />
          <button className="btn btn-primary" onClick={handleVisualize}>Visualize</button>
          <button className="btn btn-success" onClick={exportImage}>Download Image</button>
        </aside>

        <main className="canvas-area">
          <ReactFlow nodes={nodes} onNodesChange={onNodesChange}>
            <Background />
            <Controls />
          </ReactFlow>
        </main>
      </div>

      <footer style={{
        padding: '5px 20px',
        background: '#f1f5f9',
        fontSize: '12px',
        borderTop: '1px solid #ddd',
        color: isError ? '#dc2626' : '#16a34a'
      }}>
        Status: {message}
      </footer>
    </div>
  );
};

export default SQLVisualizer;