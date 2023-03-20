# from django.http import HttpResponse # static http page
from django.shortcuts import render
from .forms import EnterPolygonForm #, SearchPolygonQuery
from django.contrib.gis.geos import GEOSGeometry
from aldjemy.core import get_engine
from .functions.geometry import geoencode
from .functions.naturwb import Query as NWBQuery
from shapely.wkt import loads as wkt_loads
import traceback
from django.shortcuts import redirect
from .models import NaturwbSettings, CachedResults
from .functions.naturwb_db import results_to_db
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
import geopandas as gpd
import pandas as pd

# for result_download
import tempfile
from pathlib import Path
import zipfile
from django.http import HttpResponse, StreamingHttpResponse 
from django.core.files import File
import io
import datetime
import textwrap
from geodjango.settings import DEBUG


class Wartungsmodus:
    @property
    def state(self):
        return NaturwbSettings.objects.get(pk="Wartungsmodus").value

context_base = {
    'wartungsmodus': Wartungsmodus(),
    'debug': DEBUG}

app_dir = Path(__file__).parent
with open(app_dir.joinpath("data/README-part-Input.txt"), encoding="iso-8859-1") as f:
    README_PART_INPUT = f.read()
with open(app_dir.joinpath("data/README-part-results.txt"), encoding="iso-8859-1") as f:
    README_PART_RESULT = f.read()

# Create your views here.
def get_ref_view(request, *args, **kwargs):
    initial_data = {"geom": None}
    context = {
        "error_biggeom": False,
        'error_nogeom': False,
        **context_base
    }

    # check if it was redirected because of missing geom
    if "error_nogeom" in request.GET:
        context.update({"error_nogeom": bool(request.GET["error_nogeom"])})

    # check if it was redirected because of geom that was too big
    if "error_biggeom" in request.GET:
        context.update({"error_biggeom": bool(request.GET["error_biggeom"])})

    # do the city query if given and set initial data
    if "search_query" in request.GET:
        try:
            geom = geoencode(request.GET["search_query"])
            initial_data["geom"] = str(geom)
        except Exception as ex:
            print(ex)
            print(traceback.format_exc())
            context.update({
                "error_geoencoding": True, 
                "search_query_name": request.GET["search_query"]})

    context.update({
        'poly_form': EnterPolygonForm(None, initial=initial_data)})

    return render(request, "get_ref.html", context)

@csrf_protect
@require_POST
def result_view(request, *args, **kwargs):
    # check for empty geom
    if 'geom' not in request.POST:
        return redirect("/get_ref/?error_nogeom=True")

    urban_geom = GEOSGeometry(request.POST['geom'], 4326)

    # check size
    if urban_geom.transform(25832, True).area > 1e9:
        return redirect("/get_ref/?error_biggeom=True")

    # make naturwb query
    try:
        nwbquery = NWBQuery(
            urban_shp=wkt_loads(urban_geom.wkt), 
            db_engine=get_engine(),
            do_plots=False)

        context = {
            "messages": nwbquery.msgs,
            "success": True,
            "plot_sim_shps_clip_plotly": nwbquery.plot_web("sim_shps_clip_plotly"),
            # "plot_pie": nwbquery.plot_web("pie", figsize=(7, 7)),
            "plot_pie_plotly": nwbquery.plot_web("pie_plotly"),
            "plot_sankey": nwbquery.plot_web("sankey", figsize=(17,17), cex=1.5),
            "plot_ternary": nwbquery.plot_web("ternary", width=1000, do_size=True),
            "plot_pie_lanu": nwbquery.plot_web("pie_landuse"),
            "et_rel": "{:.0%}".format(nwbquery.naturwb_ref["et_rel"]).replace('%', ' %'),
            "a_rel": "{:.0%}".format(nwbquery.naturwb_ref["runoff_rel"]).replace('%', ' %'),
            "tp_rel": "{:.0%}".format(nwbquery.naturwb_ref["tp_rel"]).replace('%', ' %'),
            "natids": nwbquery.sim_shps_clip.index.get_level_values("nat_id").unique(),
            "urban_geom": request.POST['geom'],
            "cached": False,
            **context_base
            }

    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        context = {
            "success": False,
            **context_base
        }
        return render(request, "result.html", context)

    # save the results to DB
    try: 
        # save the landuse results to the database
        try:
            if NaturwbSettings.objects.get(pk="save_to_db").value:
                results_to_db(nwbquery)
        except NaturwbSettings.DoesNotExist:
            print("No setting parameter 'save_to_db' in the naturwb_settings table in the database")

        # save the results to the caching table in the database
        if NaturwbSettings.objects.get(pk="cache_result_to_db"):
            cache = CachedResults.objects.create_cache(
                results_genid=nwbquery.get_results_genid(),
                stat_ids=nwbquery.sim_infos["stat_id"].unique(),
                messages=nwbquery.msgs
            )
            context.update({"cache_uuid": cache.uuid, "cached":True})
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())

    return render(request, "result.html", context)

@csrf_protect
@require_POST
def result_download(request, *args, **kwargs):
    # get results from cache
    try:
        if "cache_uuid" in request.POST:
            res_gen, stat_ids, msgs = CachedResults.objects.get_cache(
                uuid=request.POST["cache_uuid"])
        else:
            raise Exception("No Cache found")
    except:
        if "urban_geom" in request.POST:
            urban_geom = GEOSGeometry(request.POST['urban_geom'])
            nwbquery = NWBQuery(
                urban_shp=wkt_loads(urban_geom.wkt), 
                db_engine=get_engine(),
                do_plots=False)
            res_gen = nwbquery.get_results_genid()
            stat_ids = nwbquery.sim_infos["stat_id"].unique()
            msgs = nwbquery.msgs
        
    # wrap messages
    new_msgs = []
    wrapper = textwrap.TextWrapper(width=150)
    for msg in msgs:
        new_msgs.append(" - " + "\n   ".join(wrapper.wrap(msg)))

    # create README.txt
    with tempfile.TemporaryDirectory() as tmp_dir:
        # create results shape file
        tmp_dir_fp = Path(tmp_dir).joinpath("temp")
        tmp_dir_fp.mkdir()
        if "add_result" in request.POST:
            res_gen.to_file(tmp_dir_fp.joinpath("results.shp"))

        # create input files
        if "add_input" in request.POST:
            sim_ids = res_gen.index.get_level_values("sim_id").unique().astype(str)
            sim_in_dir = tmp_dir_fp.joinpath("input")
            sim_in_dir.mkdir()
            simids_sql_where = f"WHERE sim_id IN ({', '.join(sim_ids)})"
            gpd.read_postgis(
                f"SELECT sim_id, geom FROM tbl_simulation_polygons {simids_sql_where};",
                con=get_engine(),
                crs=25832,
                geom_col="geom"
            ).to_file(sim_in_dir.joinpath("Modellgebiete.shp"))
            
            pd.read_sql(
                f"SELECT * FROM view_simulation_paras {simids_sql_where};",
                con=get_engine()
            ).to_csv(sim_in_dir.joinpath("Simulations-Parameter.csv"), 
                     index=False)
        
        # create zip file localy/memory
        if len(res_gen) > 500:
            zip_obj = Path(tmp_dir).joinpath("temp.zip")
        else:
            zip_obj = io.BytesIO()

        with zipfile.ZipFile(zip_obj, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for folder in tmp_dir_fp.glob("**"):
                zip_file.write(folder, folder.relative_to(tmp_dir_fp))
                for file in folder.iterdir():
                    if file.is_file():
                        zip_file.write(file, file.relative_to(tmp_dir_fp))

            # add weather
            if "add_weather" in request.POST:
                wea_zip_dir = Path("naturwb/data/weather_zips/")
                zip_file.write(wea_zip_dir, "weather_stations")
                for stid in stat_ids:
                    zip_file.write(wea_zip_dir.joinpath(f"{stid}.zip"), 
                                   f"weather_stations/{stid}.zip")
                    
            # create README.txt
            readme = (
                "# README  #\n###########\n" +
                "Diese Datei soll das Ergebnis etwas erläutern und beschreiben.\n\n")
            if "add_input" in request.POST:
                readme += README_PART_INPUT
            if "add_weather" in request.POST:
                readme += (
                    "\n# /weather_stations/\n###################\n" +
                    "Im Ordner \"weather_stations\" befinden sich die einzelnen Stations-Zeitreihen die bei der Simulation für dieses Gebiet genutzt wurden.\n" +
                    "Je Station befindet sich hierin eine ZIP-Datei die nach der DWD-Stations-ID benannt ist. \n" +
                    "Darin befinden sich die 3 Zeitreihen für Niederschlag (N), Temperatur (Ta) und Evapotranspiration(ET)\n")
            if "add_result" in request.POST:
                readme += README_PART_RESULT
            if len(msgs)>0:
                readme += (
                    "\n\n##############\n# !!Achtung!! #\n##############\n"+
                    "Um eine NatUrWB-Referenz für ihr Gebiet zu erhalten, musste an einigen Punkten vom optimalen Weg abgewichen werden.\n"+
                    "Daher sind die Ergebnisse nur unter Berücksichtigung der folgenden Anmerkungen zu verstehen: \n" +
                    "\n".join(new_msgs))
                
            # store README to zip
            zip_file.writestr("README.txt", readme.encode("iso-8859-1"))
        
        # create http response
        file_buffer = File(zip_obj)
        response = StreamingHttpResponse(file_buffer, content_type="application/zip")
        response['Content-Disposition'] = f'attachment; filename="result_{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}.zip"'
        # response['Content-Length'] = file_buffer.tell()
        return response

def home_view(request, *args, **kwargs):
    return render(request, "home.html", context_base)

def method_view(request, *args, **kwargs):
    return render(request, "method.html", context_base)

def impressum_view(request, *args, **kwargs):
    return render(request, "impressum.html", context_base)

def datenschutz_view(request, *args, **kwargs):
    return render(request, "datenschutz.html", context_base)