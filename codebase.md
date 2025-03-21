# backend\.gitignore

```
.env
```

# backend\auth.py

```py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

router = APIRouter()
oauth = OAuth()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

print(f"Loaded GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
# print(f"Loaded GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET}")
# print(f"Loaded GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")


CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth.register(
    name = 'google',
    server_metadata_url = CONF_URL,
    client_id = GOOGLE_CLIENT_ID,
    client_secret = GOOGLE_CLIENT_SECRET,
    client_kwargs = {'scope': 'openid email profile'}
)

@router.get("/auth/login")
async def login(request: Request):
    redirect_uri = str(request.url_for('auth_callback'))
    print("Redirecting to:", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        print("Token data:", token)  # debug

        # If userinfo is already in the token, use it:
        user_info = token.get("userinfo")
        if not user_info:
            # If not present, fetch it from Google:
            user_info = await oauth.google.userinfo(token=token)

        return JSONResponse({"user_info": user_info})

    except OAuthError as error:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {error.error}")

```

# backend\data_fetcher.py

```py
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
```

# backend\locustfile.py

```py
from locust import HttpUser, task, between
# locust performance test to simulate multiple users making API requests to see how well my API performs under load
# HttpUser is a simulated user
# task is a decorator to mark methods as tasks that the user will perform
# between is making users randomly wait between x and y seconds before their next request


class MyUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def list_tools(self):
        self.client.get("/tools?skip=0&limit=10")
        

    @task
    def search_tools(self):
        self.client.get("/tools/search?name=football&category=Public%20APIs&limit=10")
```

# backend\main.py

```py
from fastapi import FastAPI, Depends, HTTPException, Query
# FastAPI creates the API application
# Depends handles dependency injection
# HTTPException is used to handle errors
# Query defines query parameters w/ validation and defaults
from fastapi.middleware.cors import CORSMiddleware
# CORS middleware to allow cross-origin requests
from sqlalchemy.orm import Session
# Session is a DB session
from backend.models import SessionLocal, Tool, Base, engine
# SessionLocal creates a new database session
# Tool is the SQLAlchemy ORM model for the tools table; one we've made
# Base is the Base class; engine is the DB connection engine
import uvicorn
# ASGI server (???) to run the FastAPI app
# asynchronous server gateway interface -- allows Python web apps to multithread basically (async funcs.)
from backend.schemas import ToolCreate, ToolUpdate, ToolResponse
# our Pydantic schemas
from typing import List, Optional
# type hints for query parameters
from sentence_transformers import SentenceTransformer, util
import torch
from starlette.middleware.sessions import SessionMiddleware
import os

Base.metadata.create_all(bind = engine) # creates database tables if they don't exist
# bind = engine tells SQLAlchemy to create all tables inside the DB connected to engine
app = FastAPI(title = "Tool Hub Aggregator API") # initializing the FastAPI app

SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SESSION_SECRET_KEY is not set in the environment variables!")

app.add_middleware(
    SessionMiddleware,
    secret_key = SECRET_KEY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"], # allow all origins, can change for production
    allow_credentials = True, # allow cookies
    allow_methods = ["*"], # allow all methods
    allow_headers = ["*"] # allow all headers
)

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_db():
    db = SessionLocal() # create the session
    try:
        yield db # allow request handlers to use this session
        # allows functions to pause and resume execution; like a return that doesn't quite exit
    finally:
        db.close()

# dependency injection is a design pattern where dependences (e.g. a DB session) are passed to functions instead of created inside them
# that's why we use Depends(get_db), because the func. doesn't have to create it

# @ is a decorator, a function modifying another. It tells FastAPI to run the function below when accessing the endpoint above
@app.get("/tools", response_model = List[ToolResponse]) # this is an GET endpoint
def read_tools(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Depends(get_db) is used to inject db into these functions
    # skip is pagination offset, default 0; ignore skip rows
    # limit is max no. of results
    # e.g. offset(10).limit(5) returns rows 11-15
    tools = db.query(Tool).offset(skip).limit(limit).all()
    # queries with offset of 0 and allows 10 results
    return tools # this is a list

@app.get("/tools/search", response_model = List[ToolResponse])
def search_tools(
    name: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(Tool)
    if name:
        query = query.filter(Tool.name.ilike(f"%{name}%"))
        # ilike (SQL-based partial matching)
        # a case insensitive search
        # e.g. %fast% matches FastAPI, fast, FAST TOOLS
    if category:
        query = query.filter(Tool.category.ilike(f"%{category}%"))
    tools = query.offset(skip).limit(limit).all()
    return tools

@app.get("/tools/ai_search", response_model = List[ToolResponse])
def ai_search(
    q: str = Query(..., description = "Search query"),
    top_k: int = Query(5, description = "Number of results to return"),
    db: Session = Depends(get_db)
    ):
    # get all tools
    tools = db.query(Tool).all()
    if not tools:
        raise HTTPException(status_code = 404, detail = "No tools found")
    # prep text for each tool (usu. description preferred)
    tool_texts = [tool.description if tool.description else tool.name for tool in tools]
    # computing embeddings
    tool_embeddings = model.encode(tool_texts, convert_to_tensor = True)
    query_embedding = model.encode(q, convert_to_tensor = True)
    # calculate cosine simularity scores
    cosine_scores = util.cos_sim(query_embedding, tool_embeddings)[0]
    # the top-k indices
    top_results = torch.topk(cosine_scores, k = top_k)
    top_indices = top_results.indices.tolist()
    # retrieve the corresponding objects
    top_tools = [tools[i] for i in top_indices]
    return top_tools


@app.get("/tools/{tool_id}", response_model = ToolResponse)
def read_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if tool is None:
        raise HTTPException(status_code = 404, detail = "Tool not found")
    return tool

@app.post("/tools", response_model = ToolResponse)
def create_tool(tool: ToolCreate, db: Session = Depends(get_db)):
    # convert tool into an SQLAlchemy object
    db_tool = Tool(name = tool.name, description = tool.description, category = tool.category, url = tool.url)
    db.add(db_tool)
    db.commit() # writes to DB but doesn't get auto-updated with autu-generated fields like id
    db.refresh(db_tool) # reloads the object to ensure defaults are included
    return db_tool

@app.put("/tools/{tool_id}", response_model = ToolResponse)
def update_tool(tool_id: int, tool_update: ToolUpdate, db: Session = Depends(get_db)):
    db_tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not db_tool:
        raise HTTPException(status_code = 404, detail = "Tool not found")
    if tool_update.name is not None:
        db_tool.name = tool_update.name
    if tool_update.description is not None:
        db_tool.description = tool_update.description
    if tool_update.category is not None:
        db_tool.category = tool_update.category
    if tool_update.url is not None:
        db_tool.url = tool_update.url
    db.commit()
    db.refresh(db_tool)
    return db_tool

@app.delete("/tools/{tool_id}")
def delete_tool(tool_id: int, db: Session = Depends(get_db)):
    db_tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not db_tool:
        raise HTTPException(status_code = 404, detail = "Tool not found")
    db.delete(db_tool)
    db.commit()
    return {"detail": "Tool deleted successfully"}
    
from backend.auth import router as auth_router
app.include_router(auth_router)
# this exposes endpoints at /auth/login and /auth/callback

if __name__ == "__main__":
    uvicorn.run("main:app", host = "0.0.0.0", port = 8000, reload = True)
```

# backend\models.py

```py
from sqlalchemy import create_engine, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

# create_engine creates a connection to the PostgreSQL DB
# Column defines a column; Integer, String, Text are all data types
# declarative_base is a base class for creating ORM (object-relational mapping) models
# sessionmaker creates a session factory

# connection string
# DATABASE_URL = "postgresql://tooluser:toolhub123@localhost/toolhub"
DATABASE_URL = "postgresql://tooluser:toolhub123@localhost/toolhub?options=-csearch_path%3Dtoolhub_schema"
# DATABASE_URL = "postgresql://tooluser:toolhub123@localhost/toolhub?options=-csearch_path=toolhub_schema"
# this tells SQLAlchemy how to connect to the PostgreSQL database

# creates base class all DB models will inherit from
Base = declarative_base()
Base.metadata.schema = "toolhub_schema"
# establish connection to DB
engine = create_engine(DATABASE_URL, echo = True)
# creates the session factory; commits are not automatic, flushes are not automatic, connected to DB
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

# defining the Tool model (a table)
class Tool(Base):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("url", name = "unique_tool_url"), # unique URLs
        {"schema": "toolhub_schema"} # ensure we use correct schema
    )
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, index = True)
    description = Column(Text, nullable = True)
    category = Column(String, index = True)
    url = Column(String, unique = True, index = True)
# our indices speed up squeries
# unique ensures values are unique
# nullable means it's optional

# e.g.
# CREATE TABLE tools (
#   id SERIAL PRIMARY KEY,
#   name VARCHAR(255) UNIQUE NOT NULL,
#   description TEXT,
#   category VARCHAR(255),
#   url VARCHAR(255) UNIQUE NOT NULL
# );

# this function checks if tools exists; if not, creates the table in the DB
# def init_db():
#     with engine.connect() as connection:
#         connection.execute("SET search_path TO toolhub_schema;")
#         Base.metadata.create_all(bind = engine)
def init_db():
    with engine.begin() as connection:
        print("Existing tables before dropping:", Base.metadata.tables.keys())

        # Drop tables first (if any exist)
        Base.metadata.drop_all(bind=connection)

        # Recreate tables
        Base.metadata.create_all(bind=connection)

        print("Existing tables after creation:", Base.metadata.tables.keys())



if __name__ == "__main__":
    init_db()
    print("Database initialized ;)")
```

# backend\schemas.py

```py
from pydantic import BaseModel
# BaseModel is a Pydantic class for automatic data validation and serialization
# thus, these three models inherit from it

class ToolCreate(BaseModel):
    # for creating new tools
    name: str
    description: str = None
    category: str
    url: str

class ToolUpdate(BaseModel):
    # for updating; all fields are optional, so partial updates are allowed
    name: str = None
    description: str = None
    category: str = None
    url: str = None

class ToolResponse(BaseModel):
    # defining how data is structured when returned
    # orm_mode allows Pydantic to work w/ SQLAlchemy ORM objects
    # otherwise, we can't serialize the objects
    # SQLAlchemy obj -> Pydantic model -> JSON
    id: int
    name: str
    description: str = None
    category: str
    url: str

    class Config:
        orm_mode = True




```

# backend\scrape_public_apis.py

```py
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
```

# backend\snippet.py

```py
import openai
import os
# this snippet is just to test the openai api key and connection
# had to pay like $10

openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use GPT-3.5-turbo cause GPT4 isn't available
        messages=[
            {"role": "system", "content": "You are an API documentation assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")

```

# backend\update_descriptions.py

```py
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

```

# README.md

```md
Below is the **README.md** file in its entirety. You can copy all of the text below into a local file named `README.md`. Depending on your editor or browser, you may also be able to right-click and "Save as..." to download it.

\`\`\`markdown
# Tool Hub Aggregator

## Overview
The **Tool Hub Aggregator** is a full-stack web application that collects, categorizes, and provides AI-powered search functionality for various tools and APIs. It features:
- **FastAPI Backend** with CRUD operations
- **PostgreSQL Database** for tool storage
- **Vue.js/React Frontend** for an intuitive UI
- **AI-powered search** using NLP embeddings
- **Deployed API & Frontend** *(Optional: Insert live link if deployed)*

## Features
- **View, Add, Update, and Delete Tools**
- **Search Tools by Name, Category, or AI Similarity**
- **Bookmark & Manage Favorite Tools** *(Optional)*
- **Fully Responsive UI**
- **Backend Hosted on AWS / Vercel / Netlify** *(Optional: If deployed, provide links)*

---

## 1. Installation and Setup

### 1.1 Clone the Repository
\`\`\`sh
git clone https://github.com/YOUR_USERNAME/tool-hub.git
cd tool-hub
\`\`\`

### 1.2 Set Up the Backend

#### Install Python Dependencies
Make sure you are in the **backend** directory and set up a virtual environment:
\`\`\`sh
cd backend
python -m venv env
source env/bin/activate   # On Windows: env\Scripts\activate
pip install -r requirements.txt
\`\`\`
*(If you don’t have a `requirements.txt`, install the necessary packages manually:)*
\`\`\`sh
pip install fastapi uvicorn psycopg2 requests beautifulsoup4 sentence-transformers
\`\`\`

#### Set Up PostgreSQL Database
1. **Install PostgreSQL** if you don’t have it yet.
2. **Create a user** and **database**:
   \`\`\`sql
   CREATE DATABASE toolhub;
   CREATE USER tooluser WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE toolhub TO tooluser;
   \`\`\`
3. **Update your `DATABASE_URL`** in `backend/models.py`:
   \`\`\`python
   DATABASE_URL = "postgresql://tooluser:yourpassword@localhost/toolhub"
   \`\`\`

#### Initialize the Database
\`\`\`sh
python models.py
\`\`\`
This will create all tables in your database.

#### Run the FastAPI Server
\`\`\`sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`
The API should now be live at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 2. Using the API

### Endpoints

#### Retrieve All Tools
- **GET** `/tools`
\`\`\`sh
curl -X GET "http://127.0.0.1:8000/tools?skip=0&limit=10" -H "accept: application/json"
\`\`\`

#### Retrieve a Specific Tool
- **GET** `/tools/{tool_id}`
\`\`\`sh
curl -X GET "http://127.0.0.1:8000/tools/1" -H "accept: application/json"
\`\`\`

#### Create a New Tool
- **POST** `/tools`
\`\`\`sh
curl -X POST "http://127.0.0.1:8000/tools" \
-H "Content-Type: application/json" \
-d '{
  "name": "Example Tool",
  "description": "A useful example tool",
  "category": "Utilities",
  "url": "https://example.com"
}'
\`\`\`

#### Update a Tool
- **PUT** `/tools/{tool_id}`
\`\`\`sh
curl -X PUT "http://127.0.0.1:8000/tools/1" \
-H "Content-Type: application/json" \
-d '{
  "name": "Updated Tool",
  "description": "Updated description"
}'
\`\`\`

#### Delete a Tool
- **DELETE** `/tools/{tool_id}`
\`\`\`sh
curl -X DELETE "http://127.0.0.1:8000/tools/1"
\`\`\`

#### Search for Tools (Keyword)
- **GET** `/tools/search?name=GitHub&category=Public%20APIs`
\`\`\`sh
curl -X GET "http://127.0.0.1:8000/tools/search?name=GitHub&category=Public%20APIs"
\`\`\`

---

## 3. AI-Powered Search

### AI Embeddings
This project includes **AI-powered search** using NLP embeddings (e.g., `sentence-transformers`, `Hugging Face Transformers`, or OpenAI). Tools can be indexed by vector embeddings, allowing users to search by **semantic meaning** rather than exact keyword matches.

### How to Use AI Search
- **Endpoint**: `GET /tools/ai-search?q=your_query`
- **Example**:
\`\`\`sh
curl -X GET "http://127.0.0.1:8000/tools/ai-search?q=machine%20learning"
\`\`\`
This returns tools that are conceptually similar to the query.

---

## 4. Frontend Setup

### 4.1 Install Frontend Dependencies
Assuming you have a **frontend** folder with a Vue.js, React, or Angular project:
\`\`\`sh
cd ../frontend
npm install
\`\`\`

### 4.2 Run the Development Server
\`\`\`sh
npm run dev
\`\`\`
Your frontend will typically run at [http://localhost:3000](http://localhost:3000) or [http://localhost:5173](http://localhost:5173), depending on the framework or bundler.

---

## 5. Deployment

### Backend Deployment
- **Option 1**: Deploy FastAPI on **AWS Lambda / Elastic Beanstalk / EC2**
- **Option 2**: Deploy on **Heroku** (easy for small projects)
- **Option 3**: Use **Railway.app** or **Render.com**

### Frontend Deployment
- **Option 1**: Deploy on **Vercel** (Recommended for React/Next.js)
- **Option 2**: Deploy on **Netlify** (Great for Vue.js, React, or Angular)
- **Option 3**: Use GitHub Pages (requires build configuration)

---

## 6. Tech Stack

| Component   | Technology                                               |
|-------------|----------------------------------------------------------|
| **Backend** | FastAPI (Python)                                         |
| **Database**| PostgreSQL                                               |
| **Frontend**| Vue.js / React / Angular                                 |
| **AI Search** | NLP embeddings (sentence-transformers / HF / OpenAI)   |
| **Deployment** | AWS, Heroku, Netlify, Vercel (optional)               |

---

## 7. Future Improvements
- [ ] **User Authentication** (e.g., JWT, OAuth)
- [ ] **Bookmark & Manage Favorites** in user accounts
- [ ] **Admin Dashboard** for curating tools
- [ ] **Trending/Popular Tools** based on user activity
- [ ] **Enhanced AI & Summaries** (add text summarization or auto-categorization)

---

## 8. Contributing
Contributions are welcome! Please open an issue or submit a pull request on GitHub.

---

## 9. License
This project is licensed under the [MIT License](LICENSE). Feel free to use it for your own purposes.
\`\`\`
```

# tool-hub-frontend\.gitignore

```
.DS_Store
node_modules
/dist


# local env files
.env.local
.env.*.local

# Log files
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# Editor directories and files
.idea
.vscode
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

```

# tool-hub-frontend\babel.config.js

```js
module.exports = {
  presets: [
    '@vue/cli-plugin-babel/preset'
  ]
}

```

# tool-hub-frontend\jsconfig.json

```json
{
  "compilerOptions": {
    "target": "es5",
    "module": "esnext",
    "baseUrl": "./",
    "moduleResolution": "node",
    "paths": {
      "@/*": [
        "src/*"
      ]
    },
    "lib": [
      "esnext",
      "dom",
      "dom.iterable",
      "scripthost"
    ]
  }
}

```

# tool-hub-frontend\package.json

```json
{
  "name": "tool-hub-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "serve": "vue-cli-service serve",
    "build": "vue-cli-service build",
    "lint": "vue-cli-service lint"
  },
  "dependencies": {
    "axios": "^1.8.3",
    "core-js": "^3.8.3",
    "vue": "^3.2.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@babel/core": "^7.12.16",
    "@babel/eslint-parser": "^7.12.16",
    "@vue/cli-plugin-babel": "~5.0.0",
    "@vue/cli-plugin-eslint": "~5.0.0",
    "@vue/cli-service": "~5.0.0",
    "autoprefixer": "^10.4.14",
    "eslint": "^7.32.0",
    "eslint-plugin-vue": "^8.0.3",
    "postcss": "^8.4.21",
    "tailwindcss": "^3.3.2"
  },
  "eslintConfig": {
    "root": true,
    "env": {
      "node": true
    },
    "extends": [
      "plugin:vue/vue3-essential",
      "eslint:recommended"
    ],
    "parserOptions": {
      "parser": "@babel/eslint-parser"
    },
    "rules": {}
  },
  "browserslist": [
    "> 1%",
    "last 2 versions",
    "not dead",
    "not ie 11"
  ]
}

```

# tool-hub-frontend\postcss.config.js

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}

```

# tool-hub-frontend\public\favicon.ico

This is a binary file of the type: Binary

# tool-hub-frontend\public\index.html

```html
<!DOCTYPE html>
<html lang="">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="icon" href="<%= BASE_URL %>favicon.ico">
    <title><%= htmlWebpackPlugin.options.title %></title>
  </head>
  <body>
    <noscript>
      <strong>We're sorry but <%= htmlWebpackPlugin.options.title %> doesn't work properly without JavaScript enabled. Please enable it to continue.</strong>
    </noscript>
    <div id="app"></div>
    <!-- built files will be auto injected -->
  </body>
</html>

```

# tool-hub-frontend\README.md

```md
# tool-hub-frontend

## Project setup
\`\`\`
npm install
\`\`\`

### Compiles and hot-reloads for development
\`\`\`
npm run serve
\`\`\`

### Compiles and minifies for production
\`\`\`
npm run build
\`\`\`

### Lints and fixes files
\`\`\`
npm run lint
\`\`\`

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).

```

# tool-hub-frontend\src\App.vue

```vue
<!-- <template>
  <img alt="Vue logo" src="./assets/logo.png">
  <HelloWorld msg="Welcome to Your Vue.js App"/>
</template> -->

<template>
  <div id = "app">
    <!-- <ToolList /> -->
    <router-view />
  </div>
</template>

<script>
  // import ToolList from './components/ToolList.vue'

  export default {
    // components: {
    //   ToolList
    // }
    name: 'App',
  };
</script>


<!-- <script>
import HelloWorld from './components/HelloWorld.vue'

export default {
  name: 'App',
  components: {
    HelloWorld
  }
}
</script> -->

<!-- <style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

body {
  padding: 20px;
}
</style> -->

```

# tool-hub-frontend\src\assets\logo.png

This is a binary file of the type: Image

# tool-hub-frontend\src\assets\main.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

# tool-hub-frontend\src\components\HelloWorld.vue

```vue
<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
    <p>
      For a guide and recipes on how to configure / customize this project,<br>
      check out the
      <a href="https://cli.vuejs.org" target="_blank" rel="noopener">vue-cli documentation</a>.
    </p>
    <h3>Installed CLI Plugins</h3>
    <ul>
      <li><a href="https://github.com/vuejs/vue-cli/tree/dev/packages/%40vue/cli-plugin-babel" target="_blank" rel="noopener">babel</a></li>
      <li><a href="https://github.com/vuejs/vue-cli/tree/dev/packages/%40vue/cli-plugin-eslint" target="_blank" rel="noopener">eslint</a></li>
    </ul>
    <h3>Essential Links</h3>
    <ul>
      <li><a href="https://vuejs.org" target="_blank" rel="noopener">Core Docs</a></li>
      <li><a href="https://forum.vuejs.org" target="_blank" rel="noopener">Forum</a></li>
      <li><a href="https://chat.vuejs.org" target="_blank" rel="noopener">Community Chat</a></li>
      <li><a href="https://twitter.com/vuejs" target="_blank" rel="noopener">Twitter</a></li>
      <li><a href="https://news.vuejs.org" target="_blank" rel="noopener">News</a></li>
    </ul>
    <h3>Ecosystem</h3>
    <ul>
      <li><a href="https://router.vuejs.org" target="_blank" rel="noopener">vue-router</a></li>
      <li><a href="https://vuex.vuejs.org" target="_blank" rel="noopener">vuex</a></li>
      <li><a href="https://github.com/vuejs/vue-devtools#vue-devtools" target="_blank" rel="noopener">vue-devtools</a></li>
      <li><a href="https://vue-loader.vuejs.org" target="_blank" rel="noopener">vue-loader</a></li>
      <li><a href="https://github.com/vuejs/awesome-vue" target="_blank" rel="noopener">awesome-vue</a></li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'HelloWorld',
  props: {
    msg: String
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h3 {
  margin: 40px 0 0;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}
</style>

```

# tool-hub-frontend\src\components\ToolDetails.vue

```vue
<template>
    <div class="p-6 max-w-4xl mx-auto">
        <button @click = "$router.go(-1)" class = "text-blue-500 underline mb-4">Back</button>
    <div v-if = "tool">
        <h1 class = "text-3xl font-bold mb-2">{{  tool.name }}</h1>
        <p class = "mb-4">{{  tool.description }}</p>
        <p class = "mb-4">Category: {{  tool.category }}</p>
        <a :href = "tool.url" target="_blank" class = "text-blue-600 hover: underline"> Visit Tool </a>
    </div>
    <div v-else>
        <p>Loading tool details...</p>
    </div>
    </div>
</template>

<script>
import axios from "axios";

export default {
    data() {
        return {
            tool: null,
        };
    },
    created() {
        const toolId = this.$route.params.id;
        axios
            .get(`http://localhost:8000/tools/${toolId}`)
            .then((response) => {
                this.tool = response.data;
            })
            .catch((error) => {
                console.error("Errror fetching tool details:", error);
            });
    },
};
</script>
```

# tool-hub-frontend\src\components\ToolList.vue

```vue
<template>
  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-center">Tool Hub Aggregator</h1>
    
    <!-- Search Bar with Category Filter and AI Search Toggle -->
    <div class="flex flex-col md:flex-row md:items-center mb-6">
      <input
        v-model="searchQuery"
        @keyup.enter="searchTools"
        type="text"
        placeholder="Search by name or AI-powered..."
        class="flex-grow border border-gray-300 p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2 md:mb-0"
      />
      <input
        v-model="categoryQuery"
        @keyup.enter="searchTools"
        type="text"
        placeholder="Search by category..."
        class="flex-grow border border-gray-300 p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 md:ml-4"
      />
      <button
        @click="searchTools"
        class="ml-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
      >
        Search
      </button>
    </div>
    <!-- Toggle AI Search -->
    <div class="flex items-center mb-4">
      <input type="checkbox" v-model="useAISearch" id="ai-search-toggle" class="mr-2">
      <label for="ai-search-toggle" class="text-gray-700">Use AI-powered search</label>
    </div>

    <!-- List of Tools -->
    <ul>
      <li
        v-for="tool in tools"
        :key="tool.id"
        class="mb-4 p-4 border border-gray-200 rounded hover:shadow transition-shadow"
      >
        <!-- Use router-link to navigate to the details page -->
        <router-link :to="`/tools/${tool.id}`" class="text-xl font-semibold text-blue-600 hover:underline">
          {{ tool.name }}
        </router-link>
        <p class="text-gray-700 mt-2">{{ tool.description }}</p>
      </li>
    </ul>
  </div>
</template>
  
<script>
  import axios from "axios";
  
  export default {
    data() {
      return {
        tools: [],
        searchQuery: "",
        categoryQuery: "",
        useAISearch: false, // toggle
        timeout: null,
        lastQuery: "",
      };
    },
    watch: {
      searchQuery() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
          this.searchTools();
        }, 500);
      },
      categoryQuery() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
          this.searchTools();
        }, 500);
      },
    },
    created() {
      this.fetchTools();
    },
    methods: {
      fetchTools() {
        axios
          .get("http://localhost:8000/tools?skip=0&limit=10")
          .then((response) => {
            this.tools = response.data;
          })
          .catch((error) => {
            console.error("Error fetching tools:", error);
          });
        },
        searchTools() {
          if (this.searchQuery.trim() === "" && this.categoryQuery.trim() === "") {
            // empty, no search
            this.tools = []; // clear list
            this.fetchTools();
            return;
          }
          const params = new URLSearchParams();
          params.append("limit", "10");

          if (this.useAISearch && this.searchQuery.trim() !== "" && this.searchQuery !== this.lastQuery) {
            // AI Search 
            this.lastQuery = this.searchQuery;
            axios
              .get(`http://localhost:8000/tools/ai_search?q=${encodeURIComponent(this.searchQuery)}&top_k=10`)
              .then((response) => {
                this.tools = response.data;
              }) 
              .catch((error) => {
                console.error("Error with AI-powered search:", error);
              });
            } else {
              // Regular Search
              if (this.searchQuery.trim() !== "") {
                params.append("name", this.searchQuery);
              }
              if (this.categoryQuery.trim() !== "") {
                params.append("category", this.categoryQuery);
              }
              this.tools = [];
              axios
                .get(`http://localhost:8000/tools/search?${params.toString()}`)
                .then((response) => {
                  this.tools = response.data;
                })
                .catch((error) => {
                  console.error("Error searching tools:", error);
                });
          }
        },
    },
  };
  </script>
  
```

# tool-hub-frontend\src\main.js

```js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router';
import './assets/main.css'

// createApp(App).mount('#app')
createApp(App).use(router).mount('#app')

```

# tool-hub-frontend\src\router\index.js

```js
import {createRouter, createWebHistory} from 'vue-router';
import ToolList from '../components/ToolList.vue';
import ToolDetails from '../components/ToolDetails.vue';

const routes = [
    {
        path: '/',
        name: 'ToolList',
        component: ToolList,
    },
    {
        path: '/tools/:id',
        name: 'ToolDetails',
        component: ToolDetails,
        props: true,
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;
```

# tool-hub-frontend\tailwind.config.js

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

```

# tool-hub-frontend\vue.config.js

```js
const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true
})

```

