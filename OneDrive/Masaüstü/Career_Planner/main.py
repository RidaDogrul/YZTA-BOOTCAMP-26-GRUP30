from agents.career_goal_agent import CareerGoalAgent
from agents.task_scheduler_agent import TaskSchedulerAgent
from tools.suggestion_tool import SuggestionTool
from memory.user_memory import UserMemory
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Career Planner Agent")

    user_memory = UserMemory()
    
    goal = input("What is your target profession? ")
    user_memory.update_goal(goal)
    
    # roadmap
    goal_agent = CareerGoalAgent()
    roadmap = goal_agent.ask_career_goal(goal)

    print("\n📋 Career Roadmap:")
    print("-" * 50)
    print(roadmap)
    print("-" * 50)

    # time scheduler
    num_of_week = 4
    scheduler = TaskSchedulerAgent(weeks = num_of_week)
    schedule = scheduler.create_schedule(roadmap)
    scheduler.save_schedule(schedule)

    print(f"\n📅 {num_of_week}-Week Plan:")
    print("-" * 50)
    print(schedule)
    print("-" * 50)
    
    # Source Suggestion
    suggestor = SuggestionTool()
    topic = input("Enter a skill title for resource suggestions: ")
    results = suggestor.search_resources(topic)
    
    print("\nResource Suggestions:")
    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Description: {result['description']}")
        print("-" * 50)

