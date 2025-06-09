from typing import Optional
import shutil
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Cookie, UploadFile, File 
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import engine, get_db
from models import Base
from crud import *
from schemas import *
from security import *
import os
import uvicorn


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
Base.metadata.create_all(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

from fastapi import Header, Cookie

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None)
) -> User:
    jwt_token = None

    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]

    elif access_token and access_token.startswith("Bearer "):
        jwt_token = access_token[7:]

    if not jwt_token:
        raise HTTPException(status_code=401, detail="Токен не знайдено")

    try:
        user_login = decode_access_token(jwt_token)
        user = db.query(User).filter(User.login == user_login).first()
        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалідний токен")

@app.get("/", response_class=HTMLResponse)
def show_main_page(
    request: Request,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(None)
):
    current_user = None
    if access_token:
        scheme, _, jwt_token = access_token.partition(" ")
        if scheme.lower() == "bearer":
            try:
                user_login = decode_access_token(jwt_token)
                current_user = db.query(User).filter(User.login == user_login).first()
            except Exception:
                pass

    scope = request.query_params.get("scope", "all")

    if current_user and scope == "my":
        tracks = db.query(Track).filter(Track.user_id == current_user.id).all()
        authors = db.query(Author).all()
        playlists = db.query(Playlist).filter(Playlist.user_id == current_user.id).all()
    else:
        tracks = db.query(Track).all()
        authors = db.query(Author).all()
        playlists = db.query(Playlist).all()

    return templates.TemplateResponse(
        "music.html",
        {
            "request": request,
            "tracks": tracks,
            "authors": authors,
            "playlists": playlists,
            "current_user": current_user
        }
    )

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == login).first()  
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    if not verify_password(password, user.password):  
        raise HTTPException(status_code=401, detail="Невірний пароль")

    token = create_access_token({"sub": user.login})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", f"Bearer {token}", httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register(
    login: str = Form(...),
    password: str = Form(...),
    avatar_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    
    existing = db.query(User).filter(User.login == login).first()
    if existing:
        raise HTTPException(status_code=400, detail="Користувач вже існує")

    avatar_url = None
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    user_data = UserCreate(login = login, password = password, avatar = avatar_url)
    user = create_user(db, user_data)

    token = create_access_token({"sub": user.login})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", f"Bearer {token}", httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response

@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.login == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Невірний логін або пароль")

    access_token = create_access_token(data={"sub": user.login})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected")
def protected(current_user: User = Depends(get_current_user)):
    return {"message": f"Привіт, {current_user.login}! Це захищений маршрут."}

@app.get("/edit_user", response_class=HTMLResponse)
def edit_user_page(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse("edit_user.html", {
        "request": request,
        "user": current_user
    })
@app.post("/edit_user")
def edit_user(
    login: str = Form(...),
    avatar_file: UploadFile = File(None),
    old_password: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(User).filter(User.login == login, User.id != current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Логін вже зайнятий.")

    avatar_url = current_user.avatar
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    user_data = UserCreate(login=login, password=password, avatar=avatar_url)
    update_user(db, current_user.id, user_data)

    new_token = create_access_token({"sub": user_data.login})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("access_token", f"Bearer {new_token}", httponly=True)
    return response


@app.post("/delete_user/{user_id}")
def delete_user_view(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return delete_user(db, user_id)

def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено.")

    playlists = db.query(Playlist).filter(Playlist.user_id == user.id).all()
    for playlist in playlists:
        if playlist.avatar and os.path.exists(playlist.avatar[1:]):
            os.remove(playlist.avatar[1:])
        db.delete(playlist)

    authors = db.query(Author).all()
    for author in authors:
        if author.avatar and os.path.exists(author.avatar[1:]):
            os.remove(author.avatar[1:])
        for track in author.tracks:
            if track.file_url and os.path.exists(track.file_url[1:]):
                os.remove(track.file_url[1:])
            if track.avatar and os.path.exists(track.avatar[1:]):
                os.remove(track.avatar[1:])
            db.delete(track)
        db.delete(author)

    db.delete(user)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/add_track", response_class=HTMLResponse)
def add_track_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  
    authors = db.query(Author).all()
    return templates.TemplateResponse("add_track.html", {
        "request": request,
        "authors": authors
    })

@app.post("/add_track")
def add_track(
    title: str = Form(...),
    file: UploadFile = File(...),
    avatar_file: UploadFile = File(...),
    author_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    track_filename = file.filename  
    track_path = f"static/tracks/{track_filename}"
    with open(track_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    avatar_url = None
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    track_data = TrackCreate(
        title = title,
        file_url = f"/{track_path}",
        avatar = avatar_url,
        author_id = author_id,
        user_id = current_user.id
    )

    create_track(db, track_data)
    return RedirectResponse("/", status_code=303)

@app.get("/edit_track/{track_id}", response_class=HTMLResponse)
def edit_track_page(request: Request, track_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    track = get_track(db, track_id)
    authors = get_authors(db) 
    if not current_user or current_user.id != track.user_id:
        raise HTTPException(status_code=403, detail="Доступ заборонено.")
    return templates.TemplateResponse(
        "edit_track.html",
        {
            "request": request,
            "track": track,
            "authors": authors,
            "current_user": current_user
        }
    )

@app.post("/edit_track/{track_id}")
def edit_track_submit(
    track_id: int,
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    avatar_file: Optional[UploadFile] = File(None),
    author_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено.")
        
    file_url = track.file_url
    if file:
        track_filename = file.filename
        track_path = f"static/tracks/{track_filename}"
        with open(track_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = f"/{track_path}"

    avatar_url = track.avatar
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    track_data = TrackCreate(
    title=title,
    file_url=file_url,
    avatar=avatar_url,
    author_id=author_id,
    user_id=current_user.id  
)

    update_track(db, track_id, track_data)

    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_track/{track_id}")
def delete_track_view(track_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return delete_track(db, track_id, current_user)

def delete_track(db: Session, track_id: int, current_user: User):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено.")
    if track.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Немає прав на видалення цього треку.")

    if track.file_url:
        track_path = track.file_url.lstrip("/")
        if os.path.exists(track_path):
            os.remove(track_path)

    if track.avatar:
        avatar_path = track.avatar.lstrip("/")
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

    db.delete(track)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/add_author", response_class=HTMLResponse)
def add_author_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("add_author.html", {"request": request})

@app.post("/add_author")
def add_author(
    name: str = Form(...),
    avatar_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  
    avatar_url = None
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    author_data = AuthorCreate(
        name=name,
        avatar=avatar_url,
    )
    create_author(db, author_data)
    return RedirectResponse("/", status_code=303)

@app.get("/edit_author/{author_id}", response_class=HTMLResponse)
def edit_author_page(request: Request, author_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    author = get_author(db, author_id)
    return templates.TemplateResponse(
        "edit_author.html",
        {
            "request": request,
            "author": author,
            "current_user": current_user,
        }
    )

@app.post("/edit_author/{author_id}")
def edit_author_submit(
    author_id: int,
    name: str = Form(...),
    avatar_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автора не знайдено.")
    
    avatar_url = author.avatar
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    author.name = name
    author.avatar = avatar_url
    db.commit()
    db.refresh(author)
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete_author/{author_id}")
def delete_author_view(
    author_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_author(db, author_id)

def delete_author(db: Session, author_id: int):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автора не знайдено.")
    if author.tracks and len(author.tracks) > 0:
        raise HTTPException(status_code=400, detail="Неможливо видалити автора, бо у нього є пісні.")

    if author.avatar:
        avatar_path = author.avatar.lstrip("/")
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

    db.delete(author)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/add_playlist", response_class=HTMLResponse)
def add_playlist_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("add_playlist.html", {"request": request})

@app.post("/add_playlist")
def add_playlist(
    title: str = Form(...),
    avatar_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    avatar_url = None
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"
    playlist_data = PlaylistCreate(
    title = title,
    avatar = avatar_url,
    user_id = current_user.id
    )
    playlist = create_playlist(db, playlist_data)
    return RedirectResponse(f"/playlist/{playlist.id}", status_code=303)

@app.get("/edit_playlist/{playlist_id}", response_class=HTMLResponse)
def edit_playlist_page(request: Request, playlist_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    playlist = get_playlist(db, playlist_id)
    if not current_user or current_user.id != playlist.user_id:
        raise HTTPException(status_code=403, detail="Доступ заборонено.")
    return templates.TemplateResponse(
        "edit_playlist.html",
        {
            "request": request,
            "playlist": playlist,
            "current_user": current_user,
        }
    )


@app.post("/edit_playlist/{playlist_id}")
async def edit_playlist_submit(
    playlist_id: int,
    title: str = Form(...),
    avatar_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code = 404, detail = "Плейліст не знайдено")

    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = 403, detail = "Недостатньо прав для редагування цього плейліста")

    avatar_url = playlist.avatar
    if avatar_file:
        avatar_filename = avatar_file.filename
        avatar_path = f"static/avatars/{avatar_filename}"
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        avatar_url = f"/{avatar_path}"

    playlist_data = PlaylistCreate(
        title = title,
        avatar = avatar_url,
        user_id = current_user.id
    )

    update_playlist(db, playlist_id, playlist_data)

    return RedirectResponse(f"/playlist/{playlist_id}", status_code=303)

@app.post("/delete_playlist/{playlist_id}")
def delete_playlist_view(playlist_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return delete_playlist(db, playlist_id, current_user)

def delete_playlist(db: Session, playlist_id: int, current_user: User):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейліст не знайдено.")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Немає прав на видалення цього плейліста.")

    if playlist.avatar:
        avatar_path = playlist.avatar.lstrip("/")
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

    db.delete(playlist)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/playlist/{playlist_id}", response_class=HTMLResponse)
def show_playlist_page(
    request: Request,
    playlist_id: int,
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(None)
):
    current_user = None
    if access_token:
        scheme, _, jwt_token = access_token.partition(" ")
        if scheme.lower() == "bearer":
            try:
                user_login = decode_access_token(jwt_token)
                current_user = db.query(User).filter(User.login == user_login).first()
            except:
                pass

    playlist = get_playlist(db, playlist_id)
    tracks = playlist.tracks
    all_tracks = db.query(Track).all()

    return templates.TemplateResponse(
        "playlist.html",
        {
            "request": request,
            "playlist": playlist,
            "tracks": tracks,
            "all_tracks": all_tracks,
            "current_user": current_user,
        }
    )

@app.post("/playlist/{playlist_id}/add_track/{track_id}")
def add_track_to_playlist_endpoint(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = get_playlist(db, playlist_id)
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Немає прав")

    add_track_to_playlist(db, playlist_id, track_id)
    return JSONResponse({"detail": "OK"}, status_code=200)

@app.post("/playlist/{playlist_id}/remove_track/{track_id}")
def remove_track_from_playlist_endpoint(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = get_playlist(db, playlist_id)
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Немає прав редагувати цей плейлист")
    return remove_track_from_playlist(db, playlist_id, track_id)

uvicorn.run(app)
