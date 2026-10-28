import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Report() {
  const [report, setReport] = useState(null);

  useEffect(() => {
    api("/reports/me").then(setReport);
  }, []);
  async function deleteData() {
    if(confirm("delete your all ans?")) {
      await api("/reports/me", { method: "DELETE" });
      api("/reports/me").then(setReport);
    }
  }
  if (!report) return <p>Loading…</p>;
  async function retryScoring(qid){
    await api("/diagnostic/retry",{method:"POST",body:JSON.stringify({question_id:qid})})
    api("/reports/me").then(setReport);
  }
  return (
    <div className="card">
      <h2>{report.name}: {report.level}</h2>
      <p>Average score: {report.average_score}</p>
      <h3>Risks</h3>
      <ul>{report.risks.map((r) => <li key={r}>{r}</li>)}</ul>
      <h3>Next steps</h3>
      <ul>{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
          {report.unscored?.length > 0 && (
        <div>
          <p>{report.unscored.length} answer awaiting AI scoring.</p>
          <button onClick={() => retryScoring(report.unscored[0])}>Retry scoring</button>
        </div>
      )}
      <button onClick={deleteData}>Delete my data</button>
    </div>
  );
}
