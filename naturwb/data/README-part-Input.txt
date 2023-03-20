# /input/
#########
In diesem Ornder liegen die Eingangsparameter.

# /input/Modellgebiete.shp
##########################
Eine Shape-Datei der Geometrie aller Modellgebiete. Diese Datei gibt nur den räumlichen Bezug der Modellgebiete wieder.
Die Projektion der Datei ist dabei ETRS89 / UTM Zone 32N (EPSG:25832).

Spalten:
---------
 - sim_id:      Die ID des Modellgebiets. 
                Kann zum Verknüpfen mit den Simulations-Parametern (siehe Simulations-Parameter.csv) genutzt werden.

# /input/Simulations-Parameter.csv
##################################
Dies sind die Eingangsparameter aller Modellierungen die für diese Gebiet

Spalten:
---------
 - sim_id   :   Die ID des Modellgebiets
                Kann zur Verknüpfung mit den Modellgebieten (Modellgebiete.shp) genutzt werden.
 - gen_id   :	ID Der Bodengesellschaft in der BÜK250. Verknüpfung zur Sachdatenbank.
 - lanu_id  :   ID der genutzten Landnutzung.
 - bf_id    :   ID des Bodenprofils in der BÜK Sachdatenbank.
 - stat_id  :   die DWD-Stations ID der genutzten Wetter Station
 - f_n_wihj :   Regionalisierungs-Faktor für den Niederschlag im Winterhalbjahr (April-September) in %
 - f_n_sohj :   Regionalisierungs-Faktor für den Niederschlag im Sommerhalbjahr (Oktober-März) in %
 - f_et     :   Regionalisierungs-Faktor für die Evapotranspiration in %
 - f_t      :   Regionalisierungs-Zuschlag für die Temperatur in °C
 - slope    :   Das mittlere Gefälle des Polygons in %, bestimmt aus einem DGM25 von Copernicus
 - baeume   :   Ein RoGeR-Parameter der eine zusätzliche Verdunstungsebene der Bäume einführt
 - lanu_code:   Der RoGeR Landnutzungscode
 - mpd_v    :   Dichte der vertikal ausgerichteten Makroporen [1/m²]
 - mpl_v    :   Länge der vertikal ausgerichteten Makroporen [cm]
 - mpd_h    :   Dichte der hangparallel ausgerichteten Makroporen [1/m²]
 - muldenspeicher: Parameter der einen zusätzlichen Muldenspeicher definert in mm (vor allem für Torf-Böden)
 - grund_cm :   Die Bodentiefe in cm
 - mgw      :   mitlerer Grundwasserflurabstand in cm
 - lk       :   Anteil der Luftkapazität am Bodenvolumen [%]
 - nfk      :   Anteil der nutzbaren Feldkapazität am Bodenvolumen [%]
 - pwp      :   permanenter Welkepunkt bestimmt in mm
 - ks       :   Mittlere gesättigte hydraulische Leitfähigkeit [mm/h]
 - ks_min   :   Geringste Leitfähigkeit im Profil [mm/h]
                Wenn Grundwasser im Profil ansteht -> ks_min=0, da hierbei schnelle Abflussreaktionen angenommen werden und daher keine GWNB zugelassen wird.
 - bf_anteil:   Flächenanteil des Bodenprofils an der Bodengesellschaft in %
 - theta    :   Anfangsbodenfeuchte in %

