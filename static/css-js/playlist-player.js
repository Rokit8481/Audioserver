let globalPlayer = null;
let isPlaying = false;
let currentIndex = -1;
let playlist = [];

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".card.track").forEach(track => {
    playlist.push({
      url: track.dataset.url,
      title: track.dataset.title,
      cover: track.querySelector("img").src,
      author: track.querySelector(".track-author").textContent.trim()
    });
  });

  document.querySelectorAll(".track-play-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const index = parseInt(btn.dataset.index);
      if (currentIndex === index) {
        toggleGlobalPlay(); 
      } else {
        playPlaylistTrack(index);
      }
    });
  });
  
  const form = document.getElementById("addTrackForm");
  const select = document.getElementById("track_id");

  if (form && select) {
    const playlistId = form.dataset.playlistId;

    select.addEventListener("change", () => updateAddFormAction(playlistId));

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const trackId = select.value;

      try {
        const res = await fetch(`/playlist/${playlistId}/add_track/${trackId}`, {
          method: "POST"
        });

        if (res.ok) {
          location.reload();
        } else {
          const data = await res.json();
          alert("❌ " + (data.detail || "Помилка додавання"));
        }
      } catch (err) {
        alert("❌ Не вдалося надіслати запит");
      }
    });
  }

  document.querySelectorAll(".remove-track-btn").forEach(button => {
    button.addEventListener("click", async (e) => {
      e.preventDefault();

      const playlistId = button.dataset.playlistId;
      const trackId = button.dataset.trackId;

      try {
        const res = await fetch(`/playlist/${playlistId}/remove_track/${trackId}`, {
          method: "POST"
        });

        if (res.ok) {
          location.reload();
        } else {
          const data = await res.json();
          alert("❌ " + (data.detail || "Помилка видалення"));
        }
      } catch (err) {
        alert("❌ Не вдалося надіслати запит");
      }
    });
  });
});

function playPlaylistTrack(index) {
  const playerContainer = document.getElementById("global-player");
  const trackTitle = document.getElementById("global-track-title");
  const playButton = document.getElementById("global-play");
  const coverImg = document.getElementById("player-cover");
  const authorText = document.getElementById("global-track-author");

  if (!playlist[index]) return;

  document.getElementById("waveform-global").classList.remove("waveform-hidden");

  if (currentIndex === index && globalPlayer) {
    toggleGlobalPlay();
    return;
  }

  trackTitle.textContent = playlist[index].title;
  coverImg.src = playlist[index].cover;
  authorText.textContent = playlist[index].author;

  if (globalPlayer) globalPlayer.destroy();
  
  globalPlayer = WaveSurfer.create({
    container: "#waveform-global",
    waveColor: "#ccc",
    progressColor: "#1db954",
    height: 64,
    barWidth: 2,
    responsive: true,
  });

  globalPlayer.load(playlist[index].url);
  globalPlayer.on("ready", () => {
    globalPlayer.play();
    isPlaying = true;

    const playButtonImg = playButton.querySelector("img");
    if (playButtonImg) {
      playButtonImg.src = "/static/icons/pause.png";
      playButtonImg.alt = "pause";
    }

    document.querySelectorAll(".track-play-btn").forEach((btn, i) => {
      const img = btn.querySelector("img");
      if (img) {
        img.src = i === index ? "/static/icons/pause.png" : "/static/icons/play.png";
        img.alt = i === index ? "pause" : "play";
      }
    });

    currentIndex = index;
  });

  globalPlayer.on("finish", () => nextTrack());
}

function toggleGlobalPlay() {
  const playButtonImg = document.getElementById("global-play")?.querySelector("img");
  if (!globalPlayer || !playButtonImg) return;

  if (globalPlayer.isPlaying()) {
    globalPlayer.pause();
    playButtonImg.src = "/static/icons/play.png";
    playButtonImg.alt = "play";

    updateTrackPlayIcons(false);
  } else {
    globalPlayer.play();
    playButtonImg.src = "/static/icons/pause.png";
    playButtonImg.alt = "pause";

    updateTrackPlayIcons(true);
  }

  isPlaying = !isPlaying;
}

function updateTrackPlayIcons(isPlayingNow) {
  document.querySelectorAll(".track-play-btn").forEach((btn, i) => {
    const img = btn.querySelector("img");
    if (img) {
      if (i === currentIndex) {
        img.src = isPlayingNow ? "/static/icons/pause.png" : "/static/icons/play.png";
        img.alt = isPlayingNow ? "pause" : "play";
      } else {
        img.src = "/static/icons/play.png";
        img.alt = "play";
      }
    }
  });
}

function nextTrack() {
  if (currentIndex + 1 < playlist.length) {
    playPlaylistTrack(currentIndex + 1);
  }
}

function previousTrack() {
  if (currentIndex > 0) {
    playPlaylistTrack(currentIndex - 1);
  }
}

function setVolume(value) {
  if (globalPlayer) {
    globalPlayer.setVolume(parseFloat(value));
  }
}

function updateAddFormAction(playlistId) {
  const select = document.getElementById("track_id");
  const form = select.closest("form");
  const trackId = select.value;
  form.action = `/playlist/${playlistId}/add_track/${trackId}`;
}
