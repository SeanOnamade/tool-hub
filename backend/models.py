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

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "toolhub_schema"}

    id = Column(Integer, primary_key = True, index = True)
    email = Column(String, unique = True, index = True, nullable = False)
    name = Column(String, nullable = True)
    picture = Column(String, nullable = True)

# this function checks if tools exists; if not, creates the table in the DB
# def init_db():
#     with engine.connect() as connection:
#         connection.execute("SET search_path TO toolhub_schema;")
#         Base.metadata.create_all(bind = engine)
def init_db():
    with engine.begin() as connection:
        print("Existing tables before dropping:", Base.metadata.tables.keys())
        # Drop tables first (if any exist)
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=connection)
        # Recreate tables
        print("Creating new tables...")
        Base.metadata.create_all(bind=connection)
        print("Existing tables after creation:", Base.metadata.tables.keys())



if __name__ == "__main__":
    init_db()
    print("Database initialized ;)")