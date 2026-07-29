/**
 
 * "Rapor Oluştur" butonunu, son analizi nexus_reports'a kaydedip
 * dashboard'ı açacak şekilde bağlar. app.js'in modal davranışını bastırır.
 */
(function () {
  const HISTORY_KEY = "nexus_history";  // chat geçmişi (chat.js buraya yazıyor)
  const REPORTS_KEY = "nexus_reports";  // dashboard'ın okuduğu yer

  // Geçmişten en son analiz (agent) mesajını bul
  function getLatestAnalysis() {
    let history = [];
    try { history = JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch {}

    for (let i = history.length - 1; i >= 0; i--) {
      const m = history[i];
      // Gerçek analiz mi? (hata mesajlarında chartData alanı olmaz)
      if (m.role === "agent" && Object.prototype.hasOwnProperty.call(m, "chartData")) {
        // Bu analize ait soruyu (önceki user mesajı) başlık yap
        let title = "Analiz Raporu";
        for (let j = i - 1; j >= 0; j--) {
          if (history[j].role === "user") { title = (history[j].text || "").slice(0, 60); break; }
        }
        return { analysis: m, title };
      }
    }
    return null;
  }

  // Son analizi rapor olarak kaydet ve dashboard'ı aç
  function saveAndOpenDashboard() {
    const found = getLatestAnalysis();
    if (!found) {
      alert("Önce bir analiz yapın — kaydedilecek rapor yok.");
      return;
    }

    const sourceEl = document.getElementById("sourceType");
    const report = {
      id: "rpt_" + Date.now(),
      title: found.title,
      source_type: sourceEl ? sourceEl.value : "",   // mysql / postgresql / mongodb / s3 / snowflake
      created_at: new Date().toISOString(),
      summary: found.analysis.text || "",
      chart_data: found.analysis.chartData || [],
      action_plan: found.analysis.actionPlan || [],
      sql_query: found.analysis.sql || "",
    };

    let reports = [];
    try { reports = JSON.parse(localStorage.getItem(REPORTS_KEY)) || []; } catch {}
    reports.push(report);
    localStorage.setItem(REPORTS_KEY, JSON.stringify(reports));

    window.location.href = "../dashboard/index.html";
  }

  // Butona bizim akışımızı bağla, app.js'in modalını engelle.
  // Capture aşamasında yakalayıp stopImmediatePropagation ile app.js'in
  // click dinleyicisinin çalışmasını önlüyoruz.
  function wire() {
    const btn = document.getElementById("btnGenerateReport");
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.stopImmediatePropagation();
      e.preventDefault();
      saveAndOpenDashboard();
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();