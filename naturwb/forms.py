from django import forms
from django.contrib.gis import forms as gforms
from leaflet.forms.fields import MultiPolygonField
from leaflet.forms.widgets import LeafletWidget


# only if saved to database
# class EnterPolygonForm(forms.ModelForm):
#     class Meta:
#         model = SearchPolygon
#         fields = [
#             'geom',
#             'name'
#             ]

class SearchPolygonQuery(forms.Form):
    search_query = forms.CharField(required=False, label="Suche nach einer Stadt ")

            
class EnterPolygonForm(gforms.Form):
    geom = MultiPolygonField(
        required=True, initial=None,
        widget=LeafletWidget(
            attrs={
                'map_width': "100%", 
                'map_height': "550px",
                'settings_overrides': {
                    #'DEFAULT_CENTER': (51.351, 10.459),
                    #'DEFAULT_ZOOM': 6,
                    'SPATIAL_EXTENT': (5.2,47.0,15.5,55.2)
                    }
                }),
        label=""
        )
    # standard geodjango library, does work, but no possibility to delete points
    # geom2 = gforms.PolygonField(required=True, label="", initial=None,
    #     widget= gforms.OSMWidget(attrs={
    #         'map_width': "100%", 
    #         'map_height': 800,
    #         'default_lat': 51.351,
    #         'default_lon': 10.459,
    #         'default_zoom': 6
    #         }))
