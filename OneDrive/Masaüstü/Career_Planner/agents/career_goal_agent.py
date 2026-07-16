from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# kariyer planlama ajanı sınıfı tanımla
class CareerGoalAgent:
    def __init__(self, model_name="gpt-4"):
        self.llm = ChatOpenAI(model_name=model_name, temperature=0.5)
        

    # Generate career roadmap based on user's target profession
    def ask_career_goal(self, user_input):
        messages = [
            SystemMessage(content="""
You are a friendly career advisor agent. Help users with career goals and career planning.
Provide helpful, accurate, and engaging responses.

Write your answers in a warm, friendly tone that speaks directly to the end user.
Avoid technical jargon and use clear, understandable language.

Format your response as follows:
1. A brief introduction paragraph about the career goal
2. Step-by-step roadmap (explain each step clearly)
3. Important skills and recommendations
4. A motivating closing message

DO NOT use JSON format. Respond in plain text only.
            """),
            HumanMessage(content=f"Target Career: {user_input}. Please create a detailed career roadmap for me.")
        ]
        response = self.llm.invoke(messages)
        # yanıtı düz metin olarak döndür
        return response.content


