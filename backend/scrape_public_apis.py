from bs4 import BeautifulSoup # for parsing HTML; may no longer be needed
import requests # fetches web page content
from sqlalchemy.dialects.postgresql import insert # allows inserting data into the DB
from models import SessionLocal, Tool # SessionLocal creates a session, while Tool is the DB model
import openai
import os
import re

openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

openai.api_key = openai_api_key
GITHUB_URL = "https://github.com/public-apis/public-apis"
RAW_MARKDOWN_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"

md_link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")
# \[(.*?)\] captures everything inside [ ] (the API name).
# \((.*?)\) captures everything inside ( ) (the URL).

def generate_description(name, fallback_desc):
    name = name.strip()
    if not name:
        return fallback_desc or "No description available"
    if fallback_desc.strip() == "" or "Back to Index" in fallback_desc:
        prompt = f"""
        You are an API documentation assistant. 
        The API is called '{name}' and is a public API.
        Please provide a short, concise description for this API, focusing on what it does for developers.
        """
        try:
            response = openai.ChatCompletion.create(
                model = "gpt-3.5-turbo",
                messages = [{"role": "system", "content": "You are an API documentation assistant."},
                            {"role": "user", "content": prompt}]
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return fallback_desc or "No description available"
    else:
        return fallback_desc or "No description available"
    
def parse_markdown_table_line(line):
    """
    Split the markdown table row into columns
    API | Desc | Auth |HTTPS | CORS
    Returns (name, url, desc) or None if invalid
    """
    columns = line.split("|")
    if len(columns) < 6:
        return None
    name_col = columns[1].strip()
    desc_col = columns[2].strip()

    match = md_link_pattern.search(name_col)
    if match:
        api_name = match.group(1) or "Untitled"
        api_url = match.group(2)
    else:
        return None
    if not api_url.startswith("http"):
        return None
    if "Back to Index" in desc_col:
        desc_col = ""
    return api_name, api_url, desc_col

def scrape_public_apis():
    # response = requests.get(GITHUB_URL)
    response = requests.get(RAW_MARKDOWN_URL)
    if response.status_code != 200:
        print("Failed to fetch tools", response.status_code)
        return
    # soup = BeautifulSoup(response.text, "html.parser") # parses and organizes the raw HTML, using the built-in Python parser html.parser
    # links = soup.find_all("a", href = True) # get everything with <a> and href
    # db = SessionLocal() # new DB session
    # count = 0 # count of tools added
    # existing_urls_in_db = {row.url for row in db.query(Tool.url).all()} # stores all URLs already in the DB and puts them in a set, for O(1) lookup
    # for link in links:
    #     href = link["href"] # grabs every href
    #     text = link.get_text(strip = True) # and grabs the link text
    #     desc_tag = link.find_next("p")
    #     description = desc_tag.get_text(strip = True) if desc_tag else generate_description(text)
    #     if href.startswith("http") and "github.com/public-apis" not in href: # ensure they start w/ http and exclude internal links (redundant if we didn't do this)
    #         if href in existing_urls_in_db: # remove dups
    #             continue
    #         # if href in newly_inserted_urls:
    #         #     continue
    #         # existing_tool = db.query(Tool).filter_by(url=href).first()
    #         # if existing_tool:
    #         #     continue
    #         stmt = insert(Tool).values(
    #             name = text or "Untitled",
    #             description = description,
    #             category = "Public APIs",
    #             url = href
    #         ).on_conflict_do_nothing()
    #         # this was an insert statement; if the URL already exists, we don't insert it again
    #         db.execute(stmt)
    #         count += 1
    lines = response.text.split("\n")
    db = SessionLocal()
    existing_urls_in_db = {row.url for row in db.query(Tool.url).all()}
    count = 0
    for line in lines:
        if not line.startswith("|"):
            continue
        if line.startswith("|:---") or line.startswith("|---"):
            continue
        parsed = parse_markdown_table_line(line)
        if not parsed:
            continue
        api_name, api_url, api_desc = parsed
        if api_url in existing_urls_in_db:
            continue
        final_desc = generate_description(api_name, api_desc) # maybe
        stmt = insert(Tool).values(
            name = api_name,
            description = final_desc,
            category = "Public APIs",
            url = api_url
        ).on_conflict_do_nothing()
        db.execute(stmt)
        count += 1
        existing_urls_in_db.add(api_url)
    db.commit()
    db.close()
    print(f"Scraped and stored {count} tools (links) from the Public APIs repo")

if __name__ == "__main__":
    scrape_public_apis()