from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
import os
from dotenv import load_dotenv
from backend.models import SessionLocal, User

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
        user_info = token.get("userinfo")
        if not user_info:
            user_info = await oauth.google.userinfo(token=token)

        # Extract the fields we want
        email = user_info["email"]
        name = user_info.get("name")
        picture = user_info.get("picture")

        # Store/lookup user in DB
        db = SessionLocal()
        db_user = db.query(User).filter(User.email == email).first()
        if not db_user:
            # if we can't find by email, then we create a new user
            db_user = User(email=email, name=name, picture=picture)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

        # Store user ID in session for future requests
        request.session["user_id"] = db_user.id
        db.close()

        # Redirect user to your frontend homepage (or a profile page)
        return RedirectResponse(url="http://localhost:8080/")  # or your chosen frontend URL

    except OAuthError as error:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {error.error}")


@router.get("/auth/profile")
def get_profile(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    db = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    db.close()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": db_user.id,
        "email": db_user.email,
        "name": db_user.name,
        "picture": db_user.picture
    }


@router.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"detail": "Logged out"}
