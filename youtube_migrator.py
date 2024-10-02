import os
import csv
import logging
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError  # Import HttpError to handle API exceptions


# YouTube API scope for creating playlists and adding videos
SCOPES = ['https://www.googleapis.com/auth/youtube']
csvs_path = './csvs'
SESSION='./session/'
_TOKEN=SESSION+'token_new_account.json'
CLIENT_SECRET=SESSION+'client_secret.json'


# Setup logging
log_filename = 'youtube_migration.log'
logging.basicConfig(
    level=logging.INFO,  # Set the log level
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

def authenticate_youtube():
    creds = None
    if os.path.exists(_TOKEN):
        creds = Credentials.from_authorized_user_file(_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN, 'w') as token:
            token.write(creds.to_json())
    logging.info("Authentication successful.")
    return creds

def playlist_exists(youtube, title):
    """Check if a playlist with the given title already exists."""
    request = youtube.playlists().list(
        part='snippet',
        mine=True,
        maxResults=50
    )
    response = request.execute()
    
    for playlist in response['items']:
        if playlist['snippet']['title'] == title:
            logging.info(f"Playlist '{title}' already exists with ID: {playlist['id']}")
            return playlist['id']
    logging.info(f"Playlist '{title}' does not exist.")
    return None

def create_playlist(youtube, title, description="Imported playlist", privacy="private"):
    """Creates a new playlist for the authenticated user."""
    request_body = {
        'snippet': {
            'title': title,
            'description': description
        },
        'status': {
            'privacyStatus': privacy  # 'private', 'public', or 'unlisted'
        }
    }
    response = youtube.playlists().insert(
        part="snippet,status",
        body=request_body
    ).execute()

    logging.info(f"Created playlist: {title}")
    return response['id']  # Returns the ID of the newly created playlist

def video_exists_in_playlist(youtube, playlist_id, video_id):
    """Check if a video already exists in the playlist."""
    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()
    
    for item in response['items']:
        if item['snippet']['resourceId']['videoId'] == video_id:
            logging.info(f"Video {video_id} already exists in playlist {playlist_id}") # long log after second run <<<<<<
            return True
    return False

def add_video_to_playlist(youtube, playlist_id, video_id):
    """Adds a video to the specified playlist if it doesn't already exist."""
    try:
        if not video_exists_in_playlist(youtube, playlist_id, video_id):
            request_body = {
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
            youtube.playlistItems().insert(
                part="snippet",
                body=request_body
            ).execute()
            # logging.info(f"Added video {video_id} to playlist {playlist_id}")
        else:
            logging.info(f"Skipped adding video {video_id} since it is already in playlist {playlist_id}")
    except HttpError as e:
        if e.resp.status == 404:
            logging.error(f"Video {video_id} not found. Skipping this video.")
        else:
            logging.error(f"Failed to add video {video_id}. Error: {e}")
        # Optionally: save the failed video details to a file for later review
        with open('failed_videos.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([video_id, playlist_id, str(e)])

def like_video(youtube, video_id):
    """Likes a video by using the videos.rate endpoint."""
    try:
        youtube.videos().rate(
            id=video_id,
            rating="like"
        ).execute()
        # logging.info(f"Liked video {video_id}")
    except HttpError as e:
        if e.resp.status == 404:
            logging.error(f"Video {video_id} not found when trying to like it.")
        else:
            logging.error(f"Failed to like video {video_id}. Error: {e}")
        with open('failed_liked_videos.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([video_id, str(e)])

def load_playlists_from_csv(csv_file):
    """Loads the playlists from the specified CSV file."""
    playlists = []
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            playlists.append(row)
    logging.info(f"Loaded {len(playlists)} playlists from {csv_file}.")
    return playlists

def load_videos_from_csv(csv_file):
    """Loads the videos from the specified CSV file."""
    videos = []
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            videos.append(row)
    logging.info(f"Loaded {len(videos)} videos from {csv_file}.")
    return videos

if __name__ == '__main__':
    start_time = time.time()

    # Authenticate the new user
    youtube = build('youtube', 'v3', credentials=authenticate_youtube())

    # Load playlists from the CSV file
    playlists = load_playlists_from_csv(f'{csvs_path}/playlists_updated.csv')

    # For each playlist in the CSV, check if it exists, create if not, and add videos
    for playlist in playlists:
        title = playlist['title']
        platform = playlist['platform']

        # Determine if the playlist is from YouTube or YouTube Music
        if platform == 'music':
            title = f"YM__{title}"  # Add 'm_' prefix to differentiate YouTube Music playlists
            description = "Imported from YouTube Music"
        else:
            description = "Imported from YouTube"

        # Handle Liked Videos separately (do not create a new playlist for 'LL')
        if playlist['id'] == 'LL':
            logging.info("Processing 'Liked Videos'...")
            csv_video_filename = f"{csvs_path}/videos_Liked Videos__LL.csv"
            if os.path.exists(csv_video_filename):
                videos = load_videos_from_csv(csv_video_filename)
                logging.info(f"Total number of liked videos: {len(videos)}")
                for video in videos:
                    video_id = video['video_id']
                    like_video(youtube, video_id)  # Process and log in batches
            else:
                logging.warning(f"Video CSV for 'Liked Videos' not found.")
            continue  # Skip to the next playlist since 'LL' does not require creating a new playlist

        # Check if the playlist already exists, if not, create it
        playlist_id = playlist_exists(youtube, title)
        if not playlist_id:
            playlist_id = create_playlist(youtube, title, description=description, privacy="private")
        else:
            logging.info(f"Playlist {title} already exists.")
            continue #avoid processing that playlist, 

        # Load the videos from the corresponding CSV file
        csv_video_filename = f"{csvs_path}/videos_{playlist['title']}__{playlist['id']}.csv"
        if os.path.exists(csv_video_filename):
            videos = load_videos_from_csv(csv_video_filename)
            for video in videos:
                video_id = video['video_id']
                add_video_to_playlist(youtube, playlist_id, video_id) # Too many requests to the API
        else:
            logging.warning(f"Video CSV for playlist {title} not found.")

    end_time = time.time()
    total_time = end_time - start_time
    logging.info(f"Process completed in {total_time:.2f} seconds.")
