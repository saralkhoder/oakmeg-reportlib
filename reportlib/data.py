import io
import yaml
import urllib.parse
import pandas as pd
import sqlalchemy as sa


class DbConnection:
    """
    Creates and maintains a connection to the Atom RDS database to run queries

    Args:
        secret_yaml_path: This is the first param.

    Returns:
        A pandas DataFrame with the query result
    """
    def __init__(self, secret_yaml_path):
        print('Connecting...')
        with open(secret_yaml_path) as file:
            secrets = yaml.load(file, Loader=yaml.FullLoader)
            dbuser = secrets['rds']['dbuser']
            # NB: in secrets.yaml, special characters such as those that may be used in the password need to be URL
            # encoded to be parsed correctly, like @ must become %40
            dbpassword = urllib.parse.quote_plus(secrets['rds']['dbpassword'])
            dbhost = secrets['rds']['dbhost']
            dbport = secrets['rds']['dbport']

            url = f"postgresql://{dbuser}:{dbpassword}@{dbhost}:{str(dbport)}/postgres"

            db_engine = sa.create_engine(url)
            self.db_engine = db_engine
            print('Connected to database')

    def query(self, query):
        copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
            query=query, head="HEADER"
        )
        cur = self.db_engine.raw_connection().cursor()
        store = io.StringIO()
        cur.copy_expert(copy_sql, store)
        store.seek(0)
        return pd.read_csv(store, low_memory=False)