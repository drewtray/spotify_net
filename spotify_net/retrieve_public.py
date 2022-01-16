# AUTOGENERATED! DO NOT EDIT! File to edit: retrieve_public.ipynb (unless otherwise specified).

__all__ = ['cred']

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