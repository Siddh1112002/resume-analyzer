import React, { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App(){
  const [status, setStatus] = useState("checking...");
  const [file, setFile] = useState(null);
  const [pdfId, setPdfId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [jobText, setJobText] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  useEffect(()=>{ checkHealth(); }, []);

  async function checkHealth(){
    try{
      const res = await fetch(`${API}/health`);
      const j = await res.json();
      setStatus(`${j.status} - ${j.message}`);
    }catch(e){
      setStatus("backend unreachable: " + e.message);
    }
  }

  function onFileChange(e){
    setFile(e.target.files?.[0] ?? null);
    setPdfId(null);
    setAnalysis(null);
  }

  async function uploadFile(){
    if(!file){ alert("Select a PDF first"); return; }
    setUploading(true);
    setError(null);
    try{
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/upload`, { method:"POST", body:fd });
      if(!res.ok){
        const txt = await res.text();
        throw new Error(txt || res.statusText);
      }
      const j = await res.json();
      setPdfId(j.pdf_id);
      setAnalysis(null);
      checkHealth();
    }catch(err){
      setError("Upload failed: " + (err.message || err));
      alert("Upload failed: " + (err.message || err));
    }finally{ setUploading(false); }
  }

  async function analyzeUploaded(force=false){
    setAnalyzing(true); setError(null);
    try{
      const payload = pdfId ? { pdf_id: pdfId, job_description: jobText || "", force } : { file_path: "/mnt/data/Siddhant_Hulle_Resume.pdf", job_description: jobText || "" };
      const res = await fetch(`${API}/analyze`, {
        method:"POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify(payload)
      });
      if(!res.ok){
        const txt = await res.text().catch(()=>null);
        throw new Error(txt || res.statusText);
      }
      const j = await res.json();
      setAnalysis(j);
    }catch(err){
      setError("Analysis failed: " + (err.message || err));
      alert("Analysis failed: " + (err.message || err));
    }finally{ setAnalyzing(false); }
  }

  const getATSScore = () => {
    try{
      return analysis?.analysis?.ats_score ?? 0;
    }catch{ return 0; }
  };

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1 className="title">Resume Analyzer</h1>
          <div className="subtitle">Simple • Professional • Deployable</div>
        </div>
        <div className="small">Backend: <strong>{status}</strong></div>
      </div>

      <div className="controls">
        <div className="column">
          <div className="uploadBox">
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <strong>Upload a PDF</strong>
              <div className="small">pdf_id: <span style={{fontWeight:600}}>{pdfId ?? "(none)"}</span></div>
            </div>

            <div style={{marginTop:12}}>
              <input className="inputFile" type="file" accept="application/pdf" onChange={onFileChange} />
              <button className="btn" onClick={uploadFile} disabled={uploading} style={{marginLeft:10}}>
                {uploading ? <span className="loader" /> : "Upload"}
              </button>
            </div>

            <div style={{marginTop:12}}>
              <strong>Job Description (optional)</strong>
              <textarea className="textarea" placeholder="Paste job description (optional)" value={jobText} onChange={(e)=>setJobText(e.target.value)} />
              <div style={{marginTop:10,display:"flex",gap:8,alignItems:"center"}}>
                <button className="btn secondary" onClick={()=>analyzeUploaded(false)} disabled={analyzing}>
                  {analyzing ? <span className="loader"/> : "Analyze"}
                </button>
                <button className="btn" onClick={()=>analyzeUploaded(true)} disabled={analyzing}>
                  {analyzing ? <span className="loader"/> : "Match JD"}
                </button>
              </div>
              <div className="small">If nothing uploaded, the server-sample resume will be analyzed.</div>
            </div>
          </div>

          {error && <div style={{marginTop:12,color:"var(--bad)"}}>Error: {error}</div>}
        </div>

        <div className="column" style={{flexBasis:520}}>
          <div className="resultWrap">
            <div className="card" style={{minWidth:180}}>
              <h4>ATS Score</h4>
              <div style={{display:"flex",alignItems:"center",gap:10}}>
                <div className="atsScore">{getATSScore()}</div>
                <div style={{flex:1}}>
                  <div className="small">Match quality</div>
                  <div style={{height:8,background:"#f1f5f9",borderRadius:8,marginTop:8}}>
                    <div style={{width: Math.min(100, getATSScore()) + "%", height:8, background:"linear-gradient(90deg,var(--accent),#4f46e5)", borderRadius:8}}></div>
                  </div>
                </div>
              </div>

              <div style={{marginTop:12}}>
                <div className="small">Missing skills (job)</div>
                <div className="missing">
                  {analysis?.analysis?.missing_skills_job?.length ? analysis.analysis.missing_skills_job.join(", ") : <em>None</em>}
                </div>
              </div>
            </div>

            <div style={{flex:1}}>
              <div className="card">
                <h4>Skills found</h4>
                <div className="badges">
                  {(analysis?.analysis?.skills_found || []).length ? (analysis.analysis.skills_found.map((s,i)=> <div key={i} className="pill">{s}</div>)) : <div className="small">No skills detected yet.</div>}
                </div>

                <div style={{marginTop:12}}>
                  <strong className="small">Soft skills</strong>
                  <div className="soft">
                    {(analysis?.analysis?.soft_skills_found || []).map((s,i)=> <div key={i} className="pill" style={{background:"#fff7ed",border:"1px solid #fde68a"}}>{s}</div>)}
                    {(!(analysis?.analysis?.soft_skills_found || []).length) && <div className="small">None detected</div>}
                  </div>
                </div>

                <div style={{marginTop:12}}>
                  <strong className="small">Top suggestions</strong>
                  <div className="small" style={{color:"#334155",marginTop:6}}>
                    {(analysis?.analysis?.suggestions || []).slice(0,5).map((s,i)=> <div key={i}>• {s}</div>)}
                    {!(analysis?.analysis?.suggestions||[]).length && <div className="small">No suggestions yet</div>}
                  </div>
                </div>

                <div className="debug" aria-live="polite">
                  <strong>Raw JSON</strong>
                  <pre style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(analysis || {}, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>

          <div className="footer">Professional UI • Easy to deploy</div>
        </div>
      </div>
    </div>
  );
}
