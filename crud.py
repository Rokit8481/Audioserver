from sqlalchemy.orm import Session
from models import User, Author, Track, Playlist
from schemas import UserCreate, AuthorCreate, TrackCreate, PlaylistCreate
from fastapi import HTTPException
from security import hash_password

def create_user(db: Session, user: UserCreate):
    hashed_password = hash_password(user.password)
    new_user = User(login=user.login, password=hashed_password, avatar = user.avatar)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def update_user(db: Session, user_id: int, user_data: UserCreate):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено.")
    user.login = user_data.login
    user.password = hash_password(user_data.password)
    user.avatar = user_data.avatar 
    db.commit()
    db.refresh(user)
    return user

def get_author(db: Session, author_id: int):
    author = db.query(Author).get(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Автор не знайдений.")
    return author

def get_authors(db: Session):
    return db.query(Author).all()

def create_author(db: Session, author: AuthorCreate):
    new_author = Author(**author.dict())
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return new_author

def get_track(db: Session, track_id: int):
    track = db.query(Track).get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдений.")
    return track

def create_track(db: Session, track: TrackCreate):
    new_track = Track(**track.dict())
    db.add(new_track)
    db.commit()
    db.refresh(new_track)
    return new_track

def update_track(db: Session, track_id: int, track_data: TrackCreate):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено.")
    track.title = track_data.title
    track.file_url = track_data.file_url
    track.avatar = track_data.avatar
    track.author_id = track_data.author_id
    track.user_id = track_data.user_id
    db.commit()
    db.refresh(track)
    return track

def get_playlist(db: Session, playlist_id: int):
    playlist = db.query(Playlist).get(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейліст не знайдено.")
    return playlist

def create_playlist(db: Session, playlist: PlaylistCreate):
    new_playlist = Playlist(**playlist.dict())
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    return new_playlist

def update_playlist(db: Session, playlist_id: int, playlist_data: PlaylistCreate):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейліст не знайдено.")
    playlist.title = playlist_data.title
    playlist.avatar = playlist_data.avatar
    playlist.user_id = playlist_data.user_id
    db.commit()
    db.refresh(playlist)
    return playlist

def add_track_to_playlist(db: Session, playlist_id: int, track_id: int):
    playlist = get_playlist(db, playlist_id)
    track = get_track(db, track_id)
    if track in playlist.tracks:
        raise HTTPException(status_code=400, detail="Трек уже є в плейлисті.")
    playlist.tracks.append(track)
    db.commit()
    db.refresh(playlist)
    return playlist

def remove_track_from_playlist(db: Session, playlist_id: int, track_id: int):
    playlist = get_playlist(db, playlist_id)
    track = get_track(db, track_id)
    if track not in playlist.tracks:
        raise HTTPException(status_code=404, detail="Трек не знайдений у плейлисті.")
    playlist.tracks.remove(track)
    db.commit()
    db.refresh(playlist)
    return playlist
