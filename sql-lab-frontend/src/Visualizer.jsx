import React, { useState, useCallback } from 'react';
import { ReactFlow, Background, Controls, applyNodeChanges, applyEdgeChanges } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import download from 'downloadjs';

const Visualizer = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  
  const [tableData, setTableData] = useState([]); 
  const [summary, setSummary] = useState("");
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [showSummary, setShowSummary] = useState(true); // Toggle for clutter control

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const handleVisualize = async () => {
    setError("");
    setSummary(""); 
    try {
      const response = await fetch('http://127.0.0.1:8000/api/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      
      const results = await response.json();
      const dataList = Array.isArray(results) ? results : [results];
      setTableData(dataList);

      let tempNodes = [...nodes];
      let tempEdges = [...edges];

      dataList.forEach((data) => {
        if (data.type === 'create') {
          const newNode = {
            id: data.tableName,
            data: { 
              label: (
                <div className="table-node">
                  <div className="table-header">{data.tableName.toUpperCase()}</div>
                  {data.columns.map((col, i) => (
                    <div key={i} className="column-row">
                      <span>
                        {col.name} {col.constraints.includes("PRIMARY KEY") ? "🔑" : ""}
                      </span>
                      <span style={{color: '#94a3b8'}}>{col.type}</span>
                    </div>
                  ))}
                </div>
              ) 
            },
            // Increased multiplier to spread tables out and reduce clutter
            position: { x: Math.random() * 800, y: Math.random() * 600 },
          };

          tempNodes = tempNodes.filter(n => n.id !== data.tableName);
          tempNodes.push(newNode);

          data.columns.forEach(col => {
            if (col.references && col.references.table) {
              const is1to1 = col.constraints.includes("UNIQUE") || col.constraints.includes("PRIMARY KEY");
              const edgeId = `e-${data.tableName}-${col.references.table}`;
              
              const newEdge = {
                id: edgeId,
                source: data.tableName,
                target: col.references.table,
                label: is1to1 ? "1 : 1" : "N : 1",
                animated: true,
                style: { stroke: '#dc2626', strokeWidth: 2 },
                labelStyle: { fill: '#dc2626', fontWeight: 'bold' }
              };
              
              tempEdges = tempEdges.filter(e => e.id !== edgeId);
              tempEdges.push(newEdge);
            }
          });
        }
      });

      setNodes(tempNodes);
      setEdges(tempEdges);
    } catch (err) {
      setError("Backend unreachable.");
    }
  };

  const generateSummary = async () => {
    if (tableData.length === 0) return;
    setIsSummarizing(true);
    setShowSummary(true); // Ensure box is visible when generating
    
    const tablesInfo = tableData.map(t => 
        `Table ${t.tableName} with columns: ${t.columns.map(c => c.name).join(", ")}`
    ).join(" | ");

    try {
        const response = await fetch('http://127.0.0.1:8000/api/summary/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tables_info: tablesInfo }),
        });
        const data = await response.json();
        setSummary(data.summary);
    } catch (err) {
        setSummary("Connection error.");
    }
    setIsSummarizing(false);
  };

  const exportImage = () => {
    const element = document.querySelector('.react-flow');
    toPng(element, {
        backgroundColor: '#ffffff',
        cacheBust: true,
    })
    .then((dataUrl) => {
        download(dataUrl, 'database-schema-report.png');
    })
    .catch(err => console.error(err));
  };

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setQuery("");
    setSummary("");
    setTableData([]);
  };

  return (
    <div className="checker-layout">
      <div className="editor-section">
        <h2 style={{color: 'var(--deep-black)', borderLeft: '4px solid var(--primary-red)', paddingLeft: '10px'}}>
            SCHEMA BUILDER
        </h2>
        <textarea 
          className="sql-input" 
          placeholder="Paste multiple CREATE TABLE queries here..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        
        <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
            <button className="action-btn" onClick={handleVisualize}>
                Draw All Tables
            </button>
            
            <button className="action-btn" onClick={generateSummary} style={{background: '#6366f1'}}>
                {isSummarizing ? "Summarizing..." : "Generate AI Summary"}
            </button>

            <div style={{display: 'flex', gap: '10px'}}>
                <button className="action-btn" onClick={exportImage} style={{flex: 1, background: '#10b981'}}>
                    Download PNG
                </button>
                <button className="action-btn" onClick={clearCanvas} style={{flex: 1, background: '#334155'}}>
                    Clear
                </button>
            </div>
        </div>
        {error && <p style={{color: 'var(--primary-red)', marginTop: '10px', fontSize: '14px'}}>⚠️ {error}</p>}
      </div>

      <div className="result-section" style={{background: '#fff', padding: 0, position: 'relative'}}>
        <ReactFlow 
          nodes={nodes} 
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
        >
          <Background color="#ccc" variant="dots" />
          <Controls />
          
          {/* TOGGLE BUTTON FOR CLUTTER CONTROL */}
          {summary && (
            <button 
              onClick={() => setShowSummary(!showSummary)}
              className="action-btn"
              style={{
                position: 'absolute', top: '10px', right: '10px', zIndex: 1001,
                fontSize: '10px', padding: '5px 10px', margin: 0, width: 'auto'
              }}
            >
              {showSummary ? "HIDE SUMMARY" : "SHOW SUMMARY"}
            </button>
          )}

          {/* AI SUMMARY BOX WITH PRE-WRAP AND BLUR */}
          {summary && showSummary && (
            <div className="summary-box">
                <strong style={{color: '#dc2626', display: 'block', marginBottom: '8px', letterSpacing: '1px'}}>
                  ARCHITECTURAL OVERVIEW
                </strong>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                  {summary}
                </div>
            </div>
          )}
        </ReactFlow>
      </div>
    </div>
  );
};

export default Visualizer;