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



