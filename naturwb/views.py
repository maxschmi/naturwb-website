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
from .models import NaturwbSettings
from .functions.naturwb_db import results_to_db

# Create your views here.
def get_ref_view(request, *args, **kwargs):
    initial_data = {"geom": None}
    context = {
        "error_geoencoding": False,
        'error_nogeom': False
    }

    # check if it was redirected because of missing geom
    if "error_nogeom" in request.GET:
        context.update({"error_nogeom": bool(request.GET["error_nogeom"])})

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

def result_view(request, *args, **kwargs):
    # check for empty geom
    if 'geom' not in request.POST:
        return redirect("/get_ref/?error_nogeom=True")

    urban_geom = GEOSGeometry(request.POST['geom'])

    # make naturwb query
    try:
        nwbquery = NWBQuery(
            urban_shp=wkt_loads(urban_geom.wkt), 
            db_engine=get_engine(),
            do_plots=False)

        context = {
            "messages": nwbquery.msgs,
            "success": True,
            "plot_lookup_clip_plotly": nwbquery.plot_web("lookup_clip_plotly"),
            # "plot_pie": nwbquery.plot_web("pie", figsize=(7, 7)),
            "plot_pie_plotly": nwbquery.plot_web("pie_plotly"),
            "plot_sankey": nwbquery.plot_web("sankey", figsize=(17,17)),
            "plot_ternary": nwbquery.plot_web("ternary", width=1000, do_size=True),
            "plot_pie_lanu": nwbquery.plot_web("pie_landuse"),
            "et_rel": "{:.0%}".format(nwbquery.naturwb_ref["et_rel"]).replace('%', ' %'),
            "a_rel": "{:.0%}".format(nwbquery.naturwb_ref["runoff_rel"]).replace('%', ' %'),
            "tp_rel": "{:.0%}".format(nwbquery.naturwb_ref["tp_rel"]).replace('%', ' %'),
            "n_nres": nwbquery.lookup_clip.index.get_level_values("nat_id").unique()
            }
        
        # save the results to the database
        try:
            if NaturwbSettings.objects.get(pk="save_to_db").value:
                results_to_db(nwbquery)
        except NaturwbSettings.DoesNotExist:
            print("No setting parameter 'save_to_db' in the naturwb_settings table in the database")

    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        context = {
            "success": False,
        }

    return render(request, "result.html", context)

def home_view(request, *args, **kwargs):
    return render(request, "home.html", {})

def method_view(request, *args, **kwargs):
    return render(request, "method.html", {})

def impressum_view(request, *args, **kwargs):
    return render(request, "impressum.html", {})