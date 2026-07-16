import streamlit as st
import json
from agents.career_goal_agent import CareerGoalAgent
from agents.task_scheduler_agent import TaskSchedulerAgent
from tools.suggestion_tool import SuggestionTool
from memory.user_memory import UserMemory
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Career Planner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Header styling */
    .stTitle {
        background: linear-gradient(90deg, #00d4ff, #7b2cbf);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 800 !important;
    }
    
    /* Card styling */
    .card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #00d4ff 0%, #7b2cbf 100%);
        color: white;
        border: none;
        border-radius: 30px;
        padding: 15px 40px;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 212, 255, 0.5);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.9);
        border: 2px solid rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        color: black;
        padding: 15px;
        font-size: 1.1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #00d4ff;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Success message */
    .success-box {
        background: linear-gradient(90deg, rgba(0, 255, 136, 0.1), rgba(0, 212, 255, 0.1));
        border-left: 4px solid #00ff88;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
    }
    
    /* Week card */
    .week-card {
        background: linear-gradient(135deg, rgba(123, 44, 191, 0.2), rgba(0, 212, 255, 0.2));
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(0, 212, 255, 0.3);
    }
    
    /* Task item */
    .task-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
        border-left: 3px solid #00d4ff;
    }
    
    /* Resource card */
    .resource-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(123, 44, 191, 0.3);
        transition: transform 0.3s ease;
    }
    
    .resource-card:hover {
        transform: translateY(-5px);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(0, 212, 255, 0.1);
        border-radius: 10px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'user_memory' not in st.session_state:
    st.session_state.user_memory = UserMemory()
if 'roadmap' not in st.session_state:
    st.session_state.roadmap = None
if 'schedule' not in st.session_state:
    st.session_state.schedule = None

# Sidebar
with st.sidebar:
    st.markdown("## 🎯 AI Career Planner")
    st.markdown("---")
    st.markdown("""
    ### How to Use:
    1. 📝 Enter your target profession
    2. 🗺️ Get your personalized roadmap
    3. 📅 View your weekly schedule
    4. 📚 Find learning resources
    """)
    st.markdown("---")
    
    # Number of weeks selector
    num_weeks = st.slider("📆 Schedule Duration (Weeks)", min_value=2, max_value=12, value=4)
    
    st.markdown("---")
    st.markdown("### 💾 Your Progress")
    memory = st.session_state.user_memory.get_memory()
    if memory.get("goal"):
        st.success(f"Current Goal: {memory['goal']}")
    else:
        st.info("No goal set yet")

# Main content
st.markdown("<h1 style='text-align: center; background: linear-gradient(90deg, #00d4ff, #7b2cbf); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🚀 AI Career Planner</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; font-size: 1.2rem;'>Your intelligent companion for career planning and skill development</p>", unsafe_allow_html=True)

st.markdown("---")

# Tab layout
tab1, tab2, tab3 = st.tabs(["🎯 Career Roadmap", "📅 Weekly Schedule", "📚 Resource Finder"])

with tab1:
    st.markdown("### 🎯 Define Your Career Goal")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        career_goal = st.text_input(
            "What is your target profession?",
            placeholder="e.g., Data Scientist, Full Stack Developer, UX Designer...",
            label_visibility="collapsed"
        )
    
    with col2:
        generate_btn = st.button("🚀 Generate Roadmap", use_container_width=True)
    
    if generate_btn and career_goal:
        with st.spinner("🔮 Creating your personalized career roadmap..."):
            try:
                # Update memory
                st.session_state.user_memory.update_goal(career_goal)
                
                # Generate roadmap
                goal_agent = CareerGoalAgent()
                roadmap = goal_agent.ask_career_goal(career_goal)
                st.session_state.roadmap = roadmap
                
                # Generate schedule
                scheduler = TaskSchedulerAgent(weeks=num_weeks)
                schedule = scheduler.create_schedule(roadmap)
                scheduler.save_schedule(schedule)
                st.session_state.schedule = schedule
                
                st.success("✅ Roadmap generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error generating roadmap: {str(e)}")
    
    # Display roadmap
    if st.session_state.roadmap:
        st.markdown("### 🗺️ Your Career Roadmap")
        
        roadmap = st.session_state.roadmap
        
        # Düz metin formatında göster
        st.markdown(f"""
        <div class='card'>
            {roadmap}
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("### 📅 Your Weekly Schedule")
    
    if st.session_state.schedule:
        schedule = st.session_state.schedule
        
        # Düz metin formatında göster
        st.markdown(f"""
        <div class='card'>
            {schedule}
        </div>
        """, unsafe_allow_html=True)
        
        # Download button
        st.download_button(
            label="📥 Download Schedule (TXT)",
            data=schedule,
            file_name="career_schedule.txt",
            mime="text/plain"
        )
    else:
        st.info("👆 Generate a career roadmap first to see your weekly schedule!")

with tab3:
    st.markdown("### 📚 Find Learning Resources")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "Search for resources",
            placeholder="e.g., Python Machine Learning, React Tutorial...",
            label_visibility="collapsed"
        )
    
    with col2:
        search_btn = st.button("🔍 Search", use_container_width=True)
    
    if search_btn and search_query:
        with st.spinner("🔍 Searching for resources..."):
            try:
                suggestor = SuggestionTool()
                results = suggestor.search_resources(search_query)
                
                if results:
                    st.markdown(f"#### 📖 Found {len(results)} resources:")
                    
                    for result in results:
                        st.markdown(f"""
                        <div class='resource-card'>
                            <h4>📌 {result.get('title', 'N/A')}</h4>
                            <p>{result.get('description', 'No description available')}</p>
                            <a href="{result.get('url', '#')}" target="_blank" style="color: #00d4ff;">🔗 Visit Resource</a>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No resources found. Try a different search query.")
                    
            except Exception as e:
                st.error(f"❌ Error searching resources: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Made with ❤️ using AI | Powered by OpenAI GPT-4</p>
</div>
""", unsafe_allow_html=True)
