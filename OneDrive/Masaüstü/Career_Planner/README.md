# Career Planner Agent

An intelligent AI-powered career planning assistant that helps users create personalized career roadmaps, schedule tasks, and discover learning resources.

## 🚀 Features

- **Modern Web Interface** - Beautiful Streamlit-based UI with gradient styling and responsive design
- **Career Goal Analysis** - AI-powered agent that creates detailed career roadmaps based on your target profession
- **Task Scheduling** - Automatically generates weekly task plans to help you achieve your career goals
- **Resource Suggestions** - Smart resource finder with curated learning resources from top platforms
- **Memory Persistence** - Stores user goals and progress for future reference
- **User-Friendly Responses** - Returns plain text responses in a warm, engaging tone instead of JSON

## 📸 Screenshots

### 🗺️ Career Roadmap Generator
Generate a personalized career roadmap based on your target profession:


### 📅 Weekly Schedule
View your weekly task plan to achieve your career goals:


### 📚 Resource Finder
Find relevant learning resources, courses, and tutorials:



## 📁 Project Structure

```
Career_Planner_Agent/
├── agents/
│   ├── career_goal_agent.py    # Career roadmap generation agent
│   └── task_scheduler_agent.py # Weekly task scheduling agent
├── memory/
│   └── user_memory.py          # User data persistence
├── tools/
│   └── suggestion_tool.py      # Web search for learning resources
├── app.py                      # Streamlit web interface
├── main.py                     # CLI application entry point
├── memory.json                 # Stored user data
├── schedule.txt                # Generated schedule
└── requirements.txt            # Python dependencies
```

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/elifkeskin/-Career-Planner-with-AI-Agent.git
cd Career_Planner_Agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## 🎯 Usage

### 🌐 Web Interface (Recommended)
Run the Streamlit web app:
```bash
streamlit run app.py
```

### 💻 Command Line Interface
Run the CLI version:
```bash
python main.py
```

## 🔧 Technologies Used

- **Python 3.x**
- **Streamlit** - Modern web interface
- **LangChain** - For building AI agents
- **OpenAI GPT-4** - Language model for generating career advice
- **BeautifulSoup** - For web scraping learning resources
- **Requests** - HTTP library for API calls

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
