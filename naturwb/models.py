# from django.db import models

# Create your models here.
from django.contrib.gis.db import models

# Create your models here.

# code erstellt mit >python manage.py inspectdb > models.py

class LookupModel(models.Model):
    gid = models.AutoField(primary_key=True)
    sim_id = models.ForeignKey('SimulationModel', models.DO_NOTHING, blank=True, null=True, db_column="sim_id")
    gen_id = models.IntegerField(blank=True, null=True)
    nat_id = models.IntegerField(blank=True, null=True)
    lanu_id = models.IntegerField(blank=True, null=True)
    clc_code = models.IntegerField(blank=True, null=True)
    shape_area = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    geom = models.MultiPolygonField(srid=25832, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_lookup_polygons'


class SimulationModel(models.Model):
    geom = models.MultiPolygonField(srid=25832, blank=True, null=True)
    sim_id = models.IntegerField(primary_key=True)
    gen_id = models.IntegerField(blank=True, null=True)
    tkle_nr = models.IntegerField(blank=True, null=True)
    nrkart = models.IntegerField(blank=True, null=True)
    sym_nr = models.IntegerField(blank=True, null=True)
    buek_flag = models.SmallIntegerField(blank=True, null=True)
    stat_id = models.IntegerField(blank=True, null=True)
    wea_flag = models.SmallIntegerField(blank=True, null=True)
    wea_dist = models.IntegerField(blank=True, null=True)
    wea_n_wihj = models.DecimalField(db_column='wea_n-wihj', max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    wea_n_sohj = models.DecimalField(db_column='wea_n-sohj', max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    wea_et = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    wea_t = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    sl_mean = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    sl_flag = models.SmallIntegerField(blank=True, null=True)
    sl_dist = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    shape_area = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    lanu_key = models.IntegerField(blank=True, null=True)
    lanu_flag = models.SmallIntegerField(blank=True, null=True)
    sl_std = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    sl_count = models.IntegerField(blank=True, null=True)
    wea_t_std = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    wea_n_wihj_std = models.DecimalField(db_column='wea_n-wihj_std', max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    wea_n_sohj_std = models.DecimalField(db_column='wea_n-sohj_std', max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    wea_et_std = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    wea_count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_simulation_polygons'


class LanuJoinModel(models.Model):
    sim_id = models.IntegerField(blank=True, null=True)
    bf_id = models.IntegerField(blank=True, null=True)
    lanu_id = models.ForeignKey('LanuParasModel', models.DO_NOTHING, db_column='lanu_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tbl_lanu_join'


class LanuParasModel(models.Model):
    lanu_id = models.IntegerField(db_column='lanu_id', primary_key=True)  # Field name made lowercase.
    baeume = models.IntegerField(blank=True, null=True)  # Field name made lowercase.
    versiegelung = models.IntegerField(db_column='versiegelung', blank=True, null=True)  # Field name made lowercase.
    lanu_code = models.IntegerField(blank=True, null=True)
    mpd_v = models.IntegerField(blank=True, null=True)
    mpl_v = models.IntegerField(blank=True, null=True)
    mpd_h = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_lanu_paras'

class SavedResults(models.Model):
    urban_shp = models.MultiPolygonField(srid=25832, blank=True, null=True)
    timestamp = models.DateTimeField(blank=False, null=False, primary_key=True)
    n = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field name made lowercase.
    et = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    q_oa_za = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    q_gwnb = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    kapA = models.DecimalField(max_digits=65535, decimal_places=65535,db_column="kap.A.", blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'naturwb_results_saved'

class NaturwbSettings(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, primary_key=True)  # Field name made lowercase.
    value = models.BooleanField(blank=False, null=False)  # Field name made lowercase.

    class Meta:
        db_table = 'naturwb_settings'