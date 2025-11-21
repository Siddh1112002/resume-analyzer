import React, { useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const SAMPLE_FILE_PATH_UNIX = "/mnt/data/Siddhant_Hulle_Resume.pdf";
const SAMPLE_FILE_PATH_WINDOWS = "C:\\projects\\resume-analyzer\\backend\\uploads\\Siddhant_Hulle_Resume.pdf";

export default function App() {
  const [file, setFile] = useState(null);
  const [pdfId, setPdfId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [jobText, setJobText] = useState("");
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
  }, []);

  function onFileChange(e) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setPdfId(null);
    setAnalysis(null);
  }

async function uploadFile() {
  if (!file) {
    alert("Please select a PDF file first.");
    return;
  }

  setUploading(true);

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("job_description", jobText || "");

    const res = await fetch(`${API}/upload`, {
      method: "POST",
      body: formData,
   
    });

    if (!res.ok) {
      const txt = await res.text();
      throw new Error(txt);
    }

    const data = await res.json();
    console.log("UPLOAD RESPONSE:", data);

    setPdfId(data.pdf_id);
    setAnalysis(null);

  } catch (err) {
    alert("Upload failed: " + (err.message || err));
  } finally {
    setUploading(false);
  }
}


  async function runAnalysis(force = false) {
    setAnalyzing(true);
    try {
      const payload = pdfId
        ? { pdf_id: pdfId, job_description: jobText || "", force }
        : { file_path: SAMPLE_FILE_PATH_UNIX, job_description: jobText || "", force };

      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(await res.text());
      const j = await res.json();
      setAnalysis(j);

      setTimeout(() => {
        const center = document.querySelector(".panel.center");
        if (center) center.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 60);
    } catch (err) {
      alert("Analysis failed: " + (err.message || err));
    } finally {
      setAnalyzing(false);
    }
  }

  function getATSScore() {
    try {
      return analysis?.analysis?.ats_score ?? 0;
    } catch {
      return 0;
    }
  }

  function _loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) return resolve();
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("Failed to load " + src));
      document.head.appendChild(s);
    });
  }

  async function downloadPDF() {
    if (!analysis) {
      alert("Run an analysis first to generate a report.");
      return;
    }


    try {
      await _loadScript("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
    } catch (err) {
      alert("Failed to load PDF library: " + err.message);
      return;
    }

    try {
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ unit: "pt", format: "a4" });

 
      const pageWidth = doc.internal.pageSize.getWidth();
      const margin = 40;
      const contentWidth = pageWidth - margin * 2;
      let y = 48;

      const wrap = (text, maxWidth, options = {}) => doc.splitTextToSize(String(text || ""), maxWidth, options);

      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(230, 230, 230);
      doc.setFontSize(18);
      doc.setFont("helvetica", "bold");
      doc.text("Resume Analysis Report", margin, y);
      y += 20;

      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(100);
      doc.text(`Generated: ${new Date().toLocaleString()}`, margin, y);
      y += 18;

  
      doc.setDrawColor(230, 230, 230);
      doc.setLineWidth(0.6);
      doc.line(margin, y, pageWidth - margin, y);
      y += 18;


      const ats = analysis?.analysis?.ats_score ?? 0;
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text("ATS Score", margin, y);

      
      doc.setFontSize(26);
      doc.setTextColor("#333333");
      doc.text(String(ats), pageWidth - margin - 20 - doc.getTextWidth(String(ats)), y - 8);

      y += 18;

 
      const barX = margin;
      const barY = y;
      const barW = contentWidth;
      const barH = 12;


      doc.setFillColor(240, 240, 245);
      doc.roundedRect(barX, barY, barW, barH, 6, 6, "F");
      const fillW = Math.max(2, Math.min(1, ats / 100) * barW);
      doc.setFillColor(99, 56, 255); // purple-ish
      doc.roundedRect(barX, barY, fillW, barH, 6, 6, "F");

      y += barH + 18;
  
      const missing = (analysis?.analysis?.missing_skills_job || []).join(", ") || "None";
      doc.setFontSize(11);
      doc.setTextColor("#444");
      doc.setFont("helvetica", "bold");
      doc.text("Missing:", margin, y);
      doc.setFont("helvetica", "normal");
      doc.text(missing, margin + 60, y);
      y += 22;

      doc.setFontSize(14);
      doc.setFont("helvetica", "bold");
      doc.text("Actionable suggestions", margin, y);
      y += 14;

      doc.setFontSize(11);
      doc.setFont("helvetica", "normal");
      const suggestions = analysis?.analysis?.suggestions || [];
      if (suggestions.length === 0) {
        const t = wrap("No suggestions available.", contentWidth);
        doc.text(t, margin, y);
        y += t.length * 14 + 8;
      } else {
     
        for (let i = 0; i < suggestions.length; i++) {
          const idx = i + 1;
          const item = suggestions[i];
          const num = `${idx}. `;
          const lines = wrap(item, contentWidth - 30);
 
          doc.setFont("helvetica", "bold");
          doc.text(num, margin, y);
          doc.setFont("helvetica", "normal");
          doc.text(lines, margin + 22, y);
          y += lines.length * 14 + 8;

          
          if (y > doc.internal.pageSize.getHeight() - 80) {
            doc.addPage();
            y = 40;
          }
        }
      }

      y += 8;

      doc.setFontSize(13);
      doc.setFont("helvetica", "bold");
      doc.text("Technical skills", margin, y);
      y += 16;

      const skills = analysis?.analysis?.skills_found || [];
      const chipPaddingX = 8;
      const chipPaddingY = 4;
      const chipGap = 8;
      let cx = margin;
      let cy = y;

      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      for (let i = 0; i < skills.length; i++) {
        const s = String(skills[i]);
        const w = doc.getTextWidth(s) + chipPaddingX * 2;

        if (cx + w > pageWidth - margin) {
          cx = margin;
          cy += 22;
        }
      
        doc.setDrawColor(220);
        doc.setFillColor(245, 245, 250);
        doc.roundedRect(cx, cy - 10, w, 18, 6, 6, "F");
   
        doc.setTextColor("#222");
        doc.text(s, cx + chipPaddingX, cy + 2);
        cx += w + chipGap;
      }
      y = cy + 26;

      doc.setFontSize(13);
      doc.setFont("helvetica", "bold");
      doc.text("Soft skills", margin, y);
      y += 16;

      const soft = analysis?.analysis?.soft_skills_found || [];
      cx = margin;
      cy = y;
      doc.setFontSize(10);
      for (let i = 0; i < soft.length; i++) {
        const s = String(soft[i]);
        const w = doc.getTextWidth(s) + chipPaddingX * 2;
        if (cx + w > pageWidth - margin) {
          cx = margin;
          cy += 22;
        }
        doc.setFillColor(255, 243, 205); 
        doc.roundedRect(cx, cy - 10, w, 18, 6, 6, "F");
        doc.setTextColor("#3a2e00");
        doc.text(s, cx + chipPaddingX, cy + 2);
        cx += w + chipGap;
      }
      y = cy + 26;

      const preview = (analysis?.analysis?.raw_text_preview || "").substring(0, 1400);
      if (preview) {
        doc.setFontSize(13);
        doc.setFont("helvetica", "bold");
        doc.text("Resume preview (truncated)", margin, y);
        y += 16;
        doc.setFontSize(10);
        doc.setFont("helvetica", "normal");
        const previewLines = wrap(preview, contentWidth);
  
        for (let i = 0; i < previewLines.length; i++) {
          if (y > doc.internal.pageSize.getHeight() - 60) {
            doc.addPage();
            y = 48;
          }
          doc.text(previewLines[i], margin, y);
          y += 12;
        }
      }


      const footerY = doc.internal.pageSize.getHeight() - 28;
      doc.setFontSize(9);
      doc.setTextColor(120);
      doc.text("Generated by Resume Analyzer", margin, footerY);


      doc.save("resume-analysis.pdf");
    } catch (err) {
      console.error("PDF generation error:", err);
      alert("Could not generate PDF: " + (err.message || err));
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1 className="brand">Resume Analyzer</h1>
          {}
        </div>
      </header>

      <main className="layout">
        <aside className="panel left">
          <h3>Resume & Job Details</h3>

          <label className="fileLabel">Upload resume (PDF)</label>
          <div className="fileRow">
            <input type="file" accept="application/pdf" onChange={onFileChange} />
            <button className="btn primary" onClick={uploadFile} disabled={uploading}>
              {uploading ? "Uploading…" : "Upload"}
            </button>
          </div>

          <div className="pdfId" style={{ marginTop: 8 }}>
            {pdfId ? <><strong>Uploaded:</strong> {pdfId}</> : file ? <span>Ready to upload: {file.name}</span> : <em>No file selected</em>}
            <div style={{ marginTop: 8 }}>
              <a href={"file:///C:/projects/resume-analyzer/backend/uploads/"} target="_blank" rel="noreferrer">Open sample folder</a>
            </div>
          </div>

          <label className="jdLabel" style={{ marginTop: 12 }}>Job description (optional)</label>
          <textarea
            placeholder="Paste job description (optional)"
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
          />

          <div className="actions" style={{ marginTop: 12 }}>
            <button className="btn primary" onClick={() => runAnalysis(false)} disabled={analyzing}>
              {analyzing ? "Analyzing…" : "Run analysis"}
            </button>

            <button className="btn" onClick={() => { setFile(null); setPdfId(null); setJobText(""); setAnalysis(null); }}>
              Reset
            </button>

            <button className="btn" onClick={downloadPDF}>
              Download PDF
            </button>
          </div>

          <div className="hint" style={{ marginTop: 12 }}>
            Tip: Upload your resume for best results.
          </div>
        </aside>

        <section className="panel center">
          <div className="ats" style={{ alignItems: "flex-start" }}>
            <div className="atsBox">
              <div className="atsValue">{getATSScore()}</div>
              <div className="atsLabel">ATS Score</div>
            </div>

            <div className="progressArea" style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ fontWeight: 700 }}>Missing:</div>
                <div style={{ color: "var(--muted)" }}>
                  {analysis?.analysis?.missing_skills_job?.length ? analysis.analysis.missing_skills_job.join(", ") : "None"}
                </div>
              </div>

              <div style={{ marginTop: 8 }}>
                <div className="progressBar">
                  <div className="progressFill" style={{ width: `${Math.min(100, getATSScore())}%` }} />
                </div>
              </div>
            </div>
          </div>

          <div className="suggestions" style={{ marginTop: 14 }}>
            <h4>Actionable suggestions</h4>
            {analysis?.analysis?.suggestions?.length ? (
              <ol>
                {analysis.analysis.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            ) : (
              <div className="noSuggestions">No suggestions yet — run an analysis to see targeted feedback.</div>
            )}
          </div>
        </section>

        <aside className="panel right">
          <h3>Skills</h3>
          <div className="badges" style={{ marginBottom: 10 }}>
            {(analysis?.analysis?.skills_found || []).map((s, i) => <span key={i} className="pill">{s}</span>)}
            {!((analysis?.analysis?.skills_found || []).length) && <div className="noSkills">No skills detected yet.</div>}
          </div>

          <h4>Soft skills</h4>
          <div className="soft">
            {(analysis?.analysis?.soft_skills_found || []).map((s, i) => <span key={i} className="pill softpill">{s}</span>)}
            {!((analysis?.analysis?.soft_skills_found || []).length) && <div className="noSkills">None detected</div>}
          </div>
        </aside>
      </main>
    </div>
  );
}
