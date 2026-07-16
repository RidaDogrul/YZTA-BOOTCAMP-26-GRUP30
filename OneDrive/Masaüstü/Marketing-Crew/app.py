import streamlit as st
from datetime import datetime
from marketing-crew.crew import TheMarketingCrew
import os
from pathlib import Path

# Sayfa yapılandırması
st.set_page_config(
    page_title="AI Marketing Crew",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ile özel stil
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 10px;
        border: none;
        font-size: 1.1rem;
    }
    .stButton>button:hover {
        opacity: 0.8;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Başlık
st.markdown('<h1 class="main-header">🎯 AI Marketing Crew</h1>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #666; font-size: 1.2rem; margin-bottom: 2rem;">
    Yapay Zeka Destekli Tam Kapsamlı Marketing Otomasyonu
</div>
""", unsafe_allow_html=True)

# Sidebar - API Key Kontrolü
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # API Key kontrolü
    api_key_input = st.text_input(
        "🔑 Google Gemini API Key",
        type="password",
        help="Gemini API key'inizi Hugging Face Secrets'tan otomatik alınır, yoksa buraya girebilirsiniz"
    )
    
    # Hugging Face Secrets'tan veya kullanıcı girişinden API key al
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
    elif "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    
    # SerperDev API Key (opsiyonel)
    serper_key = st.text_input(
        "🔍 SerperDev API Key (Opsiyonel)",
        type="password",
        help="Web araması için SerperDev API key"
    )
    if serper_key:
        os.environ["SERPER_API_KEY"] = serper_key
    elif "SERPER_API_KEY" in st.secrets:
        os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
    
    st.divider()
    
    st.markdown("""
    ### 📚 Proje Hakkında
    Bu uygulama CrewAI kullanarak:
    - 📊 Pazar araştırması
    - 🎯 Marketing stratejisi
    - 📅 İçerik takvimi
    - ✍️ Sosyal medya postları
    - 📝 Blog yazıları
    - 🔍 SEO optimizasyonu
    
    oluşturur.
    """)
    
    st.divider()
    st.markdown("Made with ❤️ using [CrewAI](https://crewai.com)")

# Ana içerik
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Proje Bilgileri")
    
    product_name = st.text_input(
        "Ürün/Hizmet Adı",
        placeholder="örn: AI Destekli Excel Otomasyon Aracı",
        help="Pazarlamak istediğiniz ürün veya hizmetin adı"
    )
    
    product_description = st.text_area(
        "Ürün Açıklaması",
        placeholder="Ürününüz veya hizmetiniz hakkında detaylı bilgi...",
        help="Ürününüzün ne yaptığını, hangi problemi çözdüğünü açıklayın",
        height=120
    )
    
    target_audience = st.text_input(
        "Hedef Kitle",
        placeholder="örn: Küçük ve Orta Ölçekli İşletmeler (KOBİ)",
        help="Ürününüzün hedef kitlesi kimler?"
    )
    
    budget = st.text_input(
        "Bütçe",
        placeholder="örn: $50,000",
        help="Marketing kampanyanız için ayrılan bütçe"
    )

with col2:
    st.header("🎨 Özellikler")
    st.markdown("""
    <div class="info-box">
    <h4>🤖 AI Ajanlar</h4>
    <ul>
        <li>👨‍💼 Marketing Başkanı</li>
        <li>🎨 İçerik Yaratıcı</li>
        <li>✍️ Blog Yazarı</li>
        <li>🔍 SEO Uzmanı</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h4>📦 Çıktılar</h4>
    <ul>
        <li>📊 Pazar Araştırması Raporu</li>
        <li>🎯 Marketing Stratejisi</li>
        <li>📅 İçerik Takvimi</li>
        <li>📱 Sosyal Medya Postları</li>
        <li>📝 Blog Yazıları</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Çalıştırma butonu
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    run_crew = st.button("🚀 Marketing Crew'yu Çalıştır", use_container_width=True)

# Crew çalıştırma
if run_crew:
    # Validasyon
    if not product_name or not product_description or not target_audience or not budget:
        st.error("❌ Lütfen tüm alanları doldurun!")
    elif "GEMINI_API_KEY" not in os.environ:
        st.error("❌ Lütfen Gemini API Key'inizi girin!")
    else:
        try:
            with st.spinner("🤖 AI Marketing Crew çalışıyor... Bu birkaç dakika sürebilir."):
                
                # İlerleme göstergesi
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Input hazırlama
                inputs = {
                    "product_name": product_name,
                    "target_audience": target_audience,
                    "product_description": product_description,
                    "budget": budget,
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                }
                
                # Crew'yu çalıştır
                status_text.text("📊 Marketing Crew başlatılıyor...")
                progress_bar.progress(10)
                
                crew = TheMarketingCrew()
                
                status_text.text("🔍 Pazar araştırması yapılıyor...")
                progress_bar.progress(30)
                
                result = crew.marketingcrew().kickoff(inputs=inputs)
                
                progress_bar.progress(100)
                status_text.text("✅ Tamamlandı!")
                
                # Başarı mesajı
                st.success("🎉 Marketing içerikleri başarıyla oluşturuldu!")
                
                # Sonuçları göster
                st.header("📊 Sonuçlar")
                
                # Resources klasöründeki dosyaları göster
                drafts_path = Path("marketing-crew/resources/drafts")
                
                if drafts_path.exists():
                    # Tabs ile kategorize et
                    tab1, tab2, tab3, tab4 = st.tabs(["📄 Raporlar", "📱 Sosyal Medya", "📝 Bloglar", "🗂️ Tüm Dosyalar"])
                    
                    with tab1:
                        st.subheader("📊 Marketing Raporları")
                        
                        # Ana raporlar
                        report_files = ["market_research_report.md", "marketing_strategy.md", "content_calendar.md"]
                        for report in report_files:
                            report_path = drafts_path / report
                            if report_path.exists():
                                with st.expander(f"📄 {report.replace('_', ' ').title().replace('.md', '')}"):
                                    content = report_path.read_text(encoding='utf-8')
                                    st.markdown(content)
                                    st.download_button(
                                        label=f"⬇️ İndir",
                                        data=content,
                                        file_name=report,
                                        mime="text/markdown",
                                        key=f"download_{report}"
                                    )
                    
                    with tab2:
                        st.subheader("📱 Sosyal Medya Postları")
                        posts_path = drafts_path / "posts"
                        
                        if posts_path.exists():
                            # Platform bazında grupla
                            platforms = {"instagram": "📸 Instagram", "linkedin": "💼 LinkedIn", 
                                       "twitter": "🐦 Twitter", "facebook": "📘 Facebook"}
                            
                            for platform, icon_name in platforms.items():
                                platform_posts = list(posts_path.glob(f"*{platform}*.md"))
                                if platform_posts:
                                    st.markdown(f"### {icon_name}")
                                    for post in platform_posts:
                                        with st.expander(f"📝 {post.stem}"):
                                            content = post.read_text(encoding='utf-8')
                                            st.markdown(content)
                                            st.download_button(
                                                label="⬇️ İndir",
                                                data=content,
                                                file_name=post.name,
                                                mime="text/markdown",
                                                key=f"download_{post.name}"
                                            )
                    
                    with tab3:
                        st.subheader("📝 Blog İçerikleri")
                        blog_files = list(posts_path.glob("*blog*.md")) if posts_path.exists() else []
                        
                        if blog_files:
                            for blog in blog_files:
                                with st.expander(f"📝 {blog.stem}"):
                                    content = blog.read_text(encoding='utf-8')
                                    st.markdown(content)
                                    st.download_button(
                                        label="⬇️ İndir",
                                        data=content,
                                        file_name=blog.name,
                                        mime="text/markdown",
                                        key=f"download_{blog.name}"
                                    )
                        else:
                            st.info("📝 Blog içerikleri henüz oluşturulmadı.")
                    
                    with tab4:
                        st.subheader("🗂️ Tüm Oluşturulan Dosyalar")
                        all_files = list(drafts_path.rglob("*.md"))
                        st.info(f"Toplam {len(all_files)} dosya oluşturuldu.")
                        
                        for file in all_files:
                            st.text(f"📄 {file.relative_to(drafts_path)}")
                
        except Exception as e:
            st.error(f"❌ Bir hata oluştu: {str(e)}")
            st.exception(e)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p>🤖 Bu uygulama <strong>CrewAI</strong> ve <strong>Google Gemini</strong> kullanılarak geliştirilmiştir.</p>
    <p>📧 Sorularınız için: <a href="https://huggingface.co/spaces">Hugging Face Spaces</a></p>
</div>
""", unsafe_allow_html=True)
