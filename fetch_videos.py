import os
import json
import csv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']#
# SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']#
csvs_path = './csvs'

_TOKEN='token_old_account.json'

def authenticate_youtube():
    creds = None
    if os.path.exists(_TOKEN):
        creds = Credentials.from_authorized_user_file(_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_playlists(limit=50, include_system_playlists=True):
    creds = authenticate_youtube()
    youtube = build('youtube', 'v3', credentials=creds)

    playlists = []
    next_page_token = None
    fetched_playlists = 0

    # Fetch user-created playlists
    while True:
        request = youtube.playlists().list(
            part='snippet,contentDetails',
            mine=True,
            maxResults=limit,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            playlist_id = item['id']
            playlist_title = item['snippet']['title']
            item_count = item['contentDetails']['itemCount']
            playlist_url = "https://www.youtube.com/playlist?list=" + playlist_id
            playlists.append({
                'title': playlist_title,
                'id': playlist_id,
                'url': playlist_url,
                'item_count': item_count,
                'fetched_videos': 0,
                'platform': 'youtube'  # Assuming 'youtube' by default since API doesn't specify
            })
            fetched_playlists += 1

        next_page_token = response.get('nextPageToken')
        if not next_page_token or fetched_playlists >= limit:
            break

    # Optionally include system playlists (Watch Later and Liked Videos)
    if include_system_playlists:
        system_playlists = [
            {'title': 'Watch Later', 'id': 'WL', 'platform': 'youtube', 'url': 'https://www.youtube.com/playlist?list=WL'},
            {'title': 'Liked Videos', 'id': 'LL', 'platform': 'youtube', 'url': 'https://www.youtube.com/playlist?list=LL'}
            
        ]
        for sys_playlist in system_playlists:
            # Fetch item count for system playlists
            item_count = get_playlist_item_count(sys_playlist['id'])
            sys_playlist['item_count'] = item_count
            sys_playlist['fetched_videos'] = 0  # Set to 0, to be updated later
            playlists.append(sys_playlist)

    return playlists

def get_playlist_item_count(playlist_id):
    """
    Fetch the item count for system playlists like 'Watch Later' and 'Liked Videos'.
    """
    creds = authenticate_youtube()
    youtube = build('youtube', 'v3', credentials=creds)
    
    request = youtube.playlistItems().list(
        part='id',
        playlistId=playlist_id,
        maxResults=0  # We are only interested in getting the item count
    )
    response = request.execute()
    return response.get('pageInfo', {}).get('totalResults', 0)

def load_playlists_from_csv(filename=f'{csvs_path}/playlists_updated.csv'):
    if not os.path.exists(filename):
        return []
    with open(filename, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return list(reader)

def save_playlists_to_csv(playlists, filename=f'{csvs_path}/playlists_updated.csv'):
    keys = playlists[0].keys()
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(playlists)

def get_videos_from_playlist(playlist_id, playlist_name):
    creds = authenticate_youtube()
    youtube = build('youtube', 'v3', credentials=creds)

    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            maxResults=50,
            playlistId=playlist_id,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            video_id = item['snippet']['resourceId']['videoId']
            video_title = item['snippet']['title']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({
                'title': video_title,
                'video_id': video_id,
                'url': video_url,
                'playlist': playlist_name,
                'playlist_id': playlist_id
            })

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return videos

def save_videos_to_csv(videos, filename):
    if not videos:
        return  # Don't attempt to save empty videos
    keys = videos[0].keys()
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(videos)

def load_videos_from_csv(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return list(reader)

if __name__ == '__main__':
    print("Fetching playlists")
    
    if not os.path.exists(csvs_path):
        os.mkdir(csvs_path)

    # Fetch the playlists and check against the saved data, including system playlists
    playlists = get_playlists(limit=50, include_system_playlists=True)
    saved_playlists = load_playlists_from_csv()

    for playlist in playlists:
        print(f"\nChecking playlist: {playlist['title']}, ID: {playlist['id']}")

        # Check if the playlist already exists in the saved CSV
        saved_playlist = next((p for p in saved_playlists if p['id'] == playlist['id']), None)

        video_filename_prefix = f"{csvs_path}/videos_{playlist['title']}__{playlist['id']}.csv"
        saved_videos = load_videos_from_csv(video_filename_prefix)

        if saved_playlist:
            saved_fetched_videos = int(saved_playlist['fetched_videos'])
            item_count = int(playlist['item_count'])

            # If the number of fetched videos is the same as item_count, skip fetching
            if saved_fetched_videos == item_count and len(saved_videos) == item_count:
                print(f"'{playlist['title']}' is up-to-date. No need to fetch videos.")
                continue
            else:
                missing_videos = item_count - saved_fetched_videos
                if missing_videos > 0:
                    print(f"'{playlist['title']}' is missing {missing_videos} videos. Updating...")
                else:
                    print(f"'{playlist['title']}' has {abs(missing_videos)} new videos. Updating...")

        # Fetch the videos for the playlist
        videos = get_videos_from_playlist(playlist['id'], playlist['title'])
        
        # Check if there are any videos to save
        if videos:
            # Save the videos to a CSV
            save_videos_to_csv(videos, video_filename_prefix)
            print(f"Saved {len(videos)} videos to {video_filename_prefix}")
        else:
            print(f"No videos found for playlist: {playlist['title']}")

        # Update the playlist with the number of fetched videos
        playlist['fetched_videos'] = len(videos)

    # Save updated playlists with fetched video counts
    save_playlists_to_csv(playlists)
    print("\nPlaylists and videos have been updated.")
