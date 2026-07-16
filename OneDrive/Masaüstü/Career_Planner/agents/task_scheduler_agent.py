import datetime
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# takvim oluşturucu ajan sınıfı tanımla
class TaskSchedulerAgent:
    def __init__(self, weeks=4):
        self.weeks = weeks
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0.5)

    # Create weekly task schedule based on career roadmap
    def create_schedule(self, roadmap):
        today = datetime.date.today()
        
        messages = [
            SystemMessage(content=f"""
You are a career planning assistant. Create a {self.weeks}-week study plan based on the given career roadmap.

Today's date: {today}

Format your plan as follows:
- Header for each week (Week 1, Week 2, etc.)
- Specify the start date for each week
- List the tasks to be completed that week
- Add brief explanations for each task

Use user-friendly, clear, and motivating language.
DO NOT use JSON format. Respond in plain text only.
            """),
            HumanMessage(content=f"Career Roadmap:\n{roadmap}\n\nCreate a {self.weeks}-week study plan based on this roadmap.")
        ]
        
        response = self.llm.invoke(messages)
        return response.content

    def save_schedule(self, schedule, filename="schedule.txt"):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(schedule)