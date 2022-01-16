# AUTOGENERATED! DO NOT EDIT! File to edit: 04_lambda.ipynb (unless otherwise specified).

__all__ = ['handler']

# Cell
import requests
import base64
import json
import pandas as pd
import boto3
import math

# Cell
try:
    import spotify_net.retrieve_spot_00 as spot
    import spotify_net.retrieve_last_01 as last
    import spotify_net.prepModel_02 as prep
    import spotify_net.hit_endpoint_03 as hit
except ModuleNotFoundError:
    import retrieve_spot_00 as spot
    import retrieve_last_01 as last
    import prepModel_02 as prep
    import hit_endpoint_03 as hit

# Cell
def handler(event, context):
    # Get spotify tracks
    c_id, c_secret, a_token, r_token = spot.cred()
    o_tracks = spot.get_tracks('3ubgXaHeBn1CWLUZPXvqkj', a_token, r_token, c_id, c_secret)
    n_tracks = spot.track_reduce(o_tracks, include=30)
    n_tracks.to_csv('s3://spotify-net/newer_tracks.csv')
    _ = spot.update('3ubgXaHeBn1CWLUZPXvqkj', a_token, r_token, c_id, c_secret, o_tracks, n_tracks)
    print('Retrieved net from Spotify')

    # Get last fm tracks
    API_KEY, USER_AGENT, USERNAME = last.last_cred()
    tracks = last.last_get('user.gettoptracks', USER_AGENT, USERNAME, API_KEY)
    formatted = last.last_format(tracks, 7)
    formatted.to_csv('s3://spotify-net/df_tracks.csv')
    print('Retrieved top recent from Last FM')

    # Combine and prep for model
    s3_objects = prep.load_s3()
    merged_df = prep.merge_frame(s3_objects['spot_tracks'], s3_objects['last_tracks'])
    transformed = prep.dummies_and_scale(merged_df, 0.0000001, s3_objects['scaler'])
    _ = prep.full_frame(transformed, s3_objects['gen_series'], s3_objects['svd'], s3_objects['key_series'], s3_objects['time_series'])

    # Get predictions
    df = hit.load_s3()
    name_frame = df[['name', 'uri', 'artist']].copy()
    df_json = hit.prep_frame(df)

    df_list = []
    index=0
    for i in range(math.ceil(len(df)/3)):
        temp_json = hit.prep_frame(df.iloc[index:index+3])
        preds = requests.post(f'https://72fe4ffwc6.execute-api.us-east-1.amazonaws.com/dev/model/{temp_json}')
        preds = pd.read_json(preds.json()[0])
        index += 3
        df_list.append(preds)

    pred_frame = pd.concat(t_list, ignore_index=True)
    pred_frame = pred_frame.rename(columns={0:'predictions'})
    name_frame = pd.concat([name_frame, pred_frame], axis=1)
    name_frame = name_frame.iloc[:2]
    print(name_frame)

    # Add to playlist, delete from net
    client_id, client_secret, access_token, refresh_token = hit.cred()
    _ = hit.add_tracks(name_frame, client_id, client_secret, access_token, refresh_token)
    _ = hit.delete_tracks(name_frame, client_id, client_secret, access_token, refresh_token)

    return 'Success'

# Cell
if __name__ == '__main__':
    try:
        _ = handler(event, context)
    except NameError:
        print('No event')