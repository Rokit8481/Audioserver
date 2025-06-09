from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

playlist_tracks = Table(
    "playlist_tracks",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id")),
    Column("track_id", Integer, ForeignKey("tracks.id"))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, index = True)
    login = Column(String, unique = True, index = True)
    avatar = Column(String, unique = False, nullable=True)
    password = Column(String)

    playlists = relationship("Playlist", back_populates="user")

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key = True, index = True)
    title = Column(String, unique = False, index = True)
    avatar = Column(String, unique = False, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="playlists")
    tracks = relationship("Track", secondary=playlist_tracks, back_populates="playlists")

class Track(Base):
    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    file_url = Column(String)
    avatar = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey("authors.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    author = relationship("Author", back_populates = "tracks")
    playlists = relationship("Playlist", secondary = playlist_tracks, back_populates = "tracks")

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, unique = True, index = True)
    avatar = Column(String, unique = False, nullable=True)

    tracks = relationship("Track", back_populates = "author")

