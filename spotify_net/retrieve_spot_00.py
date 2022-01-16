# AUTOGENERATED! DO NOT EDIT! File to edit: 00_retrieve_spot.ipynb (unless otherwise specified).

__all__ = ['cred', 'get_tracks', 'track_reduce', 'update']

# Cell
import requests
import base64
import json
import pandas as pd
import boto3
import math

from datetime import date, timedelta

# Cell
def cred():
    secret_name = "spotify_35"
    region_name = "us-east-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    client_id = json.loads(get_secret_value_response['SecretString'])['spot_clientID']
    client_secret = json.loads(get_secret_value_response['SecretString'])['spot_clientSECRET']
    access_token = json.loads(get_secret_value_response['SecretString'])['spot_ACC']
    refresh_token = json.loads(get_secret_value_response['SecretString'])['spot_REF']

    return client_id, client_secret, access_token, refresh_token

# Cell
def get_tracks(p_id, access_token, refresh_token, client_id, client_secret):

    df_tracks = pd.DataFrame()

    curr_len = 0
    offset = 0

    while len(df_tracks) % 100 == 0:


        track_url = f'https://api.spotify.com/v1/playlists/{p_id}/tracks?limit=100&offset={offset}'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        r_track = requests.get(track_url, headers=headers)

        if r_track.status_code == 401:

            TOKEN_URL = 'https://accounts.spotify.com/api/token'

            message = client_id + ':' + client_secret
            messageBytes = message.encode('ascii')
            base64Bytes = base64.b64encode(messageBytes)
            base64Message = base64Bytes.decode('ascii')

            headers = {
            'Authorization': 'Basic ' + base64Message,
            'Content-Type': 'application/x-www-form-urlencoded'
            }

            pars_refresh = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'redirect_uri': 'http://localhost:8888/callback',
            }

            r_refresh = requests.post(TOKEN_URL, headers=headers, params=pars_refresh)
            access_token = r_refresh.json()['access_token']

            headers = {
            'Authorization': f'Bearer {access_token}'
                    }

            r_track = requests.get(track_url, headers=headers)

        track_ids = [t['track']['id'] for t in r_track.json()['items']]
        track_names = [t['track']['name'] for t in r_track.json()['items']]
        track_added = [t['added_at'] for t in r_track.json()['items']]
        track_artists = [t['track']['artists'][0]['name'] for t in r_track.json()['items']]
        artist_id = [t['track']['artists'][0]['id'] for t in r_track.json()['items']]

        df_t = pd.DataFrame({
            'added at': pd.to_datetime(track_added),
            'id': track_ids,
            'name': track_names,
            'artist': track_artists,
            'artist id': artist_id,
            'playlist id': p_id

        },
        # index=pd.to_datetime(track_added)
        )

        join_ids = ','.join(track_ids)
        feat_url = f'https://api.spotify.com/v1/audio-features?limit=100&offset={offset}&ids={join_ids}'
        r_feat = requests.get(feat_url, headers=headers)
        feat_frame = pd.DataFrame(r_feat.json()['audio_features'])

        df_t = pd.merge(df_t, feat_frame, on='id')
        df_tracks = df_tracks.append(df_t)

        if curr_len == len(df_tracks):
            break
        else:
            curr_len = len(df_tracks)

        offset += 100

    df_tracks = df_tracks.drop_duplicates()

    artist_list = df_tracks['artist id'].tolist()
    genre_list = []
    index = 0
    temp_list = artist_list[index: index+50]

    for i in range(math.ceil(len(artist_list)/50)):
        artist_join = ','.join(temp_list)
        art_url = f'https://api.spotify.com/v1/artists?ids={artist_join}'
        r_art = requests.get(art_url, headers=headers)
        print(r_art.status_code)

        try:
            g = [i['genres'] for i in r_art.json()['artists']]
        except IndexError:
            g = ['No Genre']

        genre_list.extend(g)
        index += 50
        temp_list = artist_list[index: index+50]


    g_ser = pd.Series(genre_list, index=df_tracks.index)
    trimmed_g = g_ser.apply(lambda x: x[:3])

    df_tracks['genre'] = trimmed_g

    genre_bin = pd.get_dummies(df_tracks['genre'].explode())
    genre_bin = genre_bin.groupby(level=0).sum()
    genre_bin = genre_bin.add_prefix('genre_')

    df_tracks = df_tracks.drop('genre', axis=1)
    df_tracks = pd.concat([df_tracks, genre_bin], axis=1)


    return df_tracks

# Cell
def track_reduce(d_tracks, include=30):
    d_tracks = d_tracks.sort_values('added at')
    today = date.today()
    today = pd.to_datetime(today, utc=True)
    d_tracks['diff'] = d_tracks['added at'].apply(lambda x: today-x)
    period = timedelta(days=include)
    d_tracks = d_tracks[d_tracks['diff'].apply(lambda x: x <= period)]
    d_tracks = d_tracks.sort_values('diff')

    return d_tracks


# Cell
def update(p_id, access_token, refresh_token, client_id, client_secret, o_tracks, n_tracks):

    headers = {
            'Authorization': f'Bearer {access_token}'
                    }

    DELETE_URL = f'https://api.spotify.com/v1/playlists/{p_id}/tracks'

    to_delete = o_tracks.loc[~o_tracks['id'].isin(n_tracks['id']), 'id'].tolist()

    x = len(to_delete)
    y = math.ceil(x/100)
    # r_delete = None

    if x != 0:
        for i in range(0, y*100, 100):
            delete_uris  = to_delete[i:(i+100)]
            del_uri = []
            for i in delete_uris:
                del_uri.append(
                    {'uri': i}
                )
            del_dict = {'tracks': del_uri}

            r_delete = requests.delete(DELETE_URL, headers=headers, data=json.dumps(del_dict))

        if r_delete.status_code == 401:

                TOKEN_URL = 'https://accounts.spotify.com/api/token'

                message = client_id + ':' + client_secret
                messageBytes = message.encode('ascii')
                base64Bytes = base64.b64encode(messageBytes)
                base64Message = base64Bytes.decode('ascii')

                headers = {
                'Authorization': 'Basic ' + base64Message,
                'Content-Type': 'application/x-www-form-urlencoded'
                }

                pars_refresh = {
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'redirect_uri': 'http://localhost:8888/callback',
                }

                r_refresh = requests.post(TOKEN_URL, headers=headers, params=pars_refresh)
                access_token = r_refresh.json()['access_token']

                headers = {
                'Authorization': f'Bearer {access_token}'
                        }

                for i in range(0, y*100, 100):
                    delete_uris  = to_delete[i:(i+100)]
                    del_uri = []
                    for i in delete_uris:
                        del_uri.append(
                            {'uri': i}
                        )
                    del_dict = {'tracks': del_uri}

                    r_delete = requests.delete(DELETE_URL, headers=headers, data=json.dumps(del_dict))

# Cell
if __name__ == '__main__':
    c_id, c_secret, a_token, r_token = cred()
    o_tracks = get_tracks('3ubgXaHeBn1CWLUZPXvqkj', a_token, r_token, c_id, c_secret)
    n_tracks = track_reduce(o_tracks, include=30)
    n_tracks.to_csv('s3://spotify-net/newer_tracks.csv')
    _ = update('3ubgXaHeBn1CWLUZPXvqkj', a_token, r_token, c_id, c_secret, o_tracks, n_tracks)
    print('Updated')