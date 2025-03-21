import requests
from models import SessionLocal, Tool

# e.g.
API_URL = "https://api.publicapis.org/entries"

def fetch_tools():
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json().get("entries", [])
        db = SessionLocal()
        for item in data[:20]:
            tool = Tool(
                name = item.get("API", "No Name"),
                description = item.get("Description", "No Description"),
                category = item.get("Category", "Uncategorized"),
                url = item.get("Link", "#")
            )
            db.add(tool)
        db.commit()
        db.close()
        print("Tools added successfully!")
    else:
        print("Failed to fetch tools", response.status_code)

if __name__ == "__main__":
    fetch_tools()