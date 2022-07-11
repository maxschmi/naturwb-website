# from django.db import models

from django.contrib.gis.db import models
import zlib
import uuid
import datetime
import io
import pickle

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
    # using = "naturwb"

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
    # using = "naturwb"

    class Meta:
        managed = False
        db_table = 'tbl_simulation_polygons'


class LanuJoinModel(models.Model):
    sim_id = models.IntegerField(blank=True, null=True)
    bf_id = models.IntegerField(blank=True, null=True)
    lanu_id = models.ForeignKey('LanuParasModel', models.DO_NOTHING, db_column='lanu_id', blank=True, null=True)  # Field name made lowercase.
    # using = "naturwb"

    class Meta:
        managed = False
        db_table = 'tbl_lanu_join'
        unique_together = (('sim_id', 'bf_id', 'lanu_id'),)


class LanuParasModel(models.Model):
    lanu_id = models.IntegerField(db_column='lanu_id', primary_key=True)  # Field name made lowercase.
    baeume = models.IntegerField(blank=True, null=True)  # Field name made lowercase.
    versiegelung = models.IntegerField(db_column='versiegelung', blank=True, null=True)  # Field name made lowercase.
    lanu_code = models.IntegerField(blank=True, null=True)
    mpd_v = models.IntegerField(blank=True, null=True)
    mpl_v = models.IntegerField(blank=True, null=True)
    mpd_h = models.IntegerField(blank=True, null=True)
    # using = "naturwb"

    class Meta:
        managed = False
        db_table = 'tbl_lanu_paras'


class SavedResults(models.Model):
    urban_shp = models.MultiPolygonField(srid=25832, blank=True, null=True)
    timestamp = models.DateTimeField(blank=False, null=False, primary_key=True)
    n = models.DecimalField(max_digits=23, decimal_places=20, blank=True, null=True)  # Field name made lowercase.
    et = models.DecimalField(max_digits=23, decimal_places=20, blank=True, null=True)
    runoff = models.DecimalField(max_digits=23, decimal_places=20, blank=True, null=True)
    gwnb = models.DecimalField(max_digits=23, decimal_places=20, blank=True, null=True)
    kapA = models.DecimalField(max_digits=23, decimal_places=20,db_column="kap.A.", blank=True, null=True)
    lanu_1 = models.DecimalField(blank=True, null=True,max_digits=23, decimal_places=20)
    lanu_2 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_3 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_4 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_5 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_6 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_7 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_8 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_9 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_10 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_11 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_12 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    lanu_13 = models.DecimalField(blank=True, null=True, max_digits=23, decimal_places=20)
    centroid = models.GeometryField(srid=25832, blank=True, null=True)
    # using = "naturwb"

    class Meta:
        managed = False
        db_table = 'naturwb_results_saved'


class CacheManager(models.Manager):
    def create_cache(self, results_genid, messages):
        # delete older cached values
        self.filter(
                timestamp__lte=datetime.datetime.now(datetime.timezone.utc)\
                    -datetime.timedelta(minutes=20)
            ).delete()

        # save new cached value
        bio = io.BytesIO()
        pickle.dump(results_genid, bio)
        new_cache = self.create(
            uuid=uuid.uuid4(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            results_genid=zlib.compress(bio.getbuffer().tobytes()), 
            messages=zlib.compress(str(messages).encode())
            )
        return new_cache

    def get_cache(self, uuid):
        cache = self.get(uuid=uuid)
        results_genid = pickle.loads(zlib.decompress(cache.results_genid))
        messages = zlib.decompress(cache.messages).decode()\
            .replace("[", "").replace("]", "")[1:-1].split("', '")

        return results_genid, messages
        
        
class CachedResults(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    timestamp = models.DateTimeField(blank=False, null=False, primary_key=False)
    results_genid = models.BinaryField(max_length=1800000, null=True, blank=True)
    messages = models.BinaryField(max_length=5000,blank=True, null=True)

    objects = CacheManager()
    class Meta:
        managed = True
        db_table = 'naturwb_results_cached'

class NaturwbSettings(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, primary_key=True)  # Field name made lowercase.
    value = models.BooleanField(blank=False, null=False)  # Field name made lowercase.
    # using = "django"

    class Meta:
        managed=False
        db_table = 'naturwb_settings'