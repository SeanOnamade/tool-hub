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
    # allow_origins = ["*"], # allow all origins, can change for production
    allow_origins = ["http://localhost:8080"], # allow all origins, can change for production
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