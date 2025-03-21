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
```sh
git clone https://github.com/YOUR_USERNAME/tool-hub.git
cd tool-hub
```

### 1.2 Set Up the Backend

#### Install Python Dependencies
Make sure you are in the **backend** directory and set up a virtual environment:
```sh
cd backend
python -m venv env
source env/bin/activate   # On Windows: env\Scripts\activate
pip install -r requirements.txt
```
*(If you don’t have a `requirements.txt`, install the necessary packages manually:)*
```sh
pip install fastapi uvicorn psycopg2 requests beautifulsoup4 sentence-transformers
```

#### Set Up PostgreSQL Database
1. **Install PostgreSQL** if you don’t have it yet.
2. **Create a user** and **database**:
   ```sql
   CREATE DATABASE toolhub;
   CREATE USER tooluser WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE toolhub TO tooluser;
   ```
3. **Update your `DATABASE_URL`** in `backend/models.py`:
   ```python
   DATABASE_URL = "postgresql://tooluser:yourpassword@localhost/toolhub"
   ```

#### Initialize the Database
```sh
python models.py
```
This will create all tables in your database.

#### Run the FastAPI Server
```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
The API should now be live at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 2. Using the API

### Endpoints

#### Retrieve All Tools
- **GET** `/tools`
```sh
curl -X GET "http://127.0.0.1:8000/tools?skip=0&limit=10" -H "accept: application/json"
```

#### Retrieve a Specific Tool
- **GET** `/tools/{tool_id}`
```sh
curl -X GET "http://127.0.0.1:8000/tools/1" -H "accept: application/json"
```

#### Create a New Tool
- **POST** `/tools`
```sh
curl -X POST "http://127.0.0.1:8000/tools" \
-H "Content-Type: application/json" \
-d '{
  "name": "Example Tool",
  "description": "A useful example tool",
  "category": "Utilities",
  "url": "https://example.com"
}'
```

#### Update a Tool
- **PUT** `/tools/{tool_id}`
```sh
curl -X PUT "http://127.0.0.1:8000/tools/1" \
-H "Content-Type: application/json" \
-d '{
  "name": "Updated Tool",
  "description": "Updated description"
}'
```

#### Delete a Tool
- **DELETE** `/tools/{tool_id}`
```sh
curl -X DELETE "http://127.0.0.1:8000/tools/1"
```

#### Search for Tools (Keyword)
- **GET** `/tools/search?name=GitHub&category=Public%20APIs`
```sh
curl -X GET "http://127.0.0.1:8000/tools/search?name=GitHub&category=Public%20APIs"
```

---

## 3. AI-Powered Search

### AI Embeddings
This project includes **AI-powered search** using NLP embeddings (e.g., `sentence-transformers`, `Hugging Face Transformers`, or OpenAI). Tools can be indexed by vector embeddings, allowing users to search by **semantic meaning** rather than exact keyword matches.

### How to Use AI Search
- **Endpoint**: `GET /tools/ai-search?q=your_query`
- **Example**:
```sh
curl -X GET "http://127.0.0.1:8000/tools/ai-search?q=machine%20learning"
```
This returns tools that are conceptually similar to the query.

---

## 4. Frontend Setup

### 4.1 Install Frontend Dependencies
Assuming you have a **frontend** folder with a Vue.js, React, or Angular project:
```sh
cd ../frontend
npm install
```

### 4.2 Run the Development Server
```sh
npm run dev
```
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