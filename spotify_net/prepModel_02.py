# AUTOGENERATED! DO NOT EDIT! File to edit: 02_prepModel.ipynb (unless otherwise specified).

__all__ = ['load_s3', 'merge_frame', 'dummies_and_scale', 'full_frame']

# Cell
import pandas as pd
import requests
import boto3
import json
from io import BytesIO
import joblib
import pickle
import numpy as np
pd.set_option('display.max_columns', None)

# Cell
def load_s3():

    s3_resource = boto3.resource('s3')

    scaler = s3_resource.Object('spotify-net', 'scaler').get()
    scaler = pickle.loads(scaler['Body'].read())

    svd = s3_resource.Object('spotify-net', 'svd').get()
    svd = pickle.loads(svd['Body'].read())

    spot_tracks = pd.read_csv('s3://spotify-net/newer_tracks.csv', index_col=0)
    last_tracks = pd.read_csv('s3://spotify-net/df_tracks.csv', index_col=0)

    gen_series = pd.read_csv('s3://spotify-net/genres_svd.csv', index_col=0, squeeze=True)
    key_series = pd.read_csv('s3://spotify-net/key_list.csv', index_col=0, squeeze=True)
    time_series = pd.read_csv('s3://spotify-net/timeSig_list.csv', index_col=0, squeeze=True)

    s3_dict = {
        'scaler': scaler,
        'svd': svd,
        'spot_tracks': spot_tracks,
        'last_tracks': last_tracks,
        'gen_series': gen_series,
        'key_series': key_series,
        'time_series': time_series
    }

    return s3_dict


# Cell
def merge_frame(spot_tracks, last_tracks):
    spot_tracks[['name', 'artist']] = spot_tracks[['name', 'artist']].applymap(lambda x: x.upper())
    last_tracks[['name', 'artist']] = last_tracks[['name', 'artist']].applymap(lambda x: x.upper())

    df_classify = pd.merge(last_tracks, spot_tracks, on=['name', 'artist'])
    to_drop = ['playcount', 'added at', 'artist id', 'id', 'playlist id', 'type', 'track_href', 'analysis_url', 'type', 'diff']
    df_classify = df_classify.drop(to_drop, axis=1)

    return df_classify


# Cell
def dummies_and_scale(df_classify, constant, scaler):
   # log-transform
   # c = 0.0000001
    c=constant
    df_classify[['speechiness', 'acousticness', 'instrumentalness']] = df_classify[['speechiness', 'acousticness', 'instrumentalness']] + c
    df_classify[['speechiness', 'acousticness', 'instrumentalness']] = np.log(df_classify[['speechiness', 'acousticness', 'instrumentalness']])

   # one-hot
    df_track = pd.get_dummies(df_classify , prefix=['key', 'time_signature'], columns=['key', 'time_signature'])

   # standardScaler
    scale_col = ['danceability', 'energy', 'loudness',
       'speechiness', 'acousticness', 'instrumentalness', 'liveness',
       'valence', 'tempo', 'duration_ms']
    df_track[scale_col].head()
    df_track[scale_col] = scaler.transform(df_track[scale_col])

    return df_track

# Cell
def full_frame(df_track, gen_series, svd, key_series, time_series):

    curr_gen = df_track.loc[:, df_track.columns.str.startswith('genre_')]
    full_gen = pd.DataFrame(np.zeros((len(df_track), len(gen_series.tolist()))) , columns=gen_series.tolist())
    full_gen = full_gen.add_prefix('genre_')
    full_gen.update(curr_gen)
    full_gen.columns = full_gen.columns.str.replace('genre_', '')

    test_trans = svd.transform(full_gen)
    test_trans = pd.DataFrame(test_trans)
    test_trans = test_trans.add_prefix('genre_')

    df_track = df_track.loc[:, ~df_track.columns.str.startswith('genre_')]
    df_track = pd.concat([df_track, test_trans], axis=1)

    curr_key = df_track.loc[:, df_track.columns.str.startswith('key_')]
    full_key = pd.DataFrame(np.zeros((len(df_track), len(key_series.tolist()))) , columns=key_series.tolist())
    full_key.update(curr_key)

    df_track = df_track.loc[:, ~df_track.columns.str.startswith('key_')]
    df_track = pd.concat([df_track, full_key], axis=1)

    curr_time = df_track.loc[:, df_track.columns.str.startswith('time_signature_')]
    full_time = pd.DataFrame(np.zeros((len(df_track), len(time_series.tolist()))) , columns=time_series.tolist())
    full_time.update(curr_time)

    df_track = df_track.loc[:, ~df_track.columns.str.startswith('time_signature_')]
    df_track = pd.concat([df_track, full_time], axis=1)
    df_track.to_csv('s3://spotify-net/for_prediction.csv')
    print(df_track.shape)

    print('Uploaded to S3')


# Cell
if __name__ == '__main__':
    s3_objects = load_s3()
    merged_df = merge_frame(s3_objects['spot_tracks'], s3_objects['last_tracks'])
    transformed = dummies_and_scale(merged_df, 0.0000001, s3_objects['scaler'])
    full_frame(transformed, s3_objects['gen_series'], s3_objects['svd'], s3_objects['key_series'], s3_objects['time_series'])