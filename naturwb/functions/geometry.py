# Here is a collection of functions to use in the app.#
#######################################################

# libraries
import requests
from django.contrib.gis.geos import GEOSGeometry


# functions
def simplify_geom(geom):
    """Simplify the geom object if more than 1000 knots.

    Parameters
    ----------
    geom : GEOSGeometry.Polygon or MultiPolygons
        The input geometry.

    Returns
    -------
    GEOSGeometry.Polygon or MultiPolygons
        Simplified Geometry.
    """    
    if geom.num_coords > 1000:
        geom = geom.simplify(0.0001)

    return geom


def geoencode(name, simplified=True):
    """Make a query to Novatim to get the best Polygon.

    Parameters
    ----------
    name : str
        The name of the german town or city to look for.
    simplified : boolean
        Should the geom get simplified?

    Returns
    -------
    GEOSGeometry.Polygon or MultiPolygons
        Simplified Geometry or total geometry.
    """    
    query_answ = requests.get("https://nominatim.openstreetmap.org/search?q=" + 
                              name + 
                              ",germany&polygon_geojson=1&format=geojson")

    # get the first polygon
    for feature in query_answ.json()["features"]:
        if feature["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
            geom = GEOSGeometry(str(feature["geometry"]))
            break

    if "geom" not in locals():
        return None
    elif simplified:
        geom = simplify_geom(geom)
    
    return geom

def geos_to_latlng(geos_shape):
    '''Calculate latlng for leaflet from geos
    '''
    latlng = []
    for el in geos_shape.coords:
        el_latlng =[]
        if type(el[0][0])==float:
            el = [el]
        for lng, lat in el[0][:-1]:
            el_latlng.append([lat, lng])
        latlng.append(el_latlng)
    return latlng