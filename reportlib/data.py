import io
import re
import yaml
import urllib.parse
import pandas as pd
import sqlalchemy as sa


class DbConnection:
    """
    Creates and maintains a connection to the Atom RDS database to run queries

    Args:
        secret_yaml_path (str): Relative path of the secret.yaml file TODO: add template in doc/readme
    """

    def __init__(self, secret_yaml_path):
        with open(secret_yaml_path) as file:
            secrets = yaml.load(file, Loader=yaml.FullLoader)
            dbuser = secrets["rds"]["dbuser"]
            # NB: in secrets.yaml, special characters such as those that may be used in the password need to be URL
            # encoded to be parsed correctly, like @ must become %40
            dbpassword = urllib.parse.quote_plus(secrets["rds"]["dbpassword"])
            dbhost = secrets["rds"]["dbhost"]
            dbport = secrets["rds"]["dbport"]

            url = f"postgresql://{dbuser}:{dbpassword}@{dbhost}:{str(dbport)}/postgres"

            db_engine = sa.create_engine(url)
            self.db_engine = db_engine
            print("Connected to database")

    def query(self, querystring):
        """
        Run query on the Atom RDS

        Args:
            querystring (str): A Postgresql query string

        Returns:
            A pandas DataFrame with the query result
        """
        copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
            query=querystring, head="HEADER"
        )
        cur = self.db_engine.raw_connection().cursor()
        store = io.StringIO()
        cur.copy_expert(copy_sql, store)
        store.seek(0)
        return pd.read_csv(store, low_memory=False)


class Data:
    """
    Loads and hosts common ATOM data like aois, dashboard data (dash), impressions (mop), etc.

    Args:
        secret_yaml_path (str): Relative path of the secret.yaml file
        campaign_id (str): Currently supports NTXX and OTXX schemes

    Returns:
        A pandas DataFrame with the query result
    """

    def __init__(self, secret_yaml_path, campaign_id):
        if "NT" in campaign_id:
            self.project_id = "Nutmeg - PRO-12767"
        elif "OT" in campaign_id:
            self.project_id = "Oak - PRO-12766"
        else:
            raise AssertionError("Unrecognized campaign ID, should be NTXX or OTXX")
        self.campaign_id = campaign_id
        self.aois = pd.DataFrame()
        self.dash = pd.DataFrame()
        self.mop = pd.DataFrame()
        self.lifesight = pd.DataFrame()
        self.survey = pd.DataFrame()

        self.db = DbConnection(secret_yaml_path)

    # Get aoi filter for campaign
    def _get_aois_filter(self):
        data = self.db.query(
            f"""
            select campaign from aois
            where campaign like '%{self.campaign_id}%'
            limit 1
            """
        )
        if data.empty:
            return None
        else:
            return {"campaign": [data["campaign"][0]]}

    # Get survey filter for campaign TODO: make more robust to handle bad messaging format
    def _get_survey_filter(self):
        return {"messaging": [self.campaign_id]}

    # Get dash_table filter for campaign
    def _get_dash_filter(self):
        if "NT" in self.campaign_id:
            project_id = "Nutmeg - PRO-12767"
        elif "OT" in self.campaign_id:
            project_id = "Oak - PRO-12766"
        else:
            raise AssertionError("Unrecognized campaign ID, should be NTXX or OTXX")
        data = self.db.query(
            f"""
            select campaign_name, project from dash_table
            where campaign_name like '%{self.campaign_id}%'
            limit 1
            """
        )
        if data.empty:
            return None
        else:
            return {
                "project": [data["project"][0]],
                "campaign_name": [data["campaign_name"][0]],
            }

    # Get mop_table filter for campaign
    def _get_mop_filter(self):
        data = self.db.query(
            f"""
            select adtype, campaign from mop_table
            where project = '{self.project_id}'
            and (adtype like '%{self.campaign_id}%'
            or campaign like '%{self.campaign_id}%')
            limit 1
            """
        )
        # Select either adtype or campaign column as filter for that campaign
        if self.campaign_id in data["adtype"][0]:
            return {"project": [self.project_id], "adtype": [data["adtype"][0]]}
        elif self.campaign_id in data["campaign"][0]:
            return {"project": [self.project_id], "campaign": [data["campaign"][0]]}
        else:
            return None

    # Extract message in <message>-<geohash> like string
    @staticmethod
    def extract_message(string):
        match = re.match("(.*)-.*", string)
        if match:
            return match[1]
        else:
            return None

    # Extract aoi name in <message>-<geohash> like string
    def extract_aoi(self, string):
        match = re.match(".*-(.*)", string)
        if match:
            return match[1]
        elif string in list(self.aois["geohash"]):
            return self.aois[self.aois["geohash"] == string]["name"].values[0]
        else:
            return None

    # Load Areas of Interest
    def load_aois(self):
        aois_filter = self._get_aois_filter()
        if filter:
            aois = self.db.query(
                f"""
                select * from aois 
                {_where_clause(aois_filter)}
                """
            )
            aois["latitude"] = aois["latitude"].astype(float)
            aois["longitude"] = aois["longitude"].astype(float)

            print(f"- {len(aois)} AOIS found in public.aois")
            self.aois = aois
        else:
            print(f"x no AOI")

    # Load impressions summary table
    def load_dash(self):
        dash_filter = self._get_dash_filter()

        if dash_filter:
            dash = self.db.query(
                f"""
                select project, adtype, impressions, clicks, date_served, message, assetid
                from dash_table
                {_where_clause(dash_filter)} 
                """
            )

            # Format dates
            dash["date_served"] = pd.to_datetime(dash["date_served"])

            if not self.aois.empty:
                dash["geohash"] = dash["message"].apply(lambda m: self.extract_aoi(m))
                dash["aoi"] = dash["geohash"].replace(
                    dict(zip(self.aois["message"].tolist(), self.aois["name"].tolist()))
                )
            else:
                print("! could not enrich dash data with aoi")
            dash["message"] = dash["message"].apply(self.extract_message)

            print(f"- {len(dash)} rows found in public.dash_table")
            self.dash = dash
        else:
            print(f"x no dash data")

    # Load full impressions table
    def load_mop(self):
        mop_filter = self._get_mop_filter()

        if mop_filter:
            mop = self.db.query(
                f"""
                select date_served, impressions, clicks, mobile_id, latitude, longitude, placement, project, assetid, 
                adtype, hourserved, targeting, message, format, message
                from mop_table 
                {_where_clause(mop_filter)}
                """
            )

            if len(mop) == 0:
                raise KeyError(
                    "Filtered MOP table is empty. Please check the filters parameters and/or RDS table"
                )

            # dtype changes (reduces size of the dataset)
            cols_to_category = [
                "placement",
                "project",
                "assetid",
                "adtype",
                "format",
                "message",
            ]
            for c in cols_to_category:
                mop[c] = mop[c].astype("category")

            mop["date_served"] = pd.to_datetime(mop["date_served"])
            mop["latitude"] = pd.to_numeric(mop["latitude"])
            mop["longitude"] = pd.to_numeric(mop["longitude"])

            if not self.aois.empty:
                mop["geohash"] = mop["message"].apply(lambda m: self.extract_aoi(m))
                mop["aoi"] = mop["geohash"].replace(
                    dict(zip(self.aois["message"].tolist(), self.aois["name"].tolist()))
                )
            mop["message"] = mop["message"].apply(self.extract_message)

            print(f"- {len(mop)} impressions found in public.mop_table")
            self.mop = mop.drop(columns=["message.1"])

        else:
            print(f"x no dash data")

    # Load Patterns of Life data from lifesight
    def load_lifesight(
        self,
    ):
        # TODO: manual_maids=None (add option to provide MAIDs manually)
        mop_filter = self._get_mop_filter()

        if mop_filter:
            # NB: we use lifesight_raw_2 as main lifesight table
            lifesight = self.db.query(
                f"""
                select *
                from lifesight_raw_2 lr
                inner join (select mobile_id from mop_table mt {_where_clause(mop_filter)}) as m 
                on lr.mobile_id = m.mobile_id
                """
            )

            # Eliminate duplicates
            lifesight = lifesight.drop_duplicates(subset=["mobile_id"])

            if not lifesight.empty:
                print(f"- {len(lifesight)} POL rows found in public.lifesight_raw_2")
                self.lifesight = lifesight
        else:
            print("x need maids from mop to load lifesight data")

    # Load survey results from new_survey_data
    def load_survey(self):
        survey_filter = self._get_survey_filter()

        survey = self.db.query(
            f"""
            select *
            from new_survey_data
            {_where_clause(survey_filter)} 
            """
        )
        if not survey.empty:
            print(f"- {len(survey)} survey answers found in public.new_survey_data")
            self.survey = survey
        else:
            print(f"x no survey data")

    def load_all(self):
        print("Loading " + self.campaign_id + " data from AWS...")

        self.load_aois()
        self.load_dash()
        self.load_mop()
        self.load_lifesight()
        self.load_survey()

        print("Done!")


# Return a where clause as a string from a dictionary of lists
# The clause applies a strict AND to all parameters
def _where_clause(dict_filters):
    first = True
    sub_sql_where = "where "
    for var, val in dict_filters.items():
        if first:
            first = False
        else:
            sub_sql_where = sub_sql_where + "and "
        if type(val) == str:
            val = list(val)
        sub_sql_where = (
            sub_sql_where + f"""{var} in ({','.join([f"'{v}'" for v in val])}) """
        )
    return sub_sql_where
