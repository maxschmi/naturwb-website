
def results_to_db(naturwb_query):
    """Save a naturwb.Query object to the database.

    Parameters
    ----------
    naturwb_query : naturwb.Query
        The Query object of the naturwb request.
    """
    # get landuse distribution
    lanus = naturwb_query.coef_all.prod(axis=1
        ).groupby("lanu_id").sum(
        ).reindex(range(0, 14)).drop(1
        ).fillna(0)

    # insert to database
    sql_insert = (
        'INSERT INTO naturwb_results_saved ' +
        '(urban_shp, centroid, n, et, runoff, gwnb, "kap.A.", {lanu_cols})' +
        "VALUES (ST_GeomFromText('{urban_shp}', 4326), " +
        "ST_Centroid(ST_GeomFromText('{urban_shp}', 4326)), "
        "{n}, {et}, {runoff}, {tp}, {kap}, {lanu_values});" +
        "DELETE FROM naturwb_results_saved " +
        "WHERE timestamp < (now() - INTERVAL '2 HOUR') ;"
    ).format(
        urban_shp=naturwb_query.urban_shp_wgs.iloc[0].to_wkt(),
        lanu_cols="lanu_" + ", lanu_".join(lanus.index.astype(str)),
        lanu_values=", ".join(lanus.astype(str).to_list()),
        **naturwb_query.naturwb_ref.rename({"kap.A.": "kap"}).to_dict()
        )
    with naturwb_query.db_engine.connect() as conn:
        conn.execute(sql_insert)

    