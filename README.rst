geoserver-restconfig
====================

.. image:: https://travis-ci.org/geosolutions-it/geoserver-restconfig.svg?branch=master
    :target: https://travis-ci.org/geosolutions-it/geoserver-restconfig

``geoserver-restconfig`` is a python library for manipulating a GeoServer instance via the GeoServer RESTConfig API. 

**Note:** geoserver-restconfig is a fork of the old https://travis-ci.org/boundlessgeo/gsconfig

The project is distributed under a `MIT License <LICENSE.txt>`_ .

Installing
==========

.. code-block:: shell

    pip install geoserver-restconfig

For developers:

.. code-block:: shell

    git clone git@github.com:geosolutions-it/geoserver-restconfig.git
    cd geoserver-restconfig
    python setup.py develop

Getting Help
============
There is a brief manual at http://geonode.org/geoserver-restconfig/ .
If you have questions, please ask them on the GeoServer Users mailing list: http://geoserver.org/ .

Please use the Github project at http://github.com/geosolutions-it/geoserver-restconfig for any bug reports (and pull requests are welcome, but please include tests where possible.)

Sample Layer Creation Code
==========================

.. code-block:: python

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    topp = cat.get_workspace("topp")
    shapefile_plus_sidecars = shapefile_and_friends("states")
    # shapefile_and_friends should look on the filesystem to find a shapefile
    # and related files based on the base path passed in
    #
    # shapefile_plus_sidecars == {
    #    'shp': 'states.shp',
    #    'shx': 'states.shx',
    #    'prj': 'states.prj',
    #    'dbf': 'states.dbf'
    # }
    
    # 'data' is required (there may be a 'schema' alternative later, for creating empty featuretypes)
    # 'workspace' is optional (GeoServer's default workspace is used by... default)
    # 'name' is required
    ft = cat.create_featurestore(name, workspace=topp, data=shapefile_plus_sidecars)

Running Tests
=============

Since the entire purpose of this module is to interact with GeoServer, the test suite is mostly composed of `integration tests <http://en.wikipedia.org/wiki/Integration_testing>`_.  
These tests necessarily rely on a running copy of GeoServer, and expect that this GeoServer instance will be using the default data directory that is included with GeoServer.
This data is also included in the GeoServer source repository as ``/data/release/``.
In addition, it is expected that there will be a postgres database available at ``postgres:password@localhost:5432/db``.
You can test connecting to this database with the ``psql`` command line client by running ``$ psql -d db -Upostgres -h localhost -p 5432`` (you will be prompted interactively for the password.)

To override the assumed database connection parameters, the following environment variables are supported:

- DATABASE
- DBUSER
- DBPASS

If present, psycopg will be used to verify the database connection prior to running the tests.

If provided, the following environment variables will be used to reset the data directory:

GEOSERVER_HOME
    Location of git repository to read the clean data from. If only this option is provided
    `git clean` will be used to reset the data.
GEOSERVER_DATA_DIR
    Optional location of the data dir geoserver will be running with. If provided, `rsync`
    will be used to reset the data.
GS_VERSION
    Optional environment variable allowing the catalog test cases to automatically download
    and start a vanilla GeoServer WAR form the web.
    Be sure that there are no running services on HTTP port 8080.

Here are the commands that I use to reset before running the geoserver-restconfig tests:

.. code-block:: shell

    $ cd ~/geoserver/src/web/app/
    $ PGUSER=postgres dropdb db
    $ PGUSER=postgres createdb db -T template_postgis
    $ git clean -dxff -- ../../../data/release/
    $ git checkout -f
    $ MAVEN_OPTS="-XX:PermSize=128M -Xmx1024M" \
    GEOSERVER_DATA_DIR=../../../data/release \
    mvn jetty:run

At this point, GeoServer will be running foregrounded, but it will take a few seconds to actually begin listening for http requests.
You can stop it with ``CTRL-C`` (but don't do that until you've run the tests!)
You can run the geoserver-restconfig tests with the following command:

.. code-block:: shell

    $ python setup.py test

Instead of restarting GeoServer after each run to reset the data, the following should allow re-running the tests:

.. code-block:: shell

    $ git clean -dxff -- ../../../data/release/
    $ curl -XPOST --user admin:geoserver http://localhost:8080/geoserver/rest/reload

More Examples - Updated for GeoServer 2.4+
==========================================

Loading the GeoServer ``catalog`` using ``geoserver-restconfig`` is quite easy. The example below allows you to connect to GeoServer by specifying custom credentials.

.. code-block:: python

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest/", "admin", "geoserver")


The code below allows you to filter which workspaces to return

.. code-block:: python

    cat.get_workspaces(names="geosolutions,topp")

You may also specify the workspaces as a proper list

.. code-block:: python

    cat.get_workspaces(names=["geosolutions", "topp"])

The code below allows you to filter which stores to return

.. code-block:: python

    cat.get_stores(names=["sf", "mosaic"], workspaces=["nurc", "topp", "sf"])

``names`` and ``workspaces`` can either be a comma delimited string or a list.
This is true for the ``get_workspaces``, ``get_stores``, ``get_resources``, ``get_layergroups`` and ``get_styles``.  

The code below allows you to create a FeatureType from a Shapefile

.. code-block:: python

    geosolutions = cat.get_workspace("geosolutions")
    import geoserver.util
    shapefile_plus_sidecars = geoserver.util.shapefile_and_friends("C:/work/geoserver-restconfig/test/data/states")
    # shapefile_and_friends should look on the filesystem to find a shapefile
    # and related files based on the base path passed in
    #
    # shapefile_plus_sidecars == {
    #    'shp': 'states.shp',
    #    'shx': 'states.shx',
    #    'prj': 'states.prj',
    #    'dbf': 'states.dbf'
    # }
    # 'data' is required (there may be a 'schema' alternative later, for creating empty featuretypes)
    # 'workspace' is optional (GeoServer's default workspace is used by... default)
    # 'name' is required
    ft = cat.create_featurestore("test", shapefile_plus_sidecars, geosolutions)

It is possible to create JDBC Virtual Layers too. The code below allow to create a new SQL View called ``my_jdbc_vt_test`` defined by a custom ``sql``.

.. code-block:: python

    from geoserver.catalog import Catalog
    from geoserver.support import JDBCVirtualTable, JDBCVirtualTableGeometry, JDBCVirtualTableParam

    cat = Catalog('http://localhost:8080/geoserver/rest/', 'admin', '****')
    store = cat.get_store('postgis-geoserver')
    geom = JDBCVirtualTableGeometry('newgeom','LineString','4326')
    ft_name = 'my_jdbc_vt_test'
    epsg_code = 'EPSG:4326'
    sql = 'select ST_MakeLine(wkb_geometry ORDER BY waypoint) As newgeom, assetid, runtime from waypoints group by assetid,runtime'
    keyColumn = None
    parameters = None

    jdbc_vt = JDBCVirtualTable(ft_name, sql, 'false', geom, keyColumn, parameters)
    ft = cat.publish_featuretype(ft_name, store, epsg_code, jdbc_virtual_table=jdbc_vt)

The next example shows how to create a ``PostGIS JNDI`` datastore (connection_parameters come from another example. 
Settings might be different depending on your needs):

.. code-block:: python

    cat = Catalog('http://localhost:8080/geoserver/rest/', 'admin', '****')
    datastore_name = 'sample_jndi_store'
    
    dstore = cat.get_store(name = datastore_name, workspace=metadata[WS])
    # Let's check that the store doesn't already exist
    if ds_store is None:
        ws = 'my_workspace'
        dstore = cat.create_datastore(workspace=ws, name = datastore_name)
        connection_parameters= {
            'type': 'PostGIS (JNDI)', 
            'schema': 'my_schema', 
            'Estimated extends': 'true', 
            'fetch size': '1000', 
            'encode functions': 'true', 
            'Expose primary keys': 'false', 
            'Support on the fly geometry simplification': 'true', 
            'Batch insert size': '1', 
            'preparedStatements': 'false', 
            'Support on the fly geometry simplification, preserving topology': 'true', 
            'jndiReferenceName': 'java:comp/env/jdbc/geodb', 
            'dbtype': 'postgis', 
            'namespace': 'my_workspace', 
            'Loose bbox': 'true'
        }
        dstore.connection_parameters.update(connection_parameters)
        cat.save(dstore)
        assert dstore.enabled
        return dstore

This example shows how to easily update a ``layer`` property. The same approach may be used with every ``catalog`` resource

.. code-block:: python

    ne_shaded = cat.get_layer("ne_shaded")
    ne_shaded.enabled=True
    cat.save(ne_shaded)
    cat.reload()

Deleting a ``store`` from the ``catalog`` requires to purge all the associated ``layers`` first. This can be done by doing something like this:

.. code-block:: python

    st = cat.get_store("ne_shaded")
    cat.delete(ne_shaded)
    cat.reload()
    cat.delete(st)
    cat.reload()

Alternatively, you can delete a ``store`` as well as all the underlying ``layers`` in one shot, like this:

.. code-block:: python

    store = cat.get_store("ne_shaded")
    cat.delete(store, purge=True, recurse=True)

There are some functionalities allowing to manage the ``ImageMosaic`` coverages. It is possible to create new ImageMosaics, add granules to them,
and also read the coverages metadata, modify the mosaic ``Dimensions`` and finally query the mosaic ``granules`` and list their properties.

The geoserver-restconfig methods map the `REST APIs for ImageMosaic <http://docs.geoserver.org/stable/en/user/rest/examples/curl.html#uploading-and-modifying-a-image-mosaic>`_

In order to create a new ImageMosaic layer, you can prepare a zip file containing the properties files for the mosaic configuration. Refer to the GeoTools ImageMosaic Plugin guide
in order to get details on the mosaic configuration. The package contains an already configured zip file with two granules.
You need to update or remove the ``datastore.properties`` file before creating the mosaic otherwise you will get an exception.

.. code-block:: python

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8180/geoserver/rest")
    cat.create_imagemosaic("NOAAWW3_NCOMultiGrid_WIND_test", "NOAAWW3_NCOMultiGrid_WIND_test.zip")

By defualt the ``cat.create_imagemosaic`` tries to configure the layer too. If you want to create the store only, you can specify the following parameter

.. code-block:: python

    cat.create_imagemosaic("NOAAWW3_NCOMultiGrid_WIND_test", "NOAAWW3_NCOMultiGrid_WIND_test.zip", "none")

In order to retrieve from the catalog the ImageMosaic coverage store you can do this

.. code-block:: python

    store = cat.get_store("NOAAWW3_NCOMultiGrid_WIND_test")

It is possible to add more granules to the mosaic at runtime.
With the following method you can add granules already present on the machine local path.

.. code-block:: python

    cat.add_granule("file://D:/Work/apache-tomcat-6.0.16/instances/data/data/MetOc/NOAAWW3/20131001/WIND/NOAAWW3_NCOMultiGrid__WIND_000_20131001T000000.tif", store.name, store.workspace.name)

The method below allows to send granules remotely via POST to the ImageMosaic.
The granules will be uploaded and stored on the ImageMosaic index folder.

.. code-block:: python

    cat.add_granule("NOAAWW3_NCOMultiGrid__WIND_000_20131002T000000.zip", store.name, store.workspace.name)

To delete an ImageMosaic store, you can follow the standard approach, by deleting the layers first.
*ATTENTION*: at this time you need to manually cleanup the data dir from the mosaic granules and, in case you used a DB datastore, you must also drop the mosaic tables.

.. code-block:: python

    layer = cat.get_layer("NOAAWW3_NCOMultiGrid_WIND_test")
    cat.delete(layer)
    cat.reload()
    cat.delete(store)
    cat.reload()

By default the ImageMosaic layer has not the coverage dimensions configured. It is possible using the coverage metadata to update and manage the coverage dimensions.
*ATTENTION*: notice that the ``presentation`` parameters accepts only one among the following values {'LIST', 'DISCRETE_INTERVAL', 'CONTINUOUS_INTERVAL'}

.. code-block:: python

    from geoserver.support import DimensionInfo
    timeInfo = DimensionInfo("time", "true", "LIST", None, "ISO8601", None)
    coverage.metadata = ({'dirName':'NOAAWW3_NCOMultiGrid_WIND_test_NOAAWW3_NCOMultiGrid_WIND_test', 'time': timeInfo})
    cat.save(coverage)

Once the ImageMosaic has been configured, it is possible to read the coverages along with their granule schema and granule info.

.. code-block:: python

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8180/geoserver/rest")
    store = cat.get_store("NOAAWW3_NCOMultiGrid_WIND_test")
    coverages = cat.mosaic_coverages(store)
    schema = cat.mosaic_coverage_schema(coverages['coverages']['coverage'][0]['name'], store)
    granules = cat.list_granules(coverages['coverages']['coverage'][0]['name'], store)

The granules details can be easily read by doing something like this:

.. code-block:: python

    granules['crs']['properties']['name']
    granules['features']
    granules['features'][0]['properties']['time']
    granules['features'][0]['properties']['location']
    granules['features'][0]['properties']['run']

When the mosaic grows up and starts having a huge set of granules, you may need to filter the granules query through a CQL filter on the coverage schema attributes.

.. code-block:: python

    granules = cat.list_granules(coverages['coverages']['coverage'][0]['name'], store, "time >= '2013-10-01T03:00:00.000Z'")
    granules = cat.list_granules(coverages['coverages']['coverage'][0]['name'], store, "time >= '2013-10-01T03:00:00.000Z' AND run = 0")
    granules = cat.list_granules(coverages['coverages']['coverage'][0]['name'], store, "location LIKE '%20131002T000000.tif'")


Creating layergroups
====================
A layergroup can be setup by providing a list of layers and the related styles to the catalog. 
In the next example, a layergroup with 3 layers and their associated styles get created.

.. code-block:: python

    workspace = 'my_workspace'
    layers_in_group = ['my_workspace:layer_1', 'my_workspace:layer_2', 'my_workspace:layer_3']
    styles = ['my_workspace:style_1', 'my_workspace:style_2', 'my_workspace:style_3']
    layergroup_name = 'test_layergroup'
    
    layergroup = cat.create_layergroup(layergroup_name, layers_in_group, styles, workspace)
    # Note that if no bounds are provided, GeoServer will automatically compute the layergroup bounding box
    cat.save(layergroup)

Nesting layergroups
^^^^^^^^^^^^^^^^^^^
A Layergroup can internally contain layergroups too. In the next example an additional layergroup containing
a ``layer_4`` simple layer plus the previously created ``test_layegroup`` will be created. 
This time, layer attributes need to be specified. 

.. code-block:: python

    workspace = 'my_workspace'
    
    layers = []
    layers.append({'name':'my_workspace:layer_4', 'attributes':{'type':'layer'}})
    layers.append({'name':'my_workspace:test_layergroup', 'attributes':{'type':'layerGroup'}})

    # Not specifying the style for the nested layergroup
    styles = []
    styles.append('my_workspace:style_4')
    styles.append(None)
    layergroup_name = 'outer_layergroup'
    
    outer_layergroup = cat.create_layergroup(layergroup_name, layers, styles, workspace)
    cat.save(outer_layergroup)    



