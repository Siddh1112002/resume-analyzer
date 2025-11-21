import React, { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [status, setStatus] = useState("checking...");
  const [file, setFile] = useState(null);
  const [pdfId, setPdfId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [jobText, setJobText] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => { checkHealth(); }, []);

  async function checkHealth() {
    try {
      const res = await fetch(`${API}/health`);
      if (!res.ok) throw new Error("no response");
      const j = await res.json();
      setStatus(`${j.status} — ${j.message}`);
    } catch (e) {
      setStatus("backend unreachable");
    }
  }

  function onFileChange(e) {
    setFile(e.target.files?.[0] ?? null);
    setPdfId(null);
    setAnalysis(null);
  }

  async function uploadFile() {
    if (!file) { alert("Choose a PDF first."); return; }
    setUploading(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/upload`, { method:"POST", body:fd });
      if (!res.ok) throw new Error(await res.text());
      const j = await res.json();
      setPdfId(j.pdf_id);
      setAnalysis(null);
      checkHealth();
    } catch (err) {
      setError("Upload failed: " + (err.message || err));
      alert("Upload failed: " + (err.message || err));
    } finally { setUploading(false); }
  }

  async function analyzeUploaded(force=false) {
    setAnalyzing(true); setError(null);
    try {
      const payload = pdfId
        ? { pdf_id: pdfId, job_description: jobText || "", force }
        : { file_path: "${serverSamplePath}", job_description: jobText || "" };
      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const txt = await res.text().catch(()=>null);
        throw new Error(txt || res.statusText || "analysis failed");
      }
      const j = await res.json();
      setAnalysis(j);
    } catch (err) {
      setError("Analysis failed: " + (err.message || err));
      alert("Analysis failed: " + (err.message || err));
    } finally { setAnalyzing(false); }
  }

  const getATS = () => {
    try { return analysis?.analysis?.ats_score ?? 0; } catch { return 0; }
  };

  return (
    <div className="ra-root">
      <header className="ra-header">
        <div>
          <h1>Resume Analyzer — Upload & Match</h1>
          <div className="ra-sub">Backend status: <strong>{status}</strong></div>
        </div>
      </header>

      <main className="ra-main">
        <aside className="ra-panel ra-left">
          <section>
            <label className="label">Upload a PDF</label>
            <div className="upload-row">
              <input type="file" accept="application/pdf" onChange={onFileChange} />
              <button className="btn primary" onClick={uploadFile} disabled={uploading}>
                {uploading ? "Uploading…" : "Upload & Extract"}
              </button>
            </div>
            <div className="muted">Selected pdf_id: <span className="mono">{pdfId ?? "(none)"}</span></div>
          </section>

          <section>
            <label className="label">Analyze / Job Description</label>
            <textarea value={jobText} onChange={e=>setJobText(e.target.value)} placeholder="Paste job description (optional)"></textarea>
            <div className="actions">
              <button className="btn" onClick={()=>analyzeUploaded(false)} disabled={analyzing}>
                {analyzing ? "Analyzing…" : "Analyze (server sample / uploaded)"}
              </button>
              <button className="btn outline" onClick={()=>analyzeUploaded(true)} disabled={analyzing}>
                {analyzing ? "Matching…" : "Match Job Description"}
              </button>
            </div>
            <div className="hint">Tip: If no file uploaded, the server-side sample will be analyzed: <code>${serverSamplePath}</code></div>
          </section>
        </aside>

        <section className="ra-center">
          <div className="card score-card">
            <div className="score-left">
              <div className="big-score">{getATS()}</div>
              <div className="small">ATS Score</div>
            </div>
            <div className="score-right">
              <div className="progress">
                <div className="bar" style={{width: Math.min(100, getATS()) + "%"}}></div>
              </div>
              <div className="muted">Match quality</div>
              <div className="missing">Missing skills: <span className="bad">{(analysis?.analysis?.missing_skills_job?.length ? analysis.analysis.missing_skills_job.join(", ") : "None")}</span></div>
            </div>
          </div>

          <div className="card suggestions-card">
            <h3>Suggestions</h3>
            <ul>
              {(analysis?.analysis?.suggestions || []).length
                ? (analysis.analysis.suggestions.map((s,i)=> <li key={i}>{s}</li>))
                : <li className="muted">No suggestions yet — run an analysis to get tailored suggestions.</li>
              }
            </ul>
          </div>
        </section>

        <aside className="ra-panel ra-right">
          <div className="card">
            <h4>Skills found</h4>
            <div className="badges">
              {(analysis?.analysis?.skills_found || []).length
                ? analysis.analysis.skills_found.map((s,i)=> <span className="pill" key={i}>{s}</span>)
                : <div className="muted">No skills detected yet.</div>
              }
            </div>

            <h5>Soft skills</h5>
            <div className="badges">
              {(analysis?.analysis?.soft_skills_found || []).length
                ? analysis.analysis.soft_skills_found.map((s,i)=> <span className="pill soft" key={i}>{s}</span>)
                : <div className="muted">None detected</div>
              }
            </div>

            <div className="raw-toggle">
              <label><input type="checkbox" checked={showRaw} onChange={e=>setShowRaw(e.target.checked)} /> Show raw JSON (debug)</label>
            </div>
            {showRaw && <pre className="raw">{JSON.stringify(analysis || {}, null, 2)}</pre>}
          </div>
        </aside>
      </main>
    </div>
  );
}
