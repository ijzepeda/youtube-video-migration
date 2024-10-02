
# YouTube Playlist Migrator

This project is a **YouTube Playlist Migrator** built with Google API to transfer playlists from one YouTube account to another. It allows users to log in to two YouTube accounts (source and destination), view playlists, and migrate selected playlists between the accounts.
Currently working on the UI using [Streamlit](https://streamlit.io/) and Tkinter.

## Features

- **Login to Two Accounts**: Authenticate with both the source (old) and destination (new) YouTube accounts.
- **View Playlists**: Display playlists from both accounts.
- **Migrate Playlists**: Select playlists from the old account to migrate to the new account.
- **Token Persistence**: The authentication tokens are saved locally for easy reuse without needing to log in every time.

## Technologies

- **Python**: Main programming language.
- **Streamlit**: For building the user interface.
- **Google API Client**: To interact with YouTube's Data API for fetching and migrating playlists.

## Setup Instructions

### Prerequisites

1. **Python 3.x**: Make sure Python is installed on your system.
2. **Google Cloud Project**: Set up a Google Cloud project with access to the YouTube Data API.
   - Enable the [YouTube Data API v3](https://console.developers.google.com/apis/library/youtube.googleapis.com).
   - Create OAuth credentials and download the `client_secret.json` file.

### Dependencies
- streamlit
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client

### Structure
youtube-video-migration/
├── csvs/               # Folder to store CSVs related to playlists and videos
├── session_ks/         # Session tokens and client secret for OAuth
│   ├── token_old_account.json
│   ├── token_new_account.json
│   └── client_secret.json
├── fetch_video.py      # retrieve playlists and videos from old/original account. Saves them on CSV
├── youtube_migrator.py # create playlists and add videos to the new account
├── requirements.txt    # Dependencies
└── README.md           # This README file

