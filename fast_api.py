import boto3
import joblib
from io import BytesIO
import pickle
import _pickle as cPickle
from fastapi import FastAPI
import tempfile


s3_resource = boto3.resource('s3')

# scaler = s3_resource.Object('spotify-net', 'lgbm').get()

# s3 = boto3.client('s3')
scaler = s3_resource.Object('spotify-net', 'lgbm.pkl').get()
scaler = cPickle.loads(scaler['Body'].read())
# pickle.loads(body._raw_stream())

# scaler = pickle.loads(scaler['Body'])
 

# print(scaler)

# app = FastAPI()


# @app.get('/model/{track_features}')
# async def root(track_features):
#     return {track_features}

# @app.get('/model')
# async def root():
#     return {'message': 'sup world'}
