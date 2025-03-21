from sqlalchemy.orm import Session
from models import SessionLocal, Tool
import openai
import os

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_description(name):
    """ Uses GPT to generate an API description """
    prompt = f"Provide a short, concise description for an API named '{name}'."
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an API documentation assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return "No description available"

def update_descriptions():
    db = SessionLocal()
    tools = db.query(Tool).filter(Tool.description == "Scraped from public-apis list").all()
    
    for tool in tools:
        print(f"Updating: {tool.name}")
        tool.description = generate_description(tool.name)
        db.commit()
    
    db.close()
    print("Descriptions updated successfully!")

if __name__ == "__main__":
    update_descriptions()
