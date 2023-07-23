# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_retrieve_spotify_data.ipynb.

# %% auto 0
__all__ = ['SpotifyAPI']

# %% ../nbs/00_retrieve_spotify_data.ipynb 3
import requests
import base64
import json
import pandas as pd
import boto3
import math
import os

from datetime import date, timedelta

# %% ../nbs/00_retrieve_spotify_data.ipynb 4
class SpotifyAPI:
    
    # do I want to initialize this list with the innstance of leave as-is?
    required_env_keys = ['spot_clientID', 'spot_clientSECRET', 'spot_ACC', 'spot_REF']

    def __init__(self, region_name):
        self.region_name = region_name
        self.playlist_id = None
        self.df_tracks = pd.DataFrame()
        
    def get_secret(self, secret_name):
        if all([k in os.environ.keys() for k in self.required_env_keys]):
            print('All required environment variables are set')
        else:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.region_name
            )
            secret_value = client.get_secret_value(
                SecretId=secret_name
            )
            secret_dict = json.loads(secret_value['SecretString'])
            for k, v in secret_dict.items():
                os.environ[k] = v

    def create_headers(self):
        return {
            'Authorization': f'Bearer {os.environ.get("spot_ACC")}'
        }

    def refresh_token(self):
        TOKEN_URL = 'https://accounts.spotify.com/api/token'

        message = os.environ.get('spot_clientID') + ':' + os.environ.get('spot_clientSECRET')
        messageBytes = message.encode('ascii')
        base64Bytes = base64.b64encode(messageBytes)
        base64Message = base64Bytes.decode('ascii')

        headers = {
            'Authorization': 'Basic ' + base64Message,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        pars_refresh = {
            'grant_type': 'refresh_token',
            'refresh_token': os.environ.get('spot_REF'),
            'redirect_uri': 'http://localhost:8888/callback',
        }

        r_refresh = requests.post(TOKEN_URL, headers=headers, params=pars_refresh)
        access_token = r_refresh.json()['access_token']
        os.environ['spot_ACC'] = access_token

    def get_track_subset(self, playlist_id, offset):
        track_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=100&offset={offset}'
        headers = self.create_headers()
        track_subset = requests.get(track_url, headers=headers)

        if track_subset.status_code == 401:
            self.refresh_token()
            headers = self.create_headers()
            track_subset = requests.get(track_url, headers=headers)
        
        return track_subset.json()['items']
    
    def get_subset_features(self, track_items):
            track_ids = [t['track']['id'] for t in track_items]
            track_names = [t['track']['name'] for t in track_items]
            track_added = [t['added_at'] for t in track_items]
            track_artists = [t['track']['artists'][0]['name'] for t in track_items]
            artist_id = [t['track']['artists'][0]['id'] for t in track_items]

            track_info = pd.DataFrame({
                'added at': pd.to_datetime(track_added),
                'id': track_ids,
                'name': track_names,
                'artist': track_artists,
                'artist id': artist_id,
            })

            track_id_list = ','.join(track_ids)
            feat_url = f'https://api.spotify.com/v1/audio-features?ids={track_id_list}'
            headers = self.create_headers()
            r_feat = requests.get(feat_url, headers=headers)
            feat_frame = pd.DataFrame(r_feat.json()['audio_features'])
            track_features = pd.concat([track_info, feat_frame], axis=1)

            return track_features 

    def get_playlist_features(self, playlist_id):
        
        offset = 0

        while True:
            subset = self.get_track_subset(playlist_id, offset)
            self.df_tracks = self.df_tracks.append(self.get_subset_features(subset))

            if len(self.df_tracks) < 100:  # less than 100 tracks in the response, we've fetched all tracks
                break

            offset += 100

        self.df_tracks = self.df_tracks.drop_duplicates()

    
    def get_artist_info(self, df_tracks, headers):
        pass

    def process_genres(self, df_tracks):
        pass

    def parse_new_tracks(self, lookback_days=7):
        """
        Sorts tracks based on when they were added. Filters out tracks added more than 'lookback_days' ago.
        Returns the original DataFrame of tracks.
        """
        self.df_tracks = self.df_tracks.sort_values('added at')
        today = pd.to_datetime(date.today(), utc=True)

        # Calculate the time difference between track addition and 'today'
        self.df_tracks['diff'] = self.df_tracks['added at'].apply(lambda x: today - x)
        lookback_period = timedelta(days=lookback_days)

        # Filter tracks based on the lookback period
        new_tracks = self.df_tracks[self.df_tracks['diff'].apply(lambda x: x <= lookback_period)]
        old_tracks = self.df_tracks[self.df_tracks['diff'].apply(lambda x: x > lookback_period)]

        return old_tracks, new_tracks

    def delete_tracks(self, tracks_to_delete):
        """
        Deletes a batch of tracks from a Spotify playlist.
        Accepts a DataFrame of tracks to delete
        """
        to_delete = tracks_to_delete['uri'].tolist()  # Assuming 'uri' is the column name in your DataFrame
        num_tracks = len(to_delete)
        num_batches = math.ceil(num_tracks/100)

        for i in range(0, num_batches*100, 100):
            delete_uris = to_delete[i:(i+100)]
            uri_dict = [{'uri': uri} for uri in delete_uris]
            del_dict = {'tracks': uri_dict}
            headers = self.create_headers()
            DELETE_URL = f'https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks'
            r_delete = requests.delete(DELETE_URL, data=json.dumps(del_dict))

# %% ../nbs/00_retrieve_spotify_data.ipynb 5
if __name__ == '__main__':
    spot = SpotifyAPI('us-east-2')
    spot.get_secret('spotify_35')
    spot.get_playlist_features('3ubgXaHeBn1CWLUZPXvqkj')
    old_tracks, new_tracks = spot.parse_new_tracks(lookback_days=7)
    new_tracks.to_csv('s3://spotify-net/newer_tracks.csv')
    spot.delete_tracks(old_tracks)
    print('Updated')
