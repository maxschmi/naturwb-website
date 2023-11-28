#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Class definitions to request a NatUrWB reference from the database."""

##############################################################################
#                              based on:                                     #
#               Masterarbeit Uni Freiburg Hydrologie                         #
#  Ermittlung einer naturnahen urbanen Wasserbilanz (NatUrWB)                #
#               als Zielvorgabe für deutsche Städte                          #
#                               -                                            #
#              Erstellung eines interaktiven Webtools                        #
#                                                                            #
#                           published on:                                    #
# Schmit, Max; Leistert, Hannes; Steinbrich, Andreas; Weiler, Markus (2022)  #
#    Webtool zur Ermittlung der naturnahen urbanen Wasserbilanz (NatUrWB)    #
#                  Korrespondenz Wasserwirtschaft, DWA                       #
#                      DOI: 10.3243/kwe2022.09.002                           #
#     Online verfügbar unter https://freidok.uni-freiburg.de/data/229574     #
##############################################################################

# libraries
import geopandas as gpd
import pandas as pd
from getpass import getpass
from shapely.geometry import Polygon, MultiPolygon
try:
    from shapely.geometry.polygon import PolygonAdapter
except:
    from shapely.geometry import Polygon as PolygonAdapter
try:
    from shapely.geometry.polygon import MultiPolygonAdapter
except:
    from shapely.geometry import Polygon as MultiPolygonAdapter
import numpy as np
import sqlalchemy
import json
from textwrap import wrap
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources
try:
    from . import data
except ImportError:
    try:
        from .. import data
    except ImportError:
        import data
from io import BytesIO
import base64

# plotly
import plotly as ply
import plotly.graph_objs as go
from plotly.offline import plot as ply_plot

# matplotlib
from matplotlib import pyplot as plt
import matplotlib as mpl
from matplotlib.sankey import Sankey
from matplotlib.path import Path as mplPath
from matplotlib.patches import PathPatch
from matplotlib import cm
import contextily as cx

# load messages file
with pkg_resources.open_text(
    data, "naturwb_messages.json", encoding="utf8") as f:
    MSGS_RAW = json.load(f)
mpl.rcParams['hatch.linewidth'] = 2

# changed Sankey class
class _SankeyNWB(Sankey):
    def finish(self):
        return self.diagrams

# plot transfer functions
def _mpl_fig_to_graphic(fig, dpi=75):
    fig.set_dpi(dpi)
    with BytesIO() as buffer:
        fig.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        image_png = buffer.getvalue()
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')

    return graphic


# own classes
# -----------
class Pool(object):
    """A class to make and save several NatUrWB-queries together.

    Parameters
    ----------
    max_queries : int, optional
        The maximum amount of queries that should get saved.
        The default is 20.
    """
    def __init__(self, max_queries=20,
                 db_pwd=None, db_user=None, db_host=None,
                 db_port=5432, db_schema=None):
        """Initiate the naturwb Pool.

        Parameters
        ----------
        max_queries : int, optional
            The maximum amount of queries that should get saved.
            The default is 20.
        db_pwd : str or None, optional
            The password for the Database.
            If None is entered, the user will be prompted to give the password.
            The default is None.
        db_user : str or None, optional
            The user for the Database.
            If None is entered, the user will be prompted to give the User.
            The default is None.
        db_host : str or None, optional
            The Host for the Database.
            If None is entered, the user will be prompted to give the Host.
            The default is None.
        db_port : str or None, optional
            The port for the Database.
            If None is entered, the user will be prompted to give the port.
            The default is None.
        db_schema : str or None, optional
            The schema for the Database.
            If None is entered, the user will be prompted to give the schema.
            The default is None.
        """
        self.queries = []
        self.max_queries = max_queries

        # create db engine
        engine_ok = False
        engine_attempts = 3
        while (not engine_ok) and (engine_attempts > 0):
            # get the DB settings
            if db_user == None:
                db_user = input("Give the User for the DB: ")
            if db_host == None:
                db_host = input("Give the Host for the DB:")
            if db_port == None:
                db_port = input("Give the port for the DB:")
            if db_schema == None:
                db_schema = input("Give the Schema for the DB:")
            # for para, label in zip(
            #     ["db_user", "db_host", "db_port", "db_schema"],
            #     ["User", "Host", "Port", "Schema"]):
            #     if (locals()[para] == None):
            #         locals()[para] = input("Give the {0} for the DB: ".format(label))

            # get DB Password
            if (db_pwd == None):
                db_pwd = getpass("Give the Password for the DB: ")

            # create engine
            self.engine = sqlalchemy.create_engine(
                'postgresql://' + db_user + ':' +
                db_pwd + "@" +
                db_host + ':' + str(db_port) + "/" + db_schema)

            # check engine
            try:
                with self.engine.connect() as con:
                    pass
                engine_ok = True
            except sqlalchemy.exc.OperationalError:
                engine_attempts -= 1
                if engine_attempts > 0:
                    print("The entered Password was not correct. Please try again." +
                          "\nYou have {} attempts left.".format(str(engine_attempts)))
                else:
                    print("The entered Password was not correct." +
                          "!!!You entered 3 times the wrong Password for the database!!!")
                db_pwd = None

        super().__init__()

    def make_query(self, **kwargs):
        """Make a NatUrWB query to the database.

        Returns
        -------
        naturwb.Query object
            The Query object, that is also saved to the pool.
        """
        query = Query(db_engine=self.engine, **kwargs)
        self.queries.append(query)
        self._clean_queries()
        return query

    def get_comparing_df(self):
        """
        Get a GeoDataFrame with all the main values of the queries to compare them.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame with all the main values of the queries,
            the input polygon and the landuse distribution. (EPSG=25832)

        """
        df = pd.DataFrame(index=range(0,len(self.queries)))
        for i, q in enumerate(self.queries):
            # add the main results
            for para in q.naturwb_ref.index:
                df.loc[i, para] = q.naturwb_ref[para]

            # add the shape
            df.loc[i, "geometry"] = q.urban_shp

            # add the landuse distributions
            lanus = q.coef_all.prod(axis=1
                ).groupby("lanu_id").sum(
                ).reindex(range(0, 14)).drop(1
                ).fillna(0)
            lanu_cols = lanus.index.map(
                lambda x: "lanu_" + str(x)).to_list()
            df.loc[i, lanu_cols] = lanus.to_list()

        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=25832)

        return gdf

    def _clean_queries(self):
        """Clean the Query-Pool if there are more saved queries than the max_queries states.

        Normaly it is not necessary to use this method manualy.
        """
        if len(self.queries) > self.max_queries:
            self.queries = self.queries[
                (len(self.queries) - self.max_queries):]


class Query(object):
    """A query to the NatUrWB-Database.

    Implements all the aggregations and standard plots for a NatUrWB reference.

    Parameters
    ----------
    urban_shp : shapely.Polygon
        The urban Polygon for which to make the query in UTM (EPSG=25832).
        This is used to query the database.
    urban_shp_wgs : geopandas.GeoSeries
        The urban Polygon for which to make the query in WGS (EPSG=4326).
    urban_shp_utm : geopandas.GeoSeries
        The urban Polygon for which to make the query in UTM (EPSG=25832).
        This is used to calculate distances.
    db_engine : sqlalchemy.engine
        The database engine to the NatUrWB database.
    sim_shps_clip : geopandas.GeoSeries
        The clip of the lookup tabel with the urban_shp Polygon
        in UTM (EPSG=25832).
    ref_lanus : pandas.DataFrame
        The DataFrame with all the landuse reference fields and their area.
    results : pandas.DataFrame
        The DataFrame with all the single simulation results from the database.
        These are the results without the aggregation.
    sim_infos : pandas.DataFrame
        The DataFrame with all the flags and special informations
        per simulation Polygon in the urban area.

        Has the following rows:

        - stat_id: The Station ID of the DWD Station.
        - buek_flag: The flag marking the step of changing the soil groups defined in the BUEK,
          because there was no main soil defined for this group.

          The buek_flag can have the following values:

            0. The GEN_ID is the original and there was no change made
            1. one or more neighbor cells have the same geology code.
               Then of those cells the cell's GEN_ID with the longest touching border is taken.
            2. no neighboor cell has the same geology information.
               Then the cell's GEN_ID with the longest touching border is taken.
            3. there was no direct neighbor therefor the nearest neighbor
               with the same geology got choosen. (<1km)
            4. the GEN_ID couldn't get a neighbor soil parameter set.
               Therefor this simulation Polygon did not get simulated.

        - bfid_undef: The percentage of soils in the soil group
          that are not defined and therefor not siulated.
        - lanu_flag: The flag marking how the landuse distribution was defined for the simulation.

          The lanu_flag can have the following values:

            0. All the soils got shuffled with the landuses found
               on the same soil in the same NRE
            1. There was no not urbanised landuse found
               on the same soil in the same NRE.
               Therefor all the possible landuses got simulated.
            2. One soil (BF_ID) defined for this polygon was a rock
               and can therefor only have lhe landuse 0.
               The other soil types of this polygon can have other landuses.
               Therefor there are different landuses that got simulated for every soil type.
               This results in a different aggregation process with the results.

        - wea_flag: The flag of the weather coefficients.
          Flags how the multi-annual value for the simulatrion-polygon
          got defined from the DWD grid.

          The wea_flag can have the following values:

            0. if the weather data got interpolated only with inlying raster cells.
            1. if the weather data got filled with data from touching raster cells.
            2. if the weather data got filled with data from nearby raster cells. (<4km away)

        - wea_dist: Only if the wea_flag is 2!
          This field gives the distance to the DWD raster cell(s)
          from which the multi-annual weather values came from in m.
        - wea_flag_n: Similar than wea_flag but only for the precipitation,
          which is regionalised with the REGNIE raster.
        - wea_dist_n: Similar than wea_dist but only for the precipitation,
          which is regionalised with the REGNIE raster.
        - sl_flag: The flag marking the quality of the mean slope
          that was calculated by an underlying DEM20 raster.

          The sl_flag can have the following values:

            0. The polygon was filled with data from an inlying cell.
            1. The polygon was filled with data from a touching cell.
            2. The polygon was filled with data from a nearby cell.
               (<2km, only later for some manually selected polygons)

        - sl_dist: Only if the sl_flag is 2!
          This field gives the distance to the raster cell(s)
          from which the slope values came from in m.
        - sl_std: The standard deviation of the mean slope in %-points.
        - sun_flag: The flag marking the quality of the sunshine values (incoming solar radiation)
          that was calculated by an underlying DEM20 raster.

          The sun_flag can have the following values:

            0. The polygon was filled with data from an inlying cell.
            1. The polygon was filled with data from a touching cell.
            2. The polygon was filled with data from a nearby cell.
               But only the "Sonnenstundenfaktor" was taken from nearby cells.
               The diffuse and direct radiation was calculated for the real location.
               (<12km, only later for some manually selected polygons)

        - sun_dist: Only if the sun_flag is 2!
          This field gives the distance to the raster cell(s)
          from which the "Sonnenstundenfaktor" values came from in m.
        - wea_t_std: The standard deviation of the multi-annual,
          yearly mean of the temperature in °C.
        - wea_et_std: The standard deviation of the multi-annual,
          yearly sum of the evapotranspiration in mm/a.
        - wea_n_wihj_std: The standard deviation of the multi-annual,
           winter half-year sum of the precipitation in mm/6 months.
        - wea_n_sohj_std: The standard deviation of the multi-annual,
          summer half-year sum of the precipitation in mm/6 months.
        - anteil: The share of the area of the simulation polygon
          in the urban area in %.
        - area: The area of the simulation polygon in the urban area in m².

    missing_lanus : pandas.DataFrame
        A DataFrame giving saying for which lookup-polygon in the urban_shp it
        was not possible to find a landuse distribution in the same NRE on the same soil.
        For those polygons a sourounding search was done to find a landuse distribution.
        Also gives an information if those polygons could get resolved with a sourounding search.
        Furthermore hands the area and the area percentage ("anteil") of those polygons.
    coef_lanu : pandas.DataFrame
        The coefficients to aggregate over the landuse.
        This is used for the second aggregation step.
    coef_nat : pandas.DataFrame
        The coefficients to aggregate over the Naturraumeinheit(NRE).
        This is used for the third aggregation step.
    coef_sim : pandas.DataFrame
        The coefficients to aggregate over the simulation polygons.
        This is used for the fourth aggregation step.
    coef_gen : pandas.DataFrame
        The coefficients to aggregate over the soil groups.
        This is used for the fifth aggregation step.
    coef_all : pandas.DataFrame
        All the coefficients to aggregate over the landuse, the soil-group,
        the simulation polygons, the NRE and the urban_shp.
    res_gat_1 : pandas.DataFrame
        The results after the first aggregation step (BF_ID).
    res_gat_2 : pandas.DataFrame
        The results after the second aggregation step (landuse).
    res_gat_sim : pandas.DataFrame
        The results after the third aggregation step.
        Has one set of values for every simulation polygon.
    res_gat_gen : pandas.DataFrame
        The results after the fifth aggregation step.
        Has one set of values for every soil group.
    naturwb_ref : pandas.Series
        The completely aggregate NatUrWB result for this query.

        Has several rows:

        - n: precipitation in mm/a
        - kap.A: the capillary rise in mm/a
        - et: the actual evapotranspiration in mm/a
        - runoff: the surface run-off together with
          the part from the interflow in mm/a
        - oa: the direct surface runoff in mm/a
        - za: the interflow in mm/a
        - tp: the deep percolation (also known as groundwater recharge) in mm/a
        - runoff_rel: the surface run-off together with the part from
          the interflow in % of the waterbalance
        - tp_rel: the groundwater recharge in % of the waterbalance
        - et_rel: the actual evapotranspiration in % of the waterbalance

    msgs : list of str
        A list of all the messages that should be added to the NatUrWB result.
    """

    def __init__(self, urban_shp, db_engine=None,
                 urban_shp_crs="EPSG:4326", do_plots=False):
        """
        Initiate the query. This is the only function needed to make the query.



        Parameters
        ----------
        urban_shp : shapely.Polygon or geopandas.GeoSeries
            The urban Polygon for which to make the query in WGS (EPSG=4326) or
            in a GeoSeries with the corresponding crs informations.
        db_engine : sqlalchemy.engine, optional.
            The database engine to the NatUrWB database.
            If None the default Database is created from the Pool class.
            Then you need to input the password for the database.
            It is recommended to first create a Pool object and then make a queries with pool.make_query().
            This prevents you from entering the database password every time.
            The default is None, so the engine from a new Pool object.
        urban_shp_crs : str of crs type, optional
            The coordinate reference system of the input urban_shp.
            The string is needed if the entry is a shapely Polygon.
            The default is "EPSG:4326"
        do_plots : bool, optional
            should the basic plots get created while initiating the object?
            The default is False.

        Returns
        -------
        None.

        """
        # check if GeoSeries
        if type(urban_shp) in [Polygon, MultiPolygon, PolygonAdapter, MultiPolygonAdapter]:
            urban_shp_gs = gpd.GeoSeries(urban_shp, crs=urban_shp_crs)
        elif type(urban_shp) == gpd.GeoSeries:
            urban_shp_gs = urban_shp
        else:
            raise ValueError("The file format for the given urban_shape is not valid.")

        # convert to UTM or WGS84 and export shapely Polygon
        self.urban_shp_wgs = urban_shp_gs.to_crs(4326)
        self.urban_shp_utm = urban_shp_gs.to_crs(25832)
        self.urban_shp = self.urban_shp_utm.iloc[0]

        # save database engine to the naturwb database
        if db_engine is None:
            self.db_engine = Pool(max_queries=1).engine
        else:
            self.db_engine = db_engine

        # do the sql queries
        self._sql_query_basics()

        # aggregate the results
        self._aggregate_results()

        # make the basic plots
        if do_plots:
            self._make_plot_sim_shps_clip()
            self._make_plot_pie()
            self._make_plot_ternary()
            self._make_plot_sankey()

        # create the messages
        self._make_msgs()

    def plot(self, kind="pie", renew=True, **kwargs):
        """
        Plot the results.

        Parameters
        ----------
        kind : str, optional
            Decide for the kind of plot that should get created.
            One of  "pie", "bar", "ternary", "sankey", "pie_plotly",
            "pie_landuse", "sim_shps_clip", "sim_shps_clip_plotly",
            "reference_polys",
            for backwards compatibility, also "lookup_clip", "lookup_clip_plotly" are accepted
            The default is "pie".
        renew : bool, optional
            Whether to redo the figure even if it got already created.
            If False only create the figur if it was not already created.
            The default is True.
        **kwargs : dict, optional
            The Keyword arguments to be handed to the _make_plot_* function.

        Returns
        -------
        fig : plotly.figure.Figure or matplotlib.figure.Figure.
            The figure object of the plot.

        """
        kind = kind.lower()

        # change lookup_clip to sim_shps__clip for backwords compatibility
        for test, repl in zip(["lookup_clip", "lookup_clip_plotly"],
                            ["sim_shps_clip", "sim_shps_clip_plotly"]):
            if kind==test:
                kind = repl
                FutureWarning("The lookup_clip is not called anymore lookup_clip but sim_shps_clip. Please consider this, as in future, the lookup_clip will get removed completely")

        # check if kind is valid
        valid_kinds = [
            "pie", "bar", "ternary", "sankey", "pie_plotly", "pie_landuse",
            "sim_shps_clip", "sim_shps_clip_plotly", "reference_polys", "pie_landuse_mpl"]
        if kind not in valid_kinds:
            raise ValueError((
                "The parameter {kind} is not a valid parameter of kind!\n" +
                'Choose one of the following ("{valid_kinds}")'
                ).format(kind=kind,
                            valid_kinds='", "'.join(valid_kinds)))

        # if the figure got not already created, create it now
        if not hasattr(self, "fig_" + kind) or renew:
            getattr(self, "_make_plot_" + kind)(**kwargs)

        return getattr(self, "fig_" + kind)

    def plot_web(self, kind, dpi=75, **kwargs):
        """Generate a plot to use in a website.

        Uses the Query.plot method to produce the plot.

        Parameters
        ----------
        dpi : int, optional
            The dpi value for a matplotlib plot to use
            The default is 75.
        **kwargs : dict
            The keyword arguments to be handed to the Query.plot method.

        Returns
        -------
        string of img64 or plotly.offline.plot
            Depending on the kind of plot produced
            a 64 bytes string image is returned(matplotlib)
            or a html string for plotly plots is returned.
        """
        fig = self.plot(kind=kind, **kwargs)
        if type(fig) == mpl.figure.Figure:
            return _mpl_fig_to_graphic(fig, dpi=dpi)
        elif type(fig) == go.Figure:
            return ply_plot(fig, output_type='div', include_plotlyjs=False)
        else:
            return None

    def get_msgs(self, kind="str"):
        """Get the messages of the NatUrWB Query.

        Every Query has some additional informations that should
        get taken into account if the results are analysed.

        Parameters
        ----------
        kind : str, optional
            Should the messages be returned as a string or as a list?
            One of "str", "list".
            The default is "str".

        Returns
        -------
        list or str
            The messages of this NatUrWB-Query.
        """
        if not hasattr(self, "msgs"):
            self._make_msgs()

        if kind == "str":
            if len(self.msgs)>0:
                return "- " + "\n- ".join(self.msgs)
            else:
                return ""
        elif kind == "list":
            return self.msgs

    def _sql_query_basics(self):
        """
        Make the basic queries to the NatUrWB Database.
        Save the resulting tables in object.

        Returns
        -------
        None.

        """
        with self.db_engine.connect() as con:
            # clip urban shape with lookup table

            sql_clip = f"""
                WITH urban_geom AS (
                        SELECT ST_GeomFromText('{self.urban_shp.wkt}', 25832) as geom
                    ), clip_sim AS (
                        SELECT sim_id, gen_id, sym_nr, tkle_nr,
                            ST_Intersection(geom, (SELECT geom from urban_geom)) as geom
                        FROM tbl_simulation_polygons
                        WHERE ST_Intersects(geom, (SELECT geom from urban_geom))
                    ), inters AS (
                        SELECT sim_id, gen_id, sym_nr, tkle_nr,
                            tn.nat_id,
                            ST_Intersection(cs.geom, tn.geom) as geom
                        FROM clip_sim cs
                        JOIN tbl_nre tn
                        ON ST_Intersects(cs.geom, tn.geom)
                )
                SELECT inters.sim_id, inters.gen_id, inters.nat_id,
                        ST_UNION(geom) as geometry,
                        SUM(ST_AREA(geom)) AS area,
                        lbc.color , ltn.txt as leg_tkle_txt,
                        ltn.kurz as leg_tkle_kurz
                    FROM inters
                    JOIN leg_buek_col lbc ON lbc.sym_nr=inters.sym_nr
                    JOIN leg_tklenr ltn ON ltn.tkle_nr=inters.tkle_nr
                    WHERE ST_Dimension(inters.geom)=2
                    GROUP BY inters.sim_id, inters.gen_id, inters.nat_id,
                            lbc.color, ltn.txt, ltn.kurz;"""

            self.sim_shps_clip = gpd.read_postgis(
                sql=sql_clip,
                con = con,
                geom_col="geometry",
                index_col=["sim_id", "gen_id", "nat_id"])
            self.sim_shps_clip["anteil"] = (self.sim_shps_clip["area"] /
                                          self.sim_shps_clip["area"].sum())

            # lookup for landuses in the same NRE with same soil
            sql_ref_lanus = (
                "SELECT gen_id, nat_id, tlp.lanu_id, SUM (area) AS area, " +
                "ll.name as lanu_name FROM tbl_lookup_polygons tlp " +
                "JOIN leg_lanuid ll ON ll.lanu_id=tlp.lanu_id " +
                "WHERE gen_id IN ({genid}) AND nat_id IN ({natid}) " +
                    "AND NOT is_urban " +
                "GROUP BY gen_id, nat_id, tlp.lanu_id, ll.name").format(
                    genid=", ".join(self.sim_shps_clip.index
                                    .get_level_values("gen_id")
                              .unique().astype(str)),
                    natid=", ".join(self.sim_shps_clip.index
                                    .get_level_values("nat_id")
                              .unique().astype(str)))

            self.ref_lanus = pd.read_sql(
                sql=sql_ref_lanus,
                con = con,
                index_col=["gen_id", "nat_id", "lanu_id"])

            # get the results
            sql_results = ('''
                SELECT tr.sim_id, tsp.gen_id, tr.lanu_id, tr.bf_id,
                        n, "kap.A.", et, oa, za, bfid_area, inf, tp, wea_et as pet,
                        za_gwnah_flag
                FROM tbl_simulation_polygons tsp
                INNER JOIN tbl_results tr on tsp.sim_id = tr.sim_id
                INNER JOIN tbl_soils ts on tr.bf_id = ts.bf_id
                WHERE tsp.sim_id IN ({0})'''.format(
                    ", ".join(self.sim_shps_clip.index.get_level_values("sim_id")
                              .unique().astype(str)))
                )

            self.results = pd.read_sql(
                sql=sql_results,
                con=con,
                index_col=["sim_id", "gen_id", "bf_id", "lanu_id"])

            # get the simulation informations like flags etc.
            sql_sim_infos = ("""
                SELECT sim_id, stat_id, buek_flag, bfid_undef,
                       lanu_flag, wea_flag, wea_dist, wea_flag_n, wea_dist_n,
                       sl_flag, sl_dist, sl_std, sun_flag, sun_dist, rs_std,
                       wea_t_std, wea_et_std, wea_n_wihj_std, wea_n_sohj_std
                FROM tbl_simulation_polygons tsp
                    JOIN tbl_soils ts ON ts.gen_id=tsp.gen_id
                WHERE sim_id IN ({simids})
                GROUP BY sim_id, buek_flag, lanu_flag, wea_flag, wea_dist,
                         sl_flag, sl_dist, sun_flag, sun_dist, bfid_undef;"""
                ).format(
                    simids=", ".join(self.sim_shps_clip.index
                                     .get_level_values("sim_id")
                                     .unique().astype(str)))

            self.sim_infos = pd.read_sql(
                sql=sql_sim_infos,
                con=con,
                index_col="sim_id")
            self.sim_infos = self.sim_infos.join(
                self.sim_shps_clip[["anteil", "area"]].groupby("sim_id").sum())

    def _sql_query_ref_polys(self):
        """
        Get the reference shapes from the database from which the landuses were taken
        """
        sql_ref_polys = (
            "SELECT gen_id, nat_id, tlp.lanu_id, area, " +
            "ll.name as lanu_name, geom as geometry " +
            "FROM tbl_lookup_polygons tlp " +
            "JOIN leg_lanuid ll ON ll.lanu_id=tlp.lanu_id " +
            "WHERE gen_id IN ({0}) AND nat_id IN ({1}) " +
                "AND not is_urban;").format(
            ", ".join(self.sim_shps_clip.index.get_level_values("gen_id")\
                      .unique().astype(str)),
            ", ".join(self.sim_shps_clip.index.get_level_values("nat_id")\
                      .unique().astype(str)))

        with self.db_engine.connect() as con:
            self.ref_polys = gpd.read_postgis(
                sql=sql_ref_polys,
                con=con,
                geom_col="geometry",
                index_col=["gen_id", "nat_id", "lanu_id"])

    def _sql_nre(self):
        sql_nre = (
            """SELECT nat_id, name,
                      ST_Transform(geom, 4326) geometry
               FROM tbl_nre
               WHERE tbl_nre.nat_id in ({});""".format(
                ", ".join(self.sim_shps_clip.index.get_level_values("nat_id")
                          .unique().astype(str))))
        with self.db_engine.connect() as con:
            self.nre = gpd.read_postgis(
                sql=sql_nre,
                con=con,
                geom_col="geometry",
                index_col="nat_id",
                crs=4326)

    def _aggregate_results(
            self,
            res_agg_cols=["n", "kap.A.", "et", "pet", "runoff",
                          "oa", "za", "za_gwnah", "tp"]):
        """
        Aggregate the results to the different variables.

            1. BF_ID
            2. lanu_id
            3. nat_id
            4. sim_id
            5. gen_id

        Parameters
        ----------
        res_agg_cols : list of str, optional
            The columns of the result dataframe to aggregate.
            The default is ["n", "kap.A.", "et", "runoff", "oa", "za", "za_gwnah", "tp"].

        Raises
        ------
        ValueError
            If one of the tests of the aggregated values is not ok.
            Then it was not possible to create a NatUrWB reference.
            1. The aggregated precipitation value is significantly different
                to the original
            2. The Sum of the product of all the coefficients is not 1.

        Returns
        -------
        None.

        """
        # calculate the ZA amount near to GW and runoff:
        results = self.results.copy()
        if "runoff" in res_agg_cols:
            results["runoff"] = results["oa"] + results["za"]
        if "za_gwnah" in res_agg_cols:
            results["za_gwnah"] = results["za"] * results["za_gwnah_flag"]

        # 1. BF_ID
        # --------
        # check for forced landuses for one soil profile
        if (self.sim_infos["lanu_flag"] == 2).sum() > 0:  # alt: (results["bfid_area"].groupby(["sim_id", "lanu_id"]).sum() != 100).sum()>0:
            for (simid, genid, lanuid), df \
                    in results.groupby(["sim_id", "gen_id", "lanu_id"]):
                sum_area = df["bfid_area"].sum()
                results.loc[
                    (simid, genid, slice(None), lanuid), "bfid_area"] = (
                        df["bfid_area"] / sum_area * 100)

        # aggregate
        res_gat_1 = results[res_agg_cols].copy()
        res_gat_1 = res_gat_1.mul(results["bfid_area"].div(100).to_list(),
                                  axis=0)
        self.res_gat_1 = res_gat_1.groupby(["sim_id", "gen_id", "lanu_id"]
                                           ).sum()

        # 2. lanu_id
        # ----------
        # get landus distribution
        self.coef_lanu = (self.ref_lanus[["area"]] /
                          self.ref_lanus[["area"]].groupby(
                              ["gen_id", "nat_id"]).sum())
        self.coef_lanu.rename({"area":"coef"}, axis=1, inplace=True)

        # get missing landuses if soil group has no natural lanu in same NRE
        self.missing_lanus = (
            set(self.sim_shps_clip.index.droplevel("sim_id").unique()) -
            set(self.coef_lanu.index.droplevel("lanu_id").unique())) # gen_id, nat_id
        self.missing_lanus = pd.DataFrame(self.missing_lanus,
                                          columns=["gen_id", "nat_id"]
                                          ).set_index(["gen_id", "nat_id"])
        self.missing_lanus["resolved"] = False
        self.missing_lanus = self.missing_lanus.join(
            self.sim_shps_clip[["area"]])

        # check for those missing landuses in the surrounding areas
        if len(self.missing_lanus) != 0:
            sql_urban_geom = f"ST_GeomFromText('{self.urban_shp.wkt}', 25832)"
            sql_ref_nolanu_raw = (
                "SELECT gen_id, lanu_id, SUM(area) as area " +
                "FROM tbl_lookup_polygons "+
                "WHERE ST_Intersects(geom, " +
                        "(ST_Buffer({urban_geom}, {dist}))) " +
                    "AND gen_id IN ({genids}) "+
                    "AND not is_urban " +
                "GROUP BY gen_id, lanu_id")

            missing_genids = \
                self.missing_lanus.index.get_level_values("gen_id").unique()

            # itterate over different distances to find landuses on same soil
            with self.db_engine.connect() as con:
                for dist in [30, 60, 90, 120]:
                    ref_nolanu = pd.read_sql(
                        sql=sql_ref_nolanu_raw.format(
                            dist=dist*1000,
                            genids=", ".join(missing_genids.astype(str)),
                            urban_geom=sql_urban_geom),
                        con=con, index_col=["gen_id",  "lanu_id"])

                    if len(ref_nolanu)>0:
                        resolved_genids = \
                            ref_nolanu.index.get_level_values("gen_id").unique()
                        missing_genids = missing_genids.drop(resolved_genids)
                        self.missing_lanus.loc[
                            (resolved_genids, slice(None)), "nolanu_dist"] = dist
                        self.missing_lanus.loc[
                            (resolved_genids, slice(None)), "resolved"] = True

                        coef_nolanu_i = (
                            self.missing_lanus.loc[
                                (resolved_genids, slice(None), slice(None)), []]
                            .groupby(["gen_id", "nat_id"]).first()
                            .join(ref_nolanu))
                        coef_nolanu_i[["coef"]] = (
                            coef_nolanu_i[["area"]] /
                            (coef_nolanu_i[["area"]]
                            .groupby(["gen_id", "nat_id"]).sum()))
                        coef_nolanu_i.drop("area", inplace=True, axis=1)
                        self.coef_lanu = pd.concat([self.coef_lanu,coef_nolanu_i])

                    if len(missing_genids) == 0:
                        break

        # aggregate
        sim_nat_comb = pd.DataFrame(
            index=self.sim_shps_clip.index.droplevel("gen_id").unique())
        self.res_gat_2 = self.res_gat_1.join(sim_nat_comb).join(self.coef_lanu)
        self.res_gat_2 = \
            self.res_gat_2[res_agg_cols].mul(self.res_gat_2["coef"].to_list(),
                                             axis=0)
        self.res_gat_2 = \
            self.res_gat_2.groupby(["sim_id", "gen_id", "nat_id"]).sum()

        # 3. nat_id
        # ---------
        # get coeficients for every NAT a SIM_ID is in
        self.coef_nat = (
            self.sim_shps_clip[["area"]]
            .groupby(["sim_id", "nat_id"]).sum()
            .join(self.sim_shps_clip["area"].groupby(["sim_id"]).sum(),
                  rsuffix="_simid"))
        self.coef_nat["coef"] = \
            self.coef_nat["area"] / self.coef_nat["area_simid"]
        self.coef_nat.drop(["area", "area_simid"], axis=1, inplace=True)

        # aggregate
        self.res_sim = self.res_gat_2.join(self.coef_nat)
        self.res_sim = \
            self.res_sim[res_agg_cols].mul(self.res_sim["coef"].to_list(),
                                           axis=0)
        self.res_sim = self.res_sim.groupby(["sim_id", "gen_id"]).sum()

        # check if the precipitation didn't change
        check_n = (
            self.results[["n"]].groupby("sim_id").first()
            .join(self.res_sim[["n"]],
                  rsuffix="_gat",
                  lsuffix="_control"))
        if (~np.isclose((check_n["n_control"] - check_n["n_gat"]), 0, atol=0.01)
            ).sum() != 0 :
            raise ValueError(
                "There was an error with the gathering of the results " +
                "to one reference value per simulation shape! " +
                "\nThe resulting precipitation differes " +
                "from the input precipitation.")

        # 4. sim_id
        # ---------
        # get the coeeficients
        self.coef_sim = (
            self.sim_shps_clip[["area"]].groupby(["gen_id", "sim_id"]).sum() /
            self.sim_shps_clip[["area"]].groupby("gen_id").sum())
        self.coef_sim.rename({"area": "coef"}, axis=1, inplace=True)

        # aggregate
        self.res_gen = self.res_sim.join(self.coef_sim)
        self.res_gen = \
            self.res_gen[res_agg_cols].mul(self.res_gen["coef"].to_list(),
                                           axis=0)
        self.res_gen = self.res_gen.groupby("gen_id").sum()

        # 5. gen_id
        # ---------
        # get the coeeficients
        self.coef_gen = (self.sim_shps_clip[["area"]].groupby("gen_id").sum() /
                         self.sim_shps_clip["area"].sum())
        self.coef_gen.rename({"area": "coef"}, axis=1, inplace=True)

        # aggregate
        self.naturwb_ref = self.res_gen.join(self.coef_gen)
        self.naturwb_ref = \
            self.naturwb_ref[res_agg_cols].mul(
                self.naturwb_ref["coef"].to_list(),
                axis=0)
        self.naturwb_ref = self.naturwb_ref.sum()

        # gather all the cooefficients and check if sum is 1
        self.coef_all = (
            self.coef_gen.join(self.coef_sim, lsuffix="_gen", rsuffix="_sim")
            .join(self.coef_nat
                  .rename({"coef": "coef_nat"}, axis=1))
            .join(self.coef_lanu
                  .rename({"coef": "coef_lanu"}, axis=1))
            .join((self.results[["bfid_area"]]/100)
                  .rename({"bfid_area": "coef_bfid"}, axis=1)))

        if not np.isclose(self.coef_all.prod(axis=1).sum(), 1, atol=0.00001):
            raise ValueError(
                "There was an error with the gathering of the results " +
                "to one reference value! " +
                "\nThe sum of all the coeficients is not near to 1.")

        # calculate the relative parts of the water balance
        paras = ["runoff", "tp", "et"]
        for para in paras:
            self.naturwb_ref[para + "_rel"] = \
                self.naturwb_ref[para] / self.naturwb_ref[paras].sum()

    def get_input_paras(self, renew=False, join_results=False):
        """Get the simulation input parameters of the query.

        Parameters
        ----------
        renew : bool, optional
            Renew the input parameters in the object.
            The default is False.
        join_results : bool, optional
            Join the results to the input parameters DataFrame.
            The default is False.

        Returns
        -------
        pandas.DataFrame
            A DataFrame with the simulation input parameters.
        """
        if (not hasattr(self, "input_paras")) or renew:
            sql_input_paras = (
                "SELECT * FROM view_simulation_paras " +
                "WHERE sim_id IN ({simids}) " +
                "AND lanu_id IN ({lanuids})").format(
                simids=", ".join(self.results.index.
                    get_level_values("sim_id").unique().astype(str)),
                lanuids=", ".join(self.results.index.
                    get_level_values("lanu_id").unique().astype(str))
                )
            with self.db_engine.connect() as con:
                self.input_paras = pd.read_sql(
                    sql=sql_input_paras,
                    con=con,
                    index_col=self.results.index.names)

        if join_results:
            return self.results.drop("bfid_area", axis=1).join(self.input_paras)
        else:
            return self.input_paras

    def get_results_genid(self, renew=False):
        if not renew and hasattr(self, "results_genid"):
            return self.results_genid
        else:
            self.results_genid = self.sim_shps_clip\
                [["geometry", "leg_tkle_txt", "leg_tkle_kurz", "color"]]\
                .join(self.res_gat_2)\
                .rename({"leg_tkle_kurz": "Boden_kurz", "leg_tkle_txt": "Boden_lang",
                        "runoff":"Abfluss", "tp": "GWNB", "n": "N",
                        "et": "ET", "oa":"OA", "za": "ZA",
                        "za_gwnah": "ZA_GWnah"}, axis=1)
            return self.results_genid

    def _make_plot_sim_shps_clip(self, width=20, cex=1,
                               bbox_x_gen=0, bbox_x_nat=0):
        """
        Create the sim_shps_clip plot to represent the soil groups and the NRE
        in the urban area.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.

        Parameters
        ----------
        width : int, optional
            The width of the matplotlibs figsize.
            The default is 20.
        cex : int, optional
            Factor to stretch the fontsizes.
            The default is 1.
        bbox_x_gen : int, optional
            Factor to add to the GEN_ID legend bbox_to_anchor x coords.
            The default is 0.
        bbox_x_nat : int, optional
            Factor to add to the NRE legend bbox_to_anchor x coords.
            The default is 0.

        Returns
        -------
        matplotlib.figure.Figure

        """
        # define variables to be able to copy the plot syntax from Notebook 5.2
        # -----------------
        sim_shps_clip = self.sim_shps_clip
        height = width * 17/20

        # plot code
        # ----------
        fig, ax = plt.subplots(figsize=(width, height))

        # plot soil classes
        gen_dis = sim_shps_clip.dissolve(["gen_id", "color", "leg_tkle_kurz"])
        plots = []
        labels_gen = []
        colors_gen = []
        for (genid, color, label), df in gen_dis.groupby(["gen_id",
                                                          "color",
                                                          "leg_tkle_kurz"]):
            plot = df.plot(ax=ax, color=color, label=label, alpha=0.8,
                           legend=True, categorical=True)
            plots.append(plot)
            labels_gen.append(str(genid) + ": " + label)
            colors_gen.append(color)

        # add NRE ID and border
        # nat_dis = sim_shps_clip.dissolve("nat_id").reset_index().explode(index_parts=True)
        sql_nre_clip = (
            'SELECT tbl_nre.nat_id, name, geom ' +
            'FROM tbl_nre ' +
            "WHERE tbl_nre.nat_id in ({})").format(
                ", ".join(sim_shps_clip.index.get_level_values("nat_id").unique().astype(str)))

        with self.db_engine.connect() as conn:
            nre_clip = gpd.read_postgis(
                sql=sql_nre_clip,
                con=conn,
                geom_col="geom",
                index_col="nat_id",
                crs=25832
            )
        lut = len(np.unique(nre_clip.index.values))
        colors_nat = cm.get_cmap(name="Set1", lut=lut)(range(0, lut))
        hatches_all = ["/", "\\", "|", "-", ".", "x", "+",
                       "//", "||", "\\\\", "*", "+"] * 2
        labels_nat = []
        for (_, gdf_nat), hatch, color in zip(nre_clip.groupby("nat_id"),
                                                  hatches_all, colors_nat):
            gdf_nat.plot(ax=ax, edgecolor=color,
                         facecolor=(0, 0, 0, 0), hatch=hatch)
            labels_nat.append(gdf_nat["name"].iloc[0])

        # add urban shape
        self.urban_shp_utm.boundary.plot(ax=ax, color="k")

        # add basemap
        cx.add_basemap(ax=ax,
                       crs=sim_shps_clip.crs,
                       source=cx.providers.OpenStreetMap.Mapnik,
                       attribution_size=18 * cex)
        ax.set_axis_off()

        # set legends
        legend_nat = ax.legend(
            handles=(
                [mpl.patches.Patch(
                    edgecolor=color,
                    facecolor=(0, 0, 0, 0),
                    hatch=hatch)
                    for color, hatch in zip(colors_nat, hatches_all)] +
                [mpl.patches.Patch(color=(0,0,0,0)),
                mpl.patches.Patch(edgecolor="k", facecolor=(0,0,0,0))]),
            labels=labels_nat + ["", "Urbanes Gebiet"],
            loc=2,
            bbox_to_anchor=(-0.1 - bbox_x_nat, 1),
            labelspacing=1.5, handlelength=3, borderpad=1,
            fontsize=13 * cex, title_fontsize=15 * cex)
        for patch in legend_nat.get_patches():
            patch.set_height(20 + 8 * (width - 20)/20)
            patch.set_y(-5)
        ax.add_artist(legend_nat)

        ncol_leg_gen = max(25, len(labels_gen))//25
        ax.legend(
            handles=[mpl.patches.Patch(color=color) for color in colors_gen],
            labels=['\n        '.join(wrap(lbl, 50)) for lbl in labels_gen],
            title="      Bodengesellschaft\nGEN_ID: Kurzbeschreibung",
            loc=1,
            bbox_to_anchor=((1.25 + (ncol_leg_gen-1) * 0.28) + bbox_x_gen, 1),
            ncol=ncol_leg_gen,
            fontsize=13 * cex, title_fontsize=15 * cex)

        fig.set_tight_layout(True)

        # save fig to object
        # -------------------
        self.fig_sim_shps_clip = fig

    def _make_plot_sim_shps_clip_plotly(self):
        """Create the sim_shps_clip figure with plotly (interactive).

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.
        """
        # create df
        gen_dis = self.sim_shps_clip.dissolve(
            ["gen_id", "color", "leg_tkle_kurz"]).to_crs(4326)
        gen_dis = gen_dis.reset_index()\
            .explode(index_parts=False).reset_index(drop=True)
        urban_shp_plot = self.urban_shp_wgs.iloc[0]

        if not hasattr(self, "nre"):
            self._sql_nre()

        # extend
        bounds = np.array(urban_shp_plot.bounds)
        center_x, center_y = bounds[:2] + ((bounds[2:] - bounds[:2]) / 2)
        ext_x = bounds[2] - bounds[0]
        ext_y = bounds[3] - bounds[1]
        zoom = min(
            np.log(360/(ext_x)) / np.log(2),
            np.log(360/(ext_y)) / np.log(2),
        ) - 1

        fig = go.Figure()

        # add soils
        for i_gen, ((genid, color, tkle_kurz, tkle_txt), df) in enumerate(
                gen_dis.groupby(["gen_id", "color",
                                 "leg_tkle_kurz", "leg_tkle_txt"])):
            fig.add_choroplethmapbox(
                geojson=json.loads(df[["geometry"]].to_json()),
                z=[i_gen,] * len(df),
                locations=df.index,
                colorscale=((0, color), (1, color)),
                showscale=False,
                hovertemplate=(
                    "<b>Bodengesellschaft</b>:<br>" +
                    "GEN_ID: %{meta[0]}<br>%{meta[1]}" +
                    "<extra>%{meta[2]}</extra>"
                ),
                meta=[genid,
                      "<br>".join(wrap(tkle_kurz, 30)),
                      "<br>".join(wrap(tkle_txt, 30))],
                showlegend=True,
                hoverlabel=dict(bgcolor=color),
                name="<br>".join(wrap(str(genid) + ": " + tkle_kurz, 40)),
                marker_line_width=0,
                marker=dict(opacity=0.75),
                legendgroup="Soils",
                visible=True
            )

        # add nat_id
        n_nre = len(self.nre)
        colors_nat = [
            mpl.colors.to_hex(color) for color in
            cm.get_cmap(name="Set1", lut=n_nre)(range(0, n_nre))]
        for i_nat, (((natid, name), gdf_nat), color) in enumerate(
                zip(self.nre.groupby(["nat_id", "name"]), colors_nat)):
            fig.add_choroplethmapbox(
                geojson=json.loads(gdf_nat[["geometry"]].to_json()),
                locations=gdf_nat.index,
                z=[i_nat,] * len(gdf_nat),
                colorscale=((0, color), (1, color)),
                showscale=False,
                hovertemplate=(
                    "<b>Naturraumeinheit</b>:<br>%{meta[0]}" +
                    "<extra></extra>"
                ),
                meta=["<br>".join(wrap(name, 30))],
                showlegend=True,
                name="<br>".join(wrap(name, 40)),
                marker_line_width=0,
                marker=dict(opacity=0.75),
                legendgroup="NRE",
                visible=False
            )

        # add urban_shp
        if type(urban_shp_plot) == MultiPolygon:
            long, lat = [],[]
            for geom in urban_shp_plot.geoms:
                xy = geom.exterior.xy
                long.append(xy[0].tolist())
                lat.append(xy[1].tolist())
        else:
            long, lat = urban_shp_plot.exterior.xy
            long = list([long.tolist()])
            lat = list([lat.tolist()])

        leg_bool = True
        for lati, longi in zip(lat, long):
            fig.add_scattermapbox(
                lat=lati,
                lon=longi,
                mode = "lines",
                marker=dict(color="black"),
                legendgroup="urban shape",
                name="urbanes Gebiet",
                visible=True,
                showlegend=leg_bool,
                hoverinfo="skip"
            )
            leg_bool=False

        # update layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=zoom,
                center={"lat": center_y, "lon": center_x}),
            legend=dict(
                title=dict(
                    text="      <b>Bodengesellschaft<br>GEN_ID: Kurzbeschreibung</b>",
                    font=dict(size=16)),
                tracegroupgap=35),
            updatemenus=[dict(
                type="dropdown",
                direction="down",
                buttons=list([
                    dict(
                        args=[
                            {"visible": ([True, ] * (i_gen+1) +
                                         [False, ] * (i_nat+1) +
                                         [True,] * len(lat))},
                            {"legend.title.text":
                                "      <b>Bodengesellschaft<br>GEN_ID: Kurzbeschreibung</b>",
                            "legend.x": 1.1}],
                        label="Bodengesellschaften",
                        method="update"
                    ),
                    dict(
                        args=[
                            {"visible": ([False, ] * (i_gen+1) +
                                         [True, ] * (i_nat+1) +
                                         [True,] * len(lat))},
                            {"legend.title.text":
                                "<b>Naturraumeinheiten</b>"}],
                        label="Naturraumeinheiten",
                        method="update"
                    )
                ]),
                showactive=True,
                x=1.05,
                xanchor="left",
                y=1.1,
                yanchor="top",
                pad=dict(r=20) )],
            autosize=True,
            margin=dict(t=12, l=0, autoexpand=True),
            modebar=dict(orientation="v"),
            height=650,
            font_size=16,
            hoverlabel=dict(font=dict(size=14)),
            annotations=[
                {"text": "© GeoBasis-DE/ BKG 2018",
                "valign": "bottom", "align": "right",
                "showarrow":False,
                "xref":'paper', "yref":'paper',
                "x":0.01, "y":0.01,
                "font_size": 12}]
        )

        # save fig to object
        # -------------------
        self.fig_sim_shps_clip_plotly = fig

    def _make_plot_reference_polys(self, figsize=(15, 15)):
        """
        Create the figure with the reference shapes.

        This plot takes a bit to get created.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.

        Parameters
        ----------
        figsize : tuple, optional
            The size of the figure in a matplotlib figsize format.
            The default is (15, 15).
        """
        # define variables to be able to copy the plot syntax from Notebook 5.2
        # -----------------
        sim_shps_clip = self.sim_shps_clip

        if hasattr(self, "ref_polys"):
            ref_polys = self.ref_polys
        else:
            self._sql_query_ref_polys()
            ref_polys = self.ref_polys

        # plot code
        # ----------
        fig, ax = plt.subplots(figsize=figsize)
        ref_polys.reset_index().plot(
            ax=ax, column="lanu_name",
            categorical=True, legend=True, alpha=0.7)

        # legend
        leg = ax.get_legend()
        leg.set_label("Landnutzung")
        for text in leg.get_texts():
            text.set_text("\n".join(wrap(text.get_text(), 40)))
        leg._set_loc(2)
        leg.set_bbox_to_anchor((0.9, 1))

        cx.add_basemap(ax=ax,
                       crs=sim_shps_clip.crs,
                       source=cx.providers.OpenStreetMap.Mapnik,
                       attribution_size=18)
        ax.set_axis_off()

        # save fig to object
        # -------------------
        self.fig_reference_polys = fig

    def _make_plot_pie(self, figsize=(7, 7), do_title=True,
                       label_fontsize="x-large", title_fontsize="xx-large"):
        """
        Create the naturwb pie figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.

        Parameters
        ----------
        figsize : tuple, optional
            The size of the figure.
            The Default is (7, 7).
        do_title : bool, optional
            Should the figure have a title?
            The default is True.
        label_fontsize : str or int, optional
            The fontsize of the labels in a matplotlib fontsize format
            The default is "x-large".
        title_fontsize : str or int, optional
            The fontsize of the labels in a matplotlib fontsize format.
            Only used if do_title is True.
            The default is "xx-large".
        """
        # plot code
        # ----------
        fig, ax = plt.subplots(figsize=figsize)
        self.naturwb_ref[["runoff", "tp", "et"]].plot.pie(
            ax=ax,
            ylabel="",
            labels=[
                "Abfluss (Q)",
                "Grundwasserneubildung (GWNB)",
                "Evapotranspitation (ET)"],
            autopct='%1.0f%%',
            fontsize=label_fontsize
        )

        if do_title:
            ax.set_title(label="NatUrWB Referenz", fontsize=title_fontsize)

        fig.set_tight_layout(True)

        # save fig to object
        # -------------------
        self.fig_pie = fig

    def _make_plot_pie_plotly(self):
        """
        Create the naturwb pie figure with plotly (interactive).

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.
        """
        # define variables to be able to copy the plot syntax from Notebook 5.2
        # -----------------
        naturwb_ref = self.naturwb_ref

        # plot code
        # ----------
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c'] # mpl standarts

        fig = go.Figure(data=[
            go.Pie(
                values=(naturwb_ref[["runoff", "tp", "et"]] /
                        naturwb_ref[["runoff", "tp", "et"]].sum()),
                labels=["Abfluss (Q)", "Grundwasserneubildung (GWNB)", "Evapotranspitation (ET)"],
                hovertemplate="%{label}<br>%{value:.1%}<extra></extra>",
                texttemplate="%{value:.1%}",
                marker=dict(
                    colors=colors
                )
            )])

        fig.update_layout(
            title=dict(
                text="NatUrWB Referenz",
                font_size=20,
                x=0.5,
                xanchor="center"),
            font_size=16,
            hoverlabel=dict(font=dict(size=14)),
            legend=dict(
                orientation="h",
                valign="bottom")
        )

        # save fig to object
        # -------------------
        self.fig_pie_plotly = fig

    def _make_plot_pie_landuse(self):
        """Create the landuse pie figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.
        """
        # plot code
        # ----------
        lanu_parts = self.coef_all.prod(axis=1).groupby("lanu_id").sum().to_frame("coef")
        sql_leg = ("SELECT lanu_id, name FROM leg_lanuid " +
                "WHERE lanu_id in ({})").format(", ".join(lanu_parts.index.astype(str)))
        with self.db_engine.connect() as con:
            lanu_parts = lanu_parts.join(pd.read_sql(con=con, sql=sql_leg, index_col="lanu_id"))

        colors=list(map(
            mpl.colors.to_hex,
            cm.get_cmap("Set1_r", len(lanu_parts))(range(0, len(lanu_parts)))))
        fig = go.Figure(data=[
            go.Pie(
                values=lanu_parts["coef"],
                labels=lanu_parts["name"].apply(lambda x: "<br>".join(wrap(x, 30))),
                hovertemplate="%{label}<br>%{value:.1%}<extra></extra>",
                texttemplate="%{value:.1%}",
                marker=dict(colors=colors)
            )])
        fig.update_layout(
            title=dict(
                text="Landnutzungsverteilung",
                x=0.5,
                xanchor="center"),
            font_size=16,
            hoverlabel=dict(font=dict(size=14))
        )

        # save fig to object
        # -------------------
        self.fig_pie_landuse = fig

    def _make_plot_pie_landuse_mpl(self, figsize=(7,7), explode_small=False):
        """Create the landuse pie figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.
        """
        # get df
        # ----------
        lanu_parts = self.coef_all.prod(axis=1).groupby("lanu_id").sum().to_frame("coef")
        sql_leg = ("SELECT lanu_id, name FROM leg_lanuid " +
                   "WHERE lanu_id in ({})").format(
                       ", ".join(lanu_parts.index.astype(str)))
        with self.db_engine.connect() as con:
            lanu_parts = lanu_parts.join(
                pd.read_sql(con=con, sql=sql_leg, index_col="lanu_id"))

        colors=list(map(
            mpl.colors.to_hex,
            cm.get_cmap("Set1_r", len(lanu_parts))(range(0, len(lanu_parts)))))

        lanu_parts["colors"] = colors
        lanu_parts["name"] = lanu_parts["name"].apply(
            lambda x: x.replace("/", "/\n"))
        lanu_parts = lanu_parts.sort_values("coef")
        lanu_parts = lanu_parts[lanu_parts["coef"]>0.001]

        # make plot
        fig, ax = plt.subplots(figsize=figsize)
        lanu_parts.plot.pie(
                    ax=ax,
                    y="coef",
                    ylabel="",
                    labels=lanu_parts["name"],
                    colors=colors,
                    autopct='%1.0f%%',
                    fontsize=12,
                    labeldistance=None,
                    pctdistance=0.8,
                    startangle=15,
                    explode=lanu_parts["coef"].apply(
                        lambda x: 0.3 if x < 0.03 and explode_small else 0)
                )
        ax.get_legend().remove()
        fig.legend(loc="lower right", bbox_to_anchor=(1.25,0.2))
        ax.set_title("Landnutzungsverteilung")

        # save fig to object
        # -------------------
        self.fig_pie_landuse_mpl = fig

    def _make_plot_ternary(self, do_size=False, width=1000,
                           marker_sizemin=2.5, marker_sizecoef=0.04):
        """
        Create the ternary figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.

        Parameters
        ----------
        do_size : boolean, optional
            Should the size of the dots represent the share the dot represents?
            The default is False.
        width : int, optional
            The width of the figure.
            The default is 1000.
        marker_sizemin : int, optional
            The Minimum size of the dots. Only relevant if do_size=True.
            The default is 2.5.
        marker_sizecoef : TYPE, optional
            The coefficient to use to scale the size of the dots.
            Only relevant if do_size=True.
            The default is 0.04.

        Returns
        -------
        plotly.graph_objs.Figure
            The plotly figure object of the plot.
        """
        # plot code
        # ----------
        # create dataframe
        res_3_ternary = self.res_sim.copy()
        naturwb_ternary = self.naturwb_ref.copy()

        paras = ["runoff", "tp", "et"]
        for para in paras:
            res_3_ternary[para + "_part"] = \
                res_3_ternary[para] / res_3_ternary[paras].sum(axis=1)
            naturwb_ternary[para + "_part"] = \
                naturwb_ternary[para] / naturwb_ternary[paras].sum()

        res_3_ternary = res_3_ternary.join(self.coef_gen * self.coef_sim)

        # add legend information to the dataframe
        sql_ternary_leg = (
            "SELECT tsp.sim_id, txt as leg_txt, kurz as leg_kurz, color " +
            "FROM tbl_simulation_polygons tsp " +
            "JOIN leg_tklenr lt ON lt.tkle_nr=tsp.tkle_nr " +
            "JOIN leg_buek_col lbc ON lbc.sym_nr=tsp.sym_nr "
            "WHERE tsp.sim_id in ({simids})"
        ).format(
            simids=", ".join(
                res_3_ternary.index.get_level_values("sim_id")
                .unique().astype(str)
            )
        )

        with self.db_engine.connect() as con:
            ternary_leg = pd.read_sql(sql=sql_ternary_leg,
                                      con=con,
                                      index_col="sim_id")
            res_3_ternary = res_3_ternary.join(ternary_leg)

        # initiate the figure
        fig = go.Figure()

        # plot the different soil
        for (genid, color), df in res_3_ternary.groupby(["gen_id", "color"]):
            # create marker dict depending if the size should be dependent
            if do_size:
                marker_dict = dict(
                    opacity=0.7, color=color,
                    size=df["coef"],
                    sizeref=marker_sizecoef * res_3_ternary["coef"].max(),
                    sizemin=marker_sizemin)
            else:
                marker_dict = dict(color=color)

            # wrap the labels
            df["leg_txt"] = df["leg_txt"].apply(
                lambda x: "<br>".join(wrap(x, 30)))

            # add the traces
            fig.add_trace(
                go.Scatterternary(
                    a=df["runoff_part"],
                    b=df["tp_part"],
                    c=df["et_part"],
                    mode="markers",
                    hovertemplate=(
                        "ET:        %{c:.1%} (%{customdata[0]:.0f} mm/a)<br>" +
                        "Q:          %{a:.1%} (%{customdata[1]:.0f} mm/a)<br>" +
                        "GWNB: %{b:.1%} (%{customdata[2]:.0f} mm/a)<br><br>" +
                        "Anteil an NatUrWB-Zielwert: %{customdata[3]:.2%}" +
                        "<extra>GEN_ID: %{meta[0]}<br>%{customdata[4]}" +
                        "</extra>"
                    ),
                    meta=[genid],
                    customdata=df[
                        ["et", "runoff", "tp", "coef", "leg_txt"]],
                    name=str(genid),  # "<br>".join(wrap(leg_kurz, 20)),
                    legendgroup="Bodengesellschaft",
                    marker=marker_dict,
                    cliponaxis=False
                )
            )

        # plot the naturwb-reference
        fig.add_trace(
            go.Scatterternary(
                a=naturwb_ternary[["runoff_part"]],
                b=naturwb_ternary[["tp_part"]],
                c=naturwb_ternary[["et_part"]],
                mode="markers",
                hovertemplate=(
                    "ET:        %{c:.1%} (%{meta[0]:,.0f} mm/a)<br>" +
                    "Q:          %{a:.1%} (%{meta[1]:,.0f} mm/a)<br>" +
                    "GWNB: %{b:.1%} (%{meta[2]:,.0f} mm/a)" +
                    "<extra>NatUrWB-Zielwert</extra>"),
                meta=[naturwb_ternary[["et", "runoff", "tp"]]],
                name="NatUrWB-Zielwert",
                legendgroup="Zielwert",
                hoverinfo="text",
                marker=dict(
                    symbol=17, size=20, color="#007bff",
                    line_color="#000000", line_width=1.5),
                cliponaxis=False
            )
        )

        # update layout
        tickvals = np.arange(0, 1.2, 0.2)
        ticktext = list(map(lambda x: x + " %",
                            np.arange(0, 120, 20).astype(str)))
        width = min(1500, max(800, width))
        height = width - 250

        fig.update_layout(
            legend=dict(
                title=dict(
                    text="Bodengesellschafts ID",
                    font=dict(size=16)),
                tracegroupgap=35
            ),
            ternary=dict(
                aaxis=dict(
                    title="",
                    color="#4B8A08",
                    ticks="outside",
                    tickangle=0,
                    tickvals=tickvals, ticktext=ticktext,
                    showline=True, linecolor="#4B8A08",
                    showgrid=True, gridcolor="#4B8A08"),
                baxis=dict(
                    title="", color="#8A2908",
                    ticks="outside", tickangle=60,
                    tickvals=tickvals, ticktext=ticktext,
                    showline=True, linecolor="#8A2908",
                    showgrid=True, gridcolor="#8A2908"),
                caxis=dict(
                    title="",  color="#0B2161",
                    ticks="outside", tickangle=-60,
                    tickvals=tickvals, ticktext=ticktext,
                    showline=True, linecolor="#0B2161",
                    showgrid=True, gridcolor="#0B2161",
                    hoverformat="ET: %{a:2}")
            ),
            annotations=[
                dict(text="Abfluss",
                     x=0.07, xref="paper",
                     y=0.5, yref="paper",
                     textangle=-60,
                     font=dict(color="#4B8A08", size=16),
                     align="left", showarrow=False),
                dict(text="Grundwasserneubildung",
                     x=0.5, xref="paper",
                     y=0.00018571*height-0.31214, yref="paper",
                     font=dict(color="#8A2908", size=16),
                     align="left", showarrow=False),
                dict(text="Evapotranspiration",
                     x=0.97, xref="paper",
                     y=0.5, yref="paper",
                     textangle=60,
                     font=dict(color="#0B2161", size=16),
                     align="left", showarrow=False)
            ],
            clickmode="event+select",
            hovermode="closest",
            width=width,
            height=height,
            font_size=16,
            hoverlabel=dict(font=dict(size=14)),
            margin=dict(b=120, r=120)
        )

        if do_size:
            fig.update_layout(
                legend=dict(
                    itemsizing="constant"))

        # save fig to object
        # -------------------
        self.fig_ternary = fig

    def _make_plot_bar(self):
        """Create the Bar figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.
        """
        # create dfs
        res_bar = self.res_gen.copy()
        naturwb_bar = self.naturwb_ref.copy()
        paras = ["runoff", "tp", "et"]
        for para in paras:
            res_bar[para + "_part"] = \
                res_bar[para] / res_bar[paras].sum(axis=1)
            naturwb_bar[para + "_part"] = \
                naturwb_bar[para] / naturwb_bar[paras].sum()

        # create dicts for the plot labels
        name_dict = {
            "legend": {
                "et_part": "Evaoptranspiration (ET)",
                "runoff_part": "Abfluss (Q)",
                "tp_part": "Grundwasserneubildung (GWNB)"},
            "short": {
                "et_part": "ET",
                "runoff_part": "Q",
                "tp_part": "GWNB"
            }
        }
        col_dict = {
            "et_part": "blue",
            "runoff_part": "green",
            "tp_part": "brown"}

        # create the plot
        fig = go.Figure()

        # add naturwb bar
        for col in ["tp_part", "runoff_part", "et_part"]:
            fig.add_trace(
                go.Bar(
                    x=['NatUrWB-Referenz'],
                    y=naturwb_bar[[col]]*100,
                    text=name_dict["legend"][col],
                    hovertemplate='%{y:.2f}%<br>%{meta}<extra>%{x}</extra>',
                    meta=name_dict["short"][col],
                    name=name_dict["legend"][col],
                    marker=dict(color=col_dict[col])
                )
            )

        # add other soils
        start = 2
        for genid, df in res_bar.groupby("gen_id"):
            for col in ["tp_part", "runoff_part", "et_part", ]:
                fig.add_trace(
                    go.Bar(
                        x=[genid],
                        text=genid,
                        y=df[col]*100,
                        hovertemplate=(
                            '%{label:.2f}%<br>%{meta}<extra>%{x}</extra>'),
                        meta=[name_dict["short"][col], ],
                        name=name_dict["legend"][col],
                        marker=dict(color=col_dict[col]),
                        showlegend=False,
                        opacity=0.7
                    )
                )
            start += len(df) + 1

        # update the layout
        fig.update_layout(
            barmode='stack',
            xaxis=dict(
                type='category',
                categoryorder='array',
                categoryarray=['NatUrWB-Referenz', ""]),
            yaxis=dict(
                title='Anteil am Niederschlag<br>und kapillaren Aufstieg in %'),
            annotations=[
                dict(text="Bodengesellschafts-ID",
                     x=0.6, y=-0.2, xref="paper", yref="paper",
                     align="left", showarrow=False)
            ],
            font_size=16,
            hoverlabel=dict(font=dict(size=14))
        )

        # save fig to object
        # -------------------
        self.fig_bar = fig

    def _make_plot_sankey(self, figsize=(15, 15), cex=1, add_pet=True):
        """
        Create the Sankey figure.

        It is recommended to use the plot or plot_web methode to create the plot figure not this function.

        Parameters
        ----------
        figsize : tuple of 2 int, optional
            The size of the figure.
            The default is (15, 15).
        cex : float, optional
            The factor to change the size of the labels.
            The default is 1.
        add_pet : bool, optional
            Should the potential evapotranspiration be added to the plot?
            The default is True.

        Returns
        -------
        matplotlib.figure.Figure.

        """
        # define variables to be able to copy the plot syntax from Notebook 5.2
        # -----------------
        df_sankey = self.naturwb_ref.copy()

        # plot code
        # ----------
        df_sankey["za_oa"] = df_sankey["za"] - df_sankey["za_gwnah"]

        with pkg_resources.open_binary(
            data, "Wasserbilanz_raw.jpg") as f:
            bg = plt.imread(f)

        scale = 1/df_sankey[["n", "kap.A."]].sum()*140
        gap = 20
        color = (0.12156862745098039, 0.4666666666666667,  0.7058823529411765,
                 0.8)
        radius = 20
        x_offset = 320
        et_width = df_sankey["et"] * scale
        tot_width = df_sankey[["n", "kap.A."]].sum() * scale
        oa_width = df_sankey["oa"] * scale
        tp_width = df_sankey["tp"] * scale
        zagw_width = df_sankey["za_gwnah"] * scale
        soil_width = 313
        x_abf_mid = 780
        y_abf_ground = -41
        y_offset = max(tot_width/2 - et_width + 2*radius + oa_width/2,
                       tot_width/2 - 1/3 * et_width)
        extent = (-bg.shape[1]/2+x_offset, bg.shape[1]/2+x_offset,
                  -bg.shape[0]/2+y_offset, bg.shape[0]/2+y_offset)

        fig, ax = plt.subplots(figsize=figsize)

        ax.imshow(bg, extent=extent)

        # create Sankey diagramm
        sk = _SankeyNWB(ax=ax, unit=" mm/a", scale=scale,
                        shoulder=0, gap=gap, radius=radius, margin=20,
                        offset=-80, format="%.1F")

        # main Sankey
        #############
        len_tp = soil_width - y_offset - tot_width/2 - radius - tp_width/2
        # remove flows with 0
        flows_sk1=pd.concat([
                df_sankey[["n", "kap.A."]],
                -df_sankey[["et", "oa"]],
                -df_sankey[["za", "tp"]]]
            ).to_list()
        labels_sk1=["Niederschlag", "kapillarer Aufstieg",
                "Evapotranspiration", "Oberflächenabfluss",
                "Zwischenabfluss", "Tiefenperkolation"]
        orientations_sk1=[1,-1,
                    1, 1,
                    0, -1]
        pathlengths_sk1=[100+y_offset, 245-y_offset-radius,
                    150+y_offset, 20,
                    50, len_tp]
        pops_count_sk1 = 0
        for i, flow in enumerate(flows_sk1):
            if flow == 0:
                j = i - pops_count_sk1
                flows_sk1.pop(j)
                labels_sk1.pop(j)
                orientations_sk1.pop(j)
                pathlengths_sk1.pop(j)
                pops_count_sk1 += 1
        sk.add(patchlabel="",
            flows=flows_sk1,
            labels=labels_sk1,
            orientations=orientations_sk1,
            trunklength=180, alpha=0.8,
            pathlengths=pathlengths_sk1
            )

        # ZA-Sankey
        ###########
        if df_sankey["za"] != 0:
            # remove flows with 0
            flows_sk2=pd.concat([
                df_sankey[["za"]],
                -df_sankey[["za_oa", "za_gwnah"]]]).to_list()
            labels_sk2=["delete",
                    "Zwischenabfluss\nzum Abfluss",
                    "Zwischenabfluss\nbei hohem Grundwasser"]
            orientations_sk2=[0, 0, -1]
            len_zagw = soil_width - y_offset - tot_width/2 + tp_width - radius * 2 - zagw_width * 3/2
            pathlengths_sk2=[50,
                        635-x_offset-gap-zagw_width, #998
                        len_zagw ]
            pops_count_sk2 = 0
            for i, flow in enumerate(flows_sk2):
                if flow == 0:
                    j = i - pops_count_sk2
                    flows_sk2.pop(j)
                    labels_sk2.pop(j)
                    orientations_sk2.pop(j)
                    pathlengths_sk2.pop(j)
                    pops_count_sk2 += 1
            sk.add(patchlabel="",
                flows=flows_sk2,
                labels=labels_sk2,
                orientations=orientations_sk2,
                trunklength=130, alpha=0.8,
                pathlengths=pathlengths_sk2,
                prior=0,
                connect=(labels_sk1.index("Zwischenabfluss"),0)
                )

        # aditional arrows
        ##################
        skouts = sk.finish()
        self.skouts = skouts

        # add potential evapotranspiration
        if add_pet:
            et_label = skouts[0].texts[labels_sk1.index("Evapotranspiration")]
            et_label.set_text(et_label.get_text()+
                            f"\n(pot. ET: {self.naturwb_ref['pet'].round():.0f} mm/a)")

        # add Path for OA
        if oa_width != 0:
            oa_tip = skouts[0].tips[labels_sk1.index("Oberflächenabfluss")]
            oapath_raw = [
                (mplPath.MOVETO, oa_tip),
                (mplPath.LINETO, oa_tip - [oa_width / 2, oa_width / 2]),
                (mplPath.LINETO, (oa_tip[0] - oa_width / 2,
                                y_offset - radius - oa_width))]
            oapath_raw.extend(
                sk._arc(quadrant=1, cw=False,
                        radius=radius + oa_width,
                        center=(oa_tip[0] + oa_width / 2 + radius,
                                y_offset - radius)))
            oapath_raw.extend([
                (mplPath.LINETO, (670, y_offset + oa_width)),
                (mplPath.LINETO, (670 + oa_width/2, y_offset + oa_width/2)),
                (mplPath.LINETO, (670, y_offset)),
                (mplPath.LINETO, (oa_tip[0] + oa_width/2 + radius, y_offset))])
            oapath_raw.extend(
                sk._arc(quadrant=1, cw=True,
                        radius=radius,
                        center=(oa_tip[0] + oa_width / 2 + radius,
                                y_offset - radius)))
            oapath_raw.extend([
                (mplPath.LINETO, oa_tip + [oa_width / 2, + oa_width / 2])])

            codes, vertices = zip(*oapath_raw)
            oapath = mplPath(vertices=vertices, codes=codes, closed=True)
            ax.add_artist(PathPatch(oapath, color=color))

        # add Path for ZA GWNAH
        if zagw_width != 0:
            # hinweg
            zagw_tip = skouts[1].tips[labels_sk2.index("Zwischenabfluss\nbei hohem Grundwasser")]
            zagw_path_raw = [(mplPath.MOVETO, zagw_tip),
                            (mplPath.LINETO, zagw_tip + [zagw_width / 2, zagw_width / 2]),
                            (mplPath.LINETO, (zagw_tip[0] + zagw_width / 2,
                                            zagw_tip[1]))
                            ]
            zagw_path_raw.extend(sk._arc(quadrant=2, cw=True, radius=radius,
                                        center=(zagw_tip[0] + zagw_width / 2 + radius,
                                                zagw_tip[1])))
            zagw_path_raw.extend(sk._arc(quadrant=3, cw=True, radius=radius,
                                        center=(x_abf_mid - radius - zagw_width/2,
                                                zagw_tip[1] )))
            zagw_path_raw.extend([
                (mplPath.LINETO, (x_abf_mid - zagw_width/2, y_abf_ground - zagw_width/2)),
                (mplPath.LINETO, (x_abf_mid, y_abf_ground))])

            # rückweg
            zagw_path_raw.extend([
                (mplPath.LINETO, (x_abf_mid + zagw_width/2, y_abf_ground - zagw_width/2)),
                (mplPath.LINETO, (x_abf_mid + zagw_width/2, zagw_tip[1] + zagw_width/2)),
            ])
            zagw_path_raw.extend(sk._arc(quadrant=3, cw=False, radius=radius + zagw_width,
                                        center=(x_abf_mid - radius - zagw_width/2,
                                                zagw_tip[1] )))
            zagw_path_raw.extend(sk._arc(quadrant=2, cw=False,
                                        radius=radius + zagw_width,
                                        center=(zagw_tip[0] + zagw_width / 2 + radius,
                                                zagw_tip[1])))
            zagw_path_raw.extend([
                (mplPath.LINETO, zagw_tip + [-zagw_width / 2, zagw_width / 2])])

            codes, vertices = zip(*zagw_path_raw)
            zagwpath = mplPath(vertices=vertices, codes=codes, closed=True)
            ax.add_artist(PathPatch(zagwpath, color=color))

            # add Information Textbox
            ax.text(x=x_abf_mid, y=y_abf_ground - 100,
                    s="Dieser Anteil wird hier \ndem Abfluss zugeordnet.\nWenn möglich selbst entscheiden.",
                    ha='center', va='center',
                    fontsize=skouts[0].texts[0].get_fontsize()*cex,
                    backgroundcolor="#FFFFFF")

        # change label background and patch color
        for skout in skouts:
            skout.patch.set_color(color)
            for text in skout.texts:
                text.set_backgroundcolor("#FFFFFF")

        # change labels position
        if "Zwischenabfluss" in labels_sk1:
            ind_za = labels_sk1.index("Zwischenabfluss")
            skouts[0].texts[ind_za].set_x(
                skouts[0].texts[ind_za].get_position()[0] + 130)
        if "Oberflächenabfluss" in labels_sk1:
            ind_oa = labels_sk1.index("Oberflächenabfluss")
            if "Zwischenabfluss" in labels_sk1:
                pos_za = skouts[0].texts[labels_sk1.index("Zwischenabfluss")].get_position()
                pos_oa = (pos_za[0] , y_offset + + oa_width/2)
            else:
                pos_oa = (300, y_offset + oa_width/2)
            skouts[0].texts[ind_oa].set_position(pos_oa)
        if "Zwischenabfluss\nzum Abfluss" in labels_sk2:
            ind_zagw = labels_sk2.index("Zwischenabfluss\nzum Abfluss")
            skouts[1].texts[ind_zagw].set_x(
                skouts[1].texts[ind_zagw].get_position()[0] - 50)

        skouts[1].texts[0].remove()

        # change labels fontsize
        for skout in skouts:
            for text in skout.texts:
                text.set_fontsize(text.get_fontsize() * cex)

        # layout
        ax.set_axis_off()
        fig.set_tight_layout(True)

        # save fig to object
        # -------------------
        self.fig_sankey = fig

    def _make_msgs(self):
        self.msgs = []

        # get messages for unsimulated area
        self.area_def_anteil = \
            self.sim_shps_clip["area"].sum() / self.urban_shp.area
        self.area_undef_anteil = 1 - self.area_def_anteil

        if self.area_undef_anteil > 0.9:
            self.msgs.append(
                MSGS_RAW["area_undef"]["all"].format(
                    area_undef_anteil=self.area_undef_anteil))
        elif self.area_undef_anteil > 0.0001:
            self.msgs.append(
                MSGS_RAW["area_undef"]["part"].format(
                    area_def_anteil=self.area_def_anteil,
                    area_undef_anteil=self.area_undef_anteil))

        # get the share of undefined soils
        if self.sim_infos["bfid_undef"].sum() > 0:
            self.msgs.append(
                MSGS_RAW["bfid_undef"].format(
                    bfid_undef=(self.sim_infos["bfid_undef"] / 100
                                * self.sim_infos["anteil"]
                                ).sum()))


        # messages for the lanu_flag
        # --------------------------
        # get the share of the polygons with missing landuses (lanu_flag=2)
        self.missing_lanus["anteil"] = \
            self.missing_lanus["area"] / self.sim_shps_clip["area"].sum()
        self.anteil_nolanu = \
            self.missing_lanus[["anteil", "resolved"]].groupby("resolved").sum()

        # create the messages manualy
        #lanu_flag 1
        anteil_nolanu_tot = self.anteil_nolanu["anteil"].sum()
        if anteil_nolanu_tot > 0.0001:
            msg = MSGS_RAW["lanu_flag"]["1"].format(
                anteil_nolanu=anteil_nolanu_tot)
            if True in self.anteil_nolanu.index:
                msg += MSGS_RAW["lanu_flag"]["1_resolved"].format(
                    anteil_nolanu_resolved=\
                        self.anteil_nolanu.loc[True, "anteil"] / anteil_nolanu_tot,
                        dist_mean=self.missing_lanus["nolanu_dist"].mean())
            if False in self.anteil_nolanu.index:
                msg += MSGS_RAW["lanu_flag"]["1_resolved"].format(
                    anteil_nolanu_notresolved=\
                        self.anteil_nolanu.loc[True, "anteil"] / anteil_nolanu_tot,
                    anteil_lanu_notresolved_tot=\
                        self.anteil_nolanu.loc[True, "anteil"])
            self.msgs.append(msg)

        # lanu flag 2
        anteil_lanu2 = self.sim_infos.loc[
            self.sim_infos["lanu_flag"] == 2, "anteil"
            ].sum()
        if anteil_lanu2 > 0.0001:
            self.msgs.append(MSGS_RAW["lanu_flag"]["2"].format(anteil_2=anteil_lanu2))

        # messages for the buek_flag, wea_flag, wea_flag_n, sl_flag
        # ---------------------------------------------------------
        # get the mean and maximum distance for the weather and slope rastercels
        flag_dict = {}
        for para in ["wea_dist", "wea_dist_n", "sl_dist", "sun_dist"]:
            if self.sim_infos[para].sum() != 0:
                dist = (
                    self.sim_infos[para] * self.sim_infos["area"] /
                    self.sim_infos.loc[~self.sim_infos[para].isna(), "area"].sum())
                flag_dict.update({
                    para + "_mean": dist.mean(),
                    para + "_max": dist.max()})

        # create the messages for the buek_flag, wea_flag, sl_flag and sun_flag
        for col in ["buek_flag", "wea_flag", "wea_flag_n", "sl_flag", "sun_flag"]:
            flag_agg = self.sim_infos.loc[self.sim_infos[col] != 0,
                                          [col, "anteil"]].groupby(col).sum()
            flag_agg = flag_agg[flag_agg["anteil"] > 0.0001]
            if len(flag_agg) > 0:
                # get the amount of all those flags
                flag_dict.update({"anteil_all": flag_agg["anteil"].sum()})

                # calculate the respecitve shares of the flags
                for flag, row in flag_agg.iterrows():
                    flag_dict.update(
                        {"anteil_{:d}".format(flag): row["anteil"]})

                # creat the message
                msg = ""
                for flag, _ in flag_agg.iterrows():
                    if str(flag) not in MSGS_RAW[col].keys():
                        continue
                    msg += MSGS_RAW[col][str(flag)].format(**flag_dict)

                # add to the msgs with header
                if len(msg) > 0:
                    self.msgs.append(
                        MSGS_RAW[col]["allg"].format(**flag_dict) + msg)

        # messages for the high standard deviations
        # -----------------------------------------
        for para, tresh in zip(
                ["sl", "wea_n_wihj", "wea_n_sohj", "wea_t", "wea_et", "rs"],
                [20, 40, 40, 0.5, 25, 0.4]):
            para_std = para + "_std"
            sim_infos_para = self.sim_infos.loc[
                self.sim_infos[para_std] >= tresh, [para_std, "anteil"]]
            if sim_infos_para["anteil"].sum() > 0.0001:
                self.msgs.append(MSGS_RAW[para_std].format(
                    anteil=sim_infos_para["anteil"].sum(),
                    grenze_std=tresh,
                    max_std=sim_infos_para[para_std].max()
                ))

        # messages for the special station ids
        # ------------------------------------
        for stat_id in MSGS_RAW["special_stat_ids"].keys():
            if int(stat_id) in self.sim_infos["stat_id"].values:
                self.msgs.append(
                    MSGS_RAW["special_stat_ids"][stat_id].format(
                        anteil=self.sim_infos.loc[
                            self.sim_infos["stat_id"] == int(stat_id), "anteil"].sum()))


# this is a cli setup mainly to debug the package
if __name__ == '__main__':
    from max_fun.geometry import geoencode
    import click
    import time

    @click.command()
    @click.option('--db_user', help='NatUrWB Database username')
    @click.option('--db_pwd', help='NatUrWB Database password')
    @click.option('--db_host', help='NatUrWB Database host')
    @click.option('--urban_name', help='Name of the urban area to query for')
    @click.option('--do_plots', help='Should the plotting be tested', type=bool)
    def cli(db_user, db_pwd, db_host, urban_name, db_port=5432, db_schema="naturwb",
                  do_plots=False):
        click.echo('creating NatUrWB-Pool object!')
        pool = Pool(1,
                    db_pwd=db_pwd,
                    db_user=db_user,
                    db_host=db_host,
                    db_port=db_port,
                    db_schema=db_schema)

        click.echo('creating urban_shp!')
        urban_shp = geoencode(urban_name)

        click.echo('starting query!')
        start = time.time()
        Query(urban_shp=urban_shp, db_engine=pool.engine, do_plots=do_plots)
        end = time.time()
        click.echo(f'Execution time: {end-start}')
        click.echo('done!')

    cli()