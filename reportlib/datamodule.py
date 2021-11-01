"""Module for downloading Atom data"""
import io
import os
import re
from pathlib import Path

import yaml
import urllib.parse
import pandas as pd
import sqlalchemy as sa


class DbConnection:
    """
    Creates and maintains a connection to the Atom RDS database to run PostgreSQL queries
    """

    def __init__(self, secret_yaml_path: str):
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

    def query(self, querystring: str) -> pd.DataFrame:
        """
        Run query on the Atom RDS

        Example:
        ``
        query(\"\"\"select * from dash_table limit 1\"\"\")
        ``

        Args:
            querystring (str): A Postgresql query string

        Returns:
            A pandas DataFrame with the query result
        """
        copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
            query=querystring, head="HEADER"
        )
        conn = self.db_engine.raw_connection()
        cur = conn.cursor()
        store = io.StringIO()
        cur.copy_expert(copy_sql, store)
        store.seek(0)
        data = pd.read_csv(store, low_memory=False)
        cur.close()
        conn.commit()
        conn.close()
        return data


class Data:
    """
    Loads and hosts common ATOM data like aois, dashboard data (dash), impressions (mop), etc.

    Attributes:
        aois (DataFrame): Campaign aois
        dash (DataFrame): Enriched dash table data (impressions by day and asset)
        cm360 (DataFrame): Enriched CM360 offline report data (impressions by day)
        mop (DataFrame): Enriched mop table data (individual impressions)
        lifesight (DataFrame): Lifesight data for MAIDs listed in mop
        survey (DataFrame): Question answers if campaign is a survey
    """

    def __init__(self, secret_yaml_path: str, campaign_id: str):
        if "NT" in campaign_id:
            self.project_id = "Nutmeg - PRO-12767"
        elif "OT" in campaign_id:
            self.project_id = "Oak - PRO-12766"
        else:
            raise AssertionError("Unrecognized campaign ID, should be NTXX or OTXX")
        self.campaign_id = campaign_id
        self.aois = pd.DataFrame()
        self.dash = pd.DataFrame()
        self.cm360 = pd.DataFrame()
        self.mop = pd.DataFrame()
        self.lifesight = pd.DataFrame()
        self.survey = pd.DataFrame()

        self.reach_ratio = None  # mop reach / mop impressions

        self.db = DbConnection(secret_yaml_path)

    def _get_aois_filter(self) -> dict:
        """
        Get aoi filter for campaign
        """
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

    def _get_survey_filter(self) -> dict:
        """
        Get survey filter for campaign
        TODO: make more robust to handle bad messaging format
        """
        return {"messaging": [self.campaign_id]}

    def _get_dash_mop_adtypes(self) -> dict:
        """
        Get adtypes for given campaign
        """
        adtypes = self.db.query(
            f"""
            select distinct adtype from dash_table
            where adtype like '%{self.campaign_id}%'
            """
        )
        return "('" + "', '".join(adtypes["adtype"].to_list()) + "')"

    @staticmethod
    def _extract_message(string: str) -> str:
        """
        Extract message in <message>-<geohash> like string
        """
        match = re.match("(.*)-.*", string)
        if match:
            return match[1]
        else:
            return None

    def _extract_aoi(self, string: str) -> str:
        """
        Extract aoi name in <message>-<geohash> like string
        """
        match = re.match(".*-(.*)", string)
        if match:
            return match[1]
        elif string in list(self.aois["geohash"]):
            return self.aois[self.aois["geohash"] == string]["name"].values[0]
        else:
            return None

    def load_aois(self) -> None:
        """
        Load Areas of Interest
        """
        aois = self.db.query(
            f"""
                        select * from aois 
                        where campaign like '%{self.campaign_id}%'
                        """
        )
        if aois.empty:
            print(f"x NO AOI")
            return None

        aois["latitude"] = aois["latitude"].astype(float)
        aois["longitude"] = aois["longitude"].astype(float)

        print(f"- {len(aois)} AOIS found in public.aois")
        self.aois = aois

    def load_dash(self) -> None:
        """
        Load impressions summary table
        """
        adtypes = self._get_dash_mop_adtypes()

        if adtypes:
            print(adtypes)
            dash = self.db.query(
                f"""
                select project, adtype, impressions, clicks, date_served, message, assetid, ad_language,\
                country_code, format
                from dash_table
                where adtype in {adtypes} 
                """
            )

            # Format dates
            dash["date_served"] = pd.to_datetime(dash["date_served"])

            if not self.aois.empty:
                dash["geohash"] = dash["message"].apply(lambda m: self._extract_aoi(m))
                print(
                    dict(zip(self.aois["geohash"].tolist(), self.aois["name"].tolist()))
                )
                dash["aoi"] = dash["geohash"].replace(
                    dict(zip(self.aois["geohash"].tolist(), self.aois["name"].tolist()))
                )
            else:
                print("! could not enrich dash data with aoi")
            dash["message"] = dash["message"].apply(self._extract_message)

            print(f"- {len(dash)} rows found in public.dash_table")

            if not dash.empty:
                print(
                    "POP:",
                    dash["date_served"].min().strftime("%Y-%m-%d"),
                    "-",
                    dash["date_served"].max().strftime("%Y-%m-%d"),
                )
            self.dash = dash
        else:
            print(f"x no dash data")

    def load_cm360(self, path: str) -> pd.DataFrame:
        """
        Load impressions by date from CM360 report file

        Report must have at least

        - dimensions: Date, Placement

        - metrics: Impressions, Clicks
        """
        dcm = pd.read_csv(path, skiprows=11)[:-1][
            ["Placement", "Date", "Impressions", "Clicks"]
        ]
        dcm.columns = ["placement", "date_served", "impressions", "clicks"]

        dcm["date_served"] = pd.to_datetime(dcm["date_served"])

        expanded = dcm["placement"].str.split("|", expand=True)
        expanded.columns = [
            "project",
            "assetid",
            "adtype",
            "message",
            "country_code",
            "ad_language",
            "format",
        ]

        msg = expanded["message"].str.split("-", expand=True)
        msg.columns = ["message", "geohash"]

        if not self.aois.empty:
            msg["aoi"] = msg["geohash"].replace(
                dict(zip(self.aois["message"].tolist(), self.aois["name"].tolist()))
            )

        self.cm360 = pd.concat(
            [dcm.drop(columns=["placement"]), expanded.drop(columns=["message"]), msg],
            axis=1,
        )

    def load_blis_raw(self, path: str, verbose=True):
        """
        Load impressions from downloaded S3 blis-raw folder

        Pass the path as parameter
        """
        dataframes = []
        for f in os.scandir(path.rstrip("/")):
            if f.is_dir():
                csvpath = f.path + "/data_file_1.csv"

                try:  # Read file and append campaign data
                    df = pd.read_csv(csvpath)
                    campaign_df = df[df["Campaign"].str.contains(self.campaign_id)]
                    dataframes.append(campaign_df)
                    if campaign_df.empty and verbose:
                        print("no data for", f.name)
                    elif verbose:
                        print(f.name, "loaded!")
                except:
                    if verbose:
                        print("no file for", f.name)

        mop = pd.concat(dataframes, axis=0)
        print(mop.shape)
        mop.columns = mop.columns.str.lower()
        mop = mop.rename(
            columns={
                "device id": "mobile_id",
                "date": "date_served",
                "hour": "hourserved",
                "loc": "aoi"
            }
        )

        mop["date_served"] = pd.to_datetime(mop["date_served"])

        aoi_exploded = (
            mop["placement"]
            .str.split(" - ", expand=True)
            .rename(columns={0: "loc", 1: "aoi"})
        )

        mop["mobile_id"] = mop["mobile_id"].str.lower()

        mop = pd.concat([mop, aoi_exploded], axis=1)

        self.mop = mop

        self.reach_ratio = mop['mobile_id'].nunique() / mop['impressions'].sum()

        print(f"- {mop['impressions'].sum()} impressions found in blis_raw folder")
        print("- reach ratio: {:.5f}".format(self.reach_ratio))

    def load_mop(self) -> None:
        """
        Load full impressions table
        """
        # TODO (important): fetch from all adtypes as follows:
        """
        select distinct adtype from dash_table
        
        -->
        select sum(impressions) from mop_table
        where project = 'Nutmeg - PRO-12767' -- Oak - PRO-12766
        and adtype in (<results from prev step>)
        """

        adtypes = self._get_dash_mop_adtypes()

        if adtypes:
            mop = self.db.query(
                f"""
                select date_served, impressions, clicks, mobile_id, latitude, longitude, placement, project, assetid, 
                adtype, hourserved, targeting, message, format, message
                from mop_table
                where project = '{self.project_id}'
                and adtype in {adtypes}
                """
            )

            if len(mop) == 0:
                print("x no mop data")
                return None

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
                mop["geohash"] = mop["message"].apply(lambda m: self._extract_aoi(m))
                mop["aoi"] = mop["geohash"].replace(
                    dict(zip(self.aois["message"].tolist(), self.aois["name"].tolist()))
                )
            mop["message"] = mop["message"].apply(self._extract_message)

            print(f"- {mop['impressions'].sum()} impressions found in public.mop_table")
            self.mop = mop.drop(columns=["message.1"])

            self.reach_ratio = mop['mobile_id'].nunique() / mop['impressions'].sum()

        else:
            print(f"x no dash data")

    def load_lifesight(self, from_manual_maid_table=False) -> None:
        """
        Load Patterns of Life data from lifesight

        Args:
            from_manual_maid_table (bool): wether to load using mop data or to look for MAIDs list in maids_manual table
        """
        if from_manual_maid_table:
            lifesight = self.db.query(
                f"""
                select *
                from lifesight_raw_2 lr
                inner join (select mobile_id from maids_manual) as m 
                on lr.mobile_id = m.mobile_id
                """
            ).drop_duplicates(subset=["mobile_id"])

            if not lifesight.empty:
                print(f"- {len(lifesight)} POL rows found in public.lifesight_raw_2")
                self.lifesight = lifesight
            else:
                print("x no maids found in maids_manual from that campaign")
        else:
            adtypes = self._get_dash_mop_adtypes()

            if adtypes:
                # NB: we use lifesight_raw_2 as main lifesight table
                lifesight = self.db.query(
                    f"""
                    select *
                    from lifesight_raw_2 lr
                    inner join (
                        select mobile_id from mop_table 
                        where project = '{self.project_id}' 
                        and adtype in {adtypes}
                    ) as m 
                    on lr.mobile_id = m.mobile_id
                    """
                ).drop_duplicates(subset=["mobile_id"])

                if not lifesight.empty:
                    print(
                        f"- {len(lifesight)} POL rows found in public.lifesight_raw_2"
                    )
                    self.lifesight = lifesight
            else:
                print("x need maids from mop to load lifesight data")

    def load_survey(self) -> None:
        """
        Load survey results from new_survey_data
        """
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

    def load_all(self) -> None:
        """
        Try to load aois, dash, mop, lifesight and surve data
        ! Warning ! If the campaign has no data in mop table query may take hours to find out
        """
        print("Loading " + self.campaign_id + " data from AWS...")

        self.load_aois()
        self.load_dash()
        self.load_mop()
        self.load_lifesight()
        self.load_survey()

        print("Done!")

    Path("raw").mkdir(parents=True, exist_ok=True)

    def export_raw(
        self, external_mop=pd.DataFrame(), external_lifesight=pd.DataFrame()
    ):
        """
        Export both mop and maids raw data for client delivery. Uses internal mop and lifesight attributes by default.

        Args:
            external_mop (DataFrame): *optional*, override mop dataframe
            external_lifesight (DataFrame): *optional*, override lifesight dataframe
        """
        # export impressions table
        cols = [
            "date_served",
            "impressions",
            "clicks",
            "mobile_id",
            "longitude",
            "latitude",
            "format",
            "message",
            "hourserved",
            'keyword',
            'ad_language',
            'adtype',
            'message',
            'video_first_quartile',
            'video_midpoint',
            'video_third_quartile',
            'video_completions'
        ]
        filename = f"Export_MOP_{self.project_id}_{self.campaign_id}"
        mop_data = external_mop if not external_mop.empty else self.mop
        assert not mop_data.empty, "no mop data provided!"

        # TODO: revert
        mop_data['keyword'] = None
        mop_data['ad_language'] = None
        mop_data['adtype'] = None
        mop_data['message'] = None
        mop_data['video_first_quartile'] = None
        mop_data['video_midpoint'] = None
        mop_data['video_third_quartile'] = None
        mop_data['video_completions'] = None

        mop_data[cols].to_csv(
            f"raw/{filename}.zip",
            compression=dict(method="zip", archive_name=f"{filename}.csv"),
            index=False,
        )

        # export maids table
        cols = [
            "mobile_id",
            "devicetype",
            "idtype",
            "make",
            "model",
            "os",
            "osver",
            "devicecost",
            "homecountry",
            "workgeohash",
            "worklat",
            "worklong",
            "carriers",
            "homegeohash",
            "homelat",
            "homelong",
            "travelcountries",
            "gender",
            "deviceage",
            "yob",
            "age",
        ]
        filename = f"Export_MAIDS_{self.project_id}_{self.campaign_id}"
        life_data = (
            external_lifesight if not external_lifesight.empty else self.lifesight
        )
        assert not life_data.empty, "no lifesight data provided!"
        life_data[cols].drop_duplicates(subset=["mobile_id"]).to_csv(
            f"raw/{filename}.zip",
            compression=dict(method="zip", archive_name=f"{filename}.csv"),
            index=False,
        )


def get_maids_data(df: pd.DataFrame) -> tuple:
    """
    Load both past impressions and lifesight for given maids

    Args:
        df (DataFrame): dataframe with mobile_id column

    Returns:
        past_impressions(DataFrame): all geolocated past impressions for those maids (from public.geoloc_impr table)
        lifesight(DataFrame): all lifesight data for those maids (from public.lifesight_raw_2)
    """
    assert "mobile_id" in df, "'mobile_id' column not found if DataFrame"

    db = DbConnection("../secrets.yaml")

    maids = df[["mobile_id"]].dropna().drop_duplicates()
    maids["mobile_id"] = maids["mobile_id"].str.lower()

    print("uploading", len(maids), "maids")
    maids.to_sql(
        "maids_manual", db.db_engine, schema="public", if_exists="replace", index=False
    )

    print("\ndownloading past impressions")
    past_impressions = db.query(
        """
    select *
    from geoloc_impr gi
    inner join (select mobile_id from maids_manual) as m 
    on gi.mobile_id = m.mobile_id
    """
    )
    print("found", len(past_impressions), "past impressions")

    print("\ndownloading lifesight data")
    lifesight = db.query(
        """
    select *
    from lifesight_raw_2 lr
    inner join (select mobile_id from maids_manual) as m 
    on lr.mobile_id = m.mobile_id
    """
    )
    print("found", len(lifesight), "entries")

    return past_impressions, lifesight


def _where_clause(dict_filters):
    """
    Return a where clause as a string from a dictionary of lists
    The clause applies a strict AND to all parameters
    """
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
