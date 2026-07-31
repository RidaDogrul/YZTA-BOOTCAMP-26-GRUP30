/**
 * i18n.js — Internationalization (Türkçe/İngilizce)
 */

const TRANSLATIONS = {
  tr: {
    "auth.login": "Giriş Yap",
    "auth.login_do": "Giriş yapın",
    "auth.login_sub": "Nexus Analytics hesabınıza giriş yapın",

    // Connection
    "connection.waiting": "Bağlantı bekleniyor",
    "connection.connected": "bağlı",
    "connection.disconnected": "bağlantı kesildi",
    "connection.source_connected": "{source} bağlı",
    
    // Sidebar
    "sidebar.data_source": "Veri Kaynağı",
    "sidebar.close": "Paneli kapat",
    "sidebar.open": "Paneli aç",
    
    // Source types
    "source.postgresql": "PostgreSQL",
    "source.mysql": "MySQL",
    "source.mongodb": "MongoDB",
    "source.s3": "☁ S3",
    "source.snowflake": "❄ Snowflake",
    
    // Connection form
    "form.connection_url": "Bağlantı URL",
    "form.mongodb_uri": "MongoDB URI",
    "form.bucket": "Bucket",
    "form.access_key": "Access Key ID",
    "form.secret_key": "Secret Access Key",
    "form.region": "Region",
    "form.account": "Account",
    "form.user": "Kullanıcı",
    "form.password": "Parola",
    "form.database": "Veritabanı",
    "form.schema": "Şema",
    "form.warehouse": "Warehouse",
    "form.role": "Rol",
    
    // Buttons
    "btn.test_connection": "Test Et",
    "btn.connect": "Bağlan",
    "btn.disconnect": "Bağlantıyı Kes",
    "btn.refresh_schema": "Yenile",
    "btn.clear_history": "Geçmişi Temizle",
    "btn.clear_chat": "Sohbeti Temizle",
    "btn.send": "Gönder",
    "btn.cancel": "İptal",
    "btn.connect_add": "Bağlan & Ekle",
    "btn.generate_report": "Rapor Oluştur",
    "btn.close": "Kapat",
    
    // Merge panel
    "merge.connected_sources": "BAĞLI KAYNAKLAR & TABLO SEÇİMİ",
    "merge.add_source": "Kaynak Ekle",
    "merge.add_source_title": "Yeni veri kaynağı ekle",
    "merge.run_merge": "Tüm Kaynaklarla Sorgula",
    "merge.query_text": "{sources} kaynaklarındaki verileri karşılaştır ve özet analiz yap",
    "merge.all_tables": "Tüm tablolar",
    "merge.selected_count": "seçili",
    "merge.select_all": "Tümünü Seç",
    "merge.clear": "Temizle",
    "merge.no_tables": "Bu kaynakta tablo bulunamadı.",
    "merge.schema_not_loaded": "Şema henüz yüklenmedi.",
    "merge.schema_loading": "Şema yükleniyor…",
    "merge.remove_source": "Kaynağı kaldır",
    "merge.show_tables": "Tabloları göster",
    "merge.remove": "Kaldır",
    "merge.schema_load_error": "Şema yüklenemedi: {error}",
    "merge.hint": "Her kaynağı genişletip hangi tabloların sorgulanacağını seçin. İkinci kaynak eklemek için <strong>Kaynak Ekle</strong>'ye tıklayın.",
    
    // Add source form
    "add_source.alias": "Kaynak Adı",
    "add_source.connect_add": "Bağlan & Ekle",
    "add_source.title": "Yeni Veri Kaynağı Bağla",
    "add_source.type": "Kaynak Türü",
    "add_source.no_types": "Eklenebilecek başka kaynak tipi yok.",
    "add_source.connecting": "Bağlanıyor…",
    "add_source.missing_info": "Eksik bilgi",
    "add_source.source_added": "Kaynak eklendi",
    "add_source.add_error": "Kaynak eklenemedi",
    "add_source.no_type_selected": "Kaynak tipi seçilmedi.",
    "add_source.unknown_type": "Bilinmeyen kaynak tipi: {type}",
    
    // Chat
    "chat.placeholder": "Verileriniz hakkında herhangi bir şey sorun…",
    "chat.placeholder_disconnected": "Veri kaynağınız hakkında bir şey sorun…",
    "chat.empty_state": "Henüz bir soru sormadınız. Veri kaynağına bağlandıktan sonra analiz yapabilirsiniz.",
    "chat.typing": "Analiz ediliyor",
    
    // Processing steps
    "proc.schema": "Şema okunuyor",
    "proc.sql": "Sorgu oluşturuluyor",
    "proc.execute": "Veri çekiliyor",
    "proc.clean": "Veri temizleniyor",
    "proc.insight": "Analiz hazırlanıyor",
    
    // Response
    "response.sql_query": "SQL Sorgusu",
    "response.copy": "📋 Kopyala",
    "response.copied": "✅ Kopyalandı",
    "response.chart": "📊 Veri Görselleştirme",
    "response.action_plan": "💡 Önerilen Adımlar — Tıklayarak Uygula",
    "response.report_link": "🔗 Rapor Linki",
    
    // Toast
    "toast.connect_success": "Bağlandı",
    "toast.connect_error": "Bağlantı hatası",
    "toast.disconnect_success": "Bağlantı kesildi",
    "toast.source_added": "Kaynak eklendi",
    "toast.source_removed": "Kaynak kaldırıldı",
    "toast.error": "Hata",
    "toast.warning": "Uyarı",
    "toast.info": "Bilgi",
    "toast.connect_first": "Önce bağlanın",
    "toast.connect_required": "Bir veri kaynağına bağlanmadan analiz yapılamaz.",
    "toast.remove_failed": "Kaldırılamadı",
    "toast.merge_ready": "Birleştirme hazır",
    "toast.merge_ready_message": "Gönder tuşuna basarak çoklu kaynak analizini başlatın.",
    
    // Session info
    "session.id": "Oturum:",
    "session.connected_sources": "Bağlı Kaynaklar",

    // Data search
    "data.search.placeholder": "Verilerde ara… (tablo, sütun, değer)",

    // App
    "app.title": "Veri Analiz Platformu",
    
    // Welcome
    "welcome.title": "Verinizi anlamlandırın",
    "welcome.desc": "Sol panelden bir veri kaynağı bağlayın, ardından verileriniz hakkında herhangi bir soru sorun — tablo yapısı, trendler, özetler.",
    
    // Input
    "input.footer": "Enter → gönder · Shift+Enter → yeni satır",
    
    // Suggestions
    "suggestion.tables": "Hangi tablolar mevcut ve kaç kayıt var?",
    "suggestion.sales_summary": "Son 30 günün satış özetini çıkar",
    "suggestion.avg_order": "Müşteri başına ortalama sipariş değeri nedir?",
    "suggestion.top_categories": "En yüksek gelir getiren kategorileri listele",
    
    // Modal
    "modal.share_report_title": "Rapor Paylaşım Ayarları",
    "modal.share_emails": "Email Adresleri (virgülle ayırın)",
    "modal.make_public": "Raporu herkese açık yap",
    
    // Report
    "report.success_title": "Raporunuz başarıyla oluşturuldu",
    "report.share_link": "Paylaşım Linki:",
  },
  en: {
    "auth.login": "Log In",
    "auth.login_do": "Log in",
    "auth.login_sub": "Log in to your Nexus Analytics account",
    
    // Connection
    "connection.waiting": "Waiting for connection",
    "connection.connected": "connected",
    "connection.disconnected": "disconnected",
    "connection.source_connected": "{source} connected",
    
    // Sidebar
    "sidebar.data_source": "Data Source",
    "sidebar.close": "Close panel",
    "sidebar.open": "Open panel",
    
    // Source types
    "source.postgresql": "PostgreSQL",
    "source.mysql": "MySQL",
    "source.mongodb": "MongoDB",
    "source.s3": "☁ S3",
    "source.snowflake": "❄ Snowflake",
    
    // Connection form
    "form.connection_url": "Connection URL",
    "form.mongodb_uri": "MongoDB URI",
    "form.bucket": "Bucket",
    "form.access_key": "Access Key ID",
    "form.secret_key": "Secret Access Key",
    "form.region": "Region",
    "form.account": "Account",
    "form.user": "User",
    "form.password": "Password",
    "form.database": "Database",
    "form.schema": "Schema",
    "form.warehouse": "Warehouse",
    "form.role": "Role",
    
    // Buttons
    "btn.test_connection": "Test Connection",
    "btn.connect": "Connect",
    "btn.disconnect": "Disconnect",
    "btn.refresh_schema": "Refresh Schema",
    "btn.clear_history": "Clear History",
    "btn.clear_chat": "Clear Chat",
    "btn.send": "Send",
    "btn.cancel": "Cancel",
    "btn.connect_add": "Connect & Add",
    "btn.generate_report": "Generate Report",
    "btn.close": "Close",
    
    // Merge panel
    "merge.connected_sources": "CONNECTED SOURCES & TABLE SELECTION",
    "merge.add_source": "Add Source",
    "merge.add_source_title": "Add new data source",
    "merge.run_merge": "Query All Sources",
    "merge.query_text": "Compare and analyze data from {sources} sources",
    "merge.all_tables": "All tables",
    "merge.selected_count": "selected",
    "merge.select_all": "Select All",
    "merge.clear": "Clear",
    "merge.no_tables": "No tables found in this source.",
    "merge.schema_not_loaded": "Schema not loaded yet.",
    "merge.schema_loading": "Loading schema…",
    "merge.remove_source": "Remove source",
    "merge.show_tables": "Show tables",
    "merge.remove": "Remove",
    "merge.schema_load_error": "Failed to load schema: {error}",
    "merge.hint": "Expand each source to select which tables to query. Click <strong>Add Source</strong> to add a second source.",
    
    // Add source form
    "add_source.alias": "Source Alias",
    "add_source.connect_add": "Connect & Add",
    "add_source.title": "Connect New Data Source",
    "add_source.type": "Source Type",
    "add_source.no_types": "No other source types available.",
    "add_source.connecting": "Connecting…",
    "add_source.missing_info": "Missing information",
    "add_source.source_added": "Source added",
    "add_source.add_error": "Could not add source",
    "add_source.no_type_selected": "No source type selected.",
    "add_source.unknown_type": "Unknown source type: {type}",
    
    // Chat
    "chat.placeholder": "Ask anything about your data…",
    "chat.placeholder_disconnected": "Ask anything about your data source…",
    "chat.empty_state": "You haven't asked a question yet. You can analyze data after connecting to a data source.",
    "chat.typing": "Analyzing",
    
    // Processing steps
    "proc.schema": "Reading schema",
    "proc.sql": "Generating query",
    "proc.execute": "Fetching data",
    "proc.clean": "Cleaning data",
    "proc.insight": "Preparing analysis",
    
    // Response
    "response.sql_query": "SQL Query",
    "response.copy": "📋 Copy",
    "response.copied": "✅ Copied",
    "response.chart": "📊 Data Visualization",
    "response.action_plan": "💡 Suggested Actions — Click to Apply",
    "response.report_link": "🔗 Report Link",
    
    // Toast
    "toast.connect_success": "Connected",
    "toast.connect_error": "Connection error",
    "toast.disconnect_success": "Disconnected",
    "toast.source_added": "Source added",
    "toast.source_removed": "Source removed",
    "toast.error": "Error",
    "toast.warning": "Warning",
    "toast.info": "Info",
    "toast.connect_first": "Connect first",
    "toast.connect_required": "Analysis cannot be performed without connecting to a data source.",
    "toast.remove_failed": "Could not remove",
    "toast.merge_ready": "Merge ready",
    "toast.merge_ready_message": "Press send to start multi-source analysis.",
    
    // Session info
    "session.id": "Session:",
    "session.connected_sources": "Connected Sources",

    // Data search
    "data.search.placeholder": "Search data… (table, column, value)",

    // App
    "app.title": "Data Analytics Platform",
    
    // Welcome
    "welcome.title": "Make sense of your data",
    "welcome.desc": "Connect a data source from the left panel, then ask any question about your data — table structure, trends, summaries.",
    
    // Input
    "input.footer": "Enter → send · Shift+Enter → new line",
    
    // Suggestions
    "suggestion.tables": "Which tables are available and how many records do they have?",
    "suggestion.sales_summary": "Get sales summary for the last 30 days",
    "suggestion.avg_order": "What is the average order value per customer?",
    "suggestion.top_categories": "List the highest revenue generating categories",
    
    // Modal
    "modal.share_report_title": "Report Sharing Settings",
    "modal.share_emails": "Email Addresses (comma separated)",
    "modal.make_public": "Make report publicly accessible",
    
    // Report
    "report.success_title": "Your report has been successfully created",
    "report.share_link": "Share Link:",
  }
};

let currentLang = localStorage.getItem("nexus_lang") || "tr";

function setLanguage(lang) {
  if (!["tr", "en"].includes(lang)) return;
  currentLang = lang;
  localStorage.setItem("nexus_lang", lang);
  updateUIText();
  updateLangLabel();
}

function getLanguage() {
  return currentLang;
}

function t(key, params = {}) {
  let text = TRANSLATIONS[currentLang][key] || key;
  // Replace {param} placeholders
  Object.keys(params).forEach(param => {
    text = text.replace(`{${param}}`, params[param]);
  });
  return text;
}

function updateUIText() {
  // Update all elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      el.textContent = t(key);
    }
  });
  
  // Update placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key) {
      el.placeholder = t(key);
    }
  });
  
  // Update aria-labels
  document.querySelectorAll("[data-i18n-aria]").forEach(el => {
    const key = el.getAttribute("data-i18n-aria");
    if (key) {
      el.setAttribute("aria-label", t(key));
    }
  });

  // Update title attributes
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    const key = el.getAttribute("data-i18n-title");
    if (key) {
      el.setAttribute("title", t(key));
    }
  });
  
  // Update suggestion cards (both text and data-q)
  document.querySelectorAll("[data-i18n-q]").forEach(el => {
    const key = el.getAttribute("data-i18n-q");
    if (key) {
      const translatedText = t(key);
      el.setAttribute("data-q", translatedText);
      const textSpan = el.querySelector(".sg-text");
      if (textSpan) {
        textSpan.textContent = translatedText;
      }
    }
  });

  // Update connection label
  const connLabel = document.getElementById("connLabel");
  const connDot = document.getElementById("connDot");
  if (connLabel && connDot) {
    // Check if connected
    const isConnected = connDot.classList.contains("connected");
    if (isConnected) {
      // Extract source name from current label (e.g., "MySQL bağlı" -> "MySQL")
      const currentText = connLabel.textContent;
      const sourceName = currentText.replace(" bağlı", "").replace(" connected", "");
      if (sourceName && sourceName !== currentText) {
        connLabel.textContent = t("connection.source_connected", { source: sourceName });
      }
    } else {
      connLabel.textContent = t("connection.waiting");
    }
  }

  // Update input placeholders
  const questionInput = document.getElementById("questionInput");
  if (questionInput) {
    const isConnected = questionInput.disabled === false;
    questionInput.placeholder = isConnected ? t("chat.placeholder") : t("chat.placeholder_disconnected");
  }

  // Update merge panel if visible
  if (typeof _renderMergeSourceList === "function") {
    _renderMergeSourceList();
  }
}

function updateLangLabel() {
  const langLabel = document.getElementById("langLabel");
  const langToggle = document.getElementById("langToggle");
  if (langLabel) {
    // Buton her zaman diğer dili gösterir (değiştirme butonu gibi)
    langLabel.textContent = currentLang === "tr" ? "EN" : "TR";
  }
  if (langToggle) {
    const label = currentLang === "tr" ? "Switch to English" : "Türkçe'ye geç";
    langToggle.setAttribute("aria-label", label);
  }
}

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
  updateUIText();
  updateLangLabel();
  
  // Language toggle handler
  const langToggle = document.getElementById("langToggle");
  if (langToggle) {
    langToggle.addEventListener("click", () => {
      setLanguage(currentLang === "tr" ? "en" : "tr");
    });
  }
});
