from django.contrib import admin

from .models import LookupModel, SimulationModel, NaturwbSettings

# Register your models here.
admin.site.register(LookupModel)
admin.site.register(SimulationModel)
admin.site.register(NaturwbSettings)