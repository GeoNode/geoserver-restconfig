# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright 2019, GeoSolutions Sas.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE.txt file in the root directory of this source tree.
#
#########################################################################
import os
import subprocess
import atexit
import signal
import time
import re
import unittest
import gisdata
from geoserver.catalog import Catalog
from geoserver.catalog import ConflictingDataError
from geoserver.catalog import UploadError
from geoserver.catalog import FailedRequestError
from geoserver.support import ResourceInfo, build_url
from geoserver.support import DimensionInfo
from geoserver.support import JDBCVirtualTable
from geoserver.support import JDBCVirtualTableGeometry
from geoserver.layergroup import LayerGroup
from geoserver.util import shapefile_and_friends
from .utils import DBPARAMS
from .utils import GSPARAMS

try:
    import psycopg2
    # only used for connection sanity if present
    conn = psycopg2.connect(('dbname=%(database)s user=%(user)s password=%(passwd)s'
                             ' port=%(port)s host=%(host)s'
                             ) % DBPARAMS)
except ImportError:
    pass

# support resetting geoserver datadir
if GSPARAMS['GEOSERVER_HOME']:
    dest = GSPARAMS['DATA_DIR']
    data = os.path.join(GSPARAMS['GEOSERVER_HOME'], 'data/release', '')
    if dest:
        os.system(f"rsync -v -a --delete {data} {os.path.join(dest, '')}")
    else:
        os.system(f'git clean -dxf -- {data}')
    os.system(f"curl -XPOST --user '{GSPARAMS['GSUSER']}':'{GSPARAMS['GSPASSWORD']}' '{GSPARAMS['GSURL']}/reload'")

# set GS_VERSION to None in order to skip the GeoServer setup
global child_pid
child_pid = None
# use "master" in order to test against the latest GeoServer version
if GSPARAMS['GS_VERSION']:
    subprocess.Popen(["rm", "-rf", f"{GSPARAMS['GS_BASE_DIR']}/gs"]).communicate()
    subprocess.Popen(["mkdir", f"{GSPARAMS['GS_BASE_DIR']}/gs"]).communicate()
    subprocess.Popen(
        [
            "wget",
            "http://central.maven.org/maven2/org/eclipse/jetty/jetty-runner/9.4.5.v20170502/jetty-runner-9.4.5.v20170502.jar",
            "-P", f"{GSPARAMS['GS_BASE_DIR']}/gs"
        ]
    ).communicate()

    subprocess.Popen(
        [
            "wget",
            f"https://build.geoserver.org/geoserver/{GSPARAMS['GS_VERSION']}/geoserver-{GSPARAMS['GS_VERSION']}-latest-war.zip",
            "-P", f"{GSPARAMS['GS_BASE_DIR']}/gs"
        ]
    ).communicate()

    subprocess.Popen(
        [
            "unzip",
            "-o",
            "-d",
            f"{GSPARAMS['GS_BASE_DIR']}/gs",
            f"{GSPARAMS['GS_BASE_DIR']}/gs/geoserver-{GSPARAMS['GS_VERSION']}-latest-war.zip"
        ]
    ).communicate()

    FNULL = open(os.devnull, 'w')

    match = re.compile(r'[^\d.]+')
    geoserver_short_version = match.sub('', GSPARAMS['GS_VERSION']).strip('.')
    if geoserver_short_version >= "2.15" or GSPARAMS['GS_VERSION'].lower() == 'master':
        java_executable = "/usr/local/lib/jvm/openjdk11/bin/java"
    else:
        java_executable = "/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java"

    print(f"geoserver_short_version: {geoserver_short_version}")
    print(f"java_executable: {java_executable}")
    proc = subprocess.Popen(
        [
            java_executable,
            "-Xmx1024m",
            "-Dorg.eclipse.jetty.server.webapp.parentLoaderPriority=true",
            "-jar", f"{GSPARAMS['GS_BASE_DIR']}/gs/jetty-runner-9.4.5.v20170502.jar",
            "--path", "/geoserver", f"{GSPARAMS['GS_BASE_DIR']}/gs/geoserver.war"
        ],
        stdout=FNULL, stderr=subprocess.STDOUT
    )
    child_pid = proc.pid
    print("Sleep (90)...")
    time.sleep(40)


def kill_child():
    if child_pid is None:
        pass
    else:
        subprocess.Popen(["rm", "-Rf", f"{GSPARAMS['GS_BASE_DIR']}/gs"]).communicate()
        print(f"KILLING PROCESS: {str(child_pid)}")
        os.kill(child_pid, signal.SIGTERM)


atexit.register(kill_child)


def drop_table(table):
    def outer(func):
        def inner(*args):
            try:
                func(*args)
            finally:
                try:
                    if conn:
                        conn.cursor().execute(f'DROP TABLE {table}')
                except Exception as e:
                    print('ERROR dropping table')
                    print(e)
        return inner
    return outer


class NonCatalogTests(unittest.TestCase):

    def testDimensionInfo(self):
        inf = DimensionInfo(* (None,) * 6)
        # make sure these work with no resolution set
        self.assertTrue(inf.resolution_millis() is None)
        self.assertTrue(inf.resolution_str() is None)

        def inf(r): return DimensionInfo(None, None, None, r, None, None)

        def assertEqualResolution(spec, millis):
            self.assertEqual(millis, inf(spec).resolution_millis())
            self.assertEqual(spec, inf(millis).resolution_str())

        assertEqualResolution('0.5 seconds', 500)
        assertEqualResolution('7 days', 604800000)
        assertEqualResolution('10 years', 315360000000000)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.gs_version = self.cat.get_short_version()

    def testGSVersion(self):
        version = self.cat.get_version()
        pat = re.compile('\\d\\.\\d+')
        self.assertTrue(pat.match('2.2.x'))
        self.assertTrue(pat.match('2.3.2'))
        self.assertTrue(pat.match('2.3-SNAPSHOT'))
        self.assertTrue(pat.match(version))

    def testWorkspaces(self):
        self.assertEqual(7, len(self.cat.get_workspaces()))
        # marking out test since geoserver default workspace is not consistent
        # self.assertEqual("cite", self.cat.get_default_workspace().name)
        self.assertEqual("topp", self.cat.get_workspaces(names="topp")[-1].name)
        self.assertEqual(2, len(self.cat.get_workspaces(names=['topp', 'sde'])))
        self.assertEqual(2, len(self.cat.get_workspaces(names='topp, sde')))
        self.assertEqual("topp", self.cat.get_workspace("topp").name)
        self.assertIsNone(self.cat.get_workspace("blahblah-"))

    def testStores(self):
        self.assertEqual(0, len(self.cat.get_stores(names="nonexistentstore")))
        topp = self.cat.get_workspaces("topp")[0]
        sf = self.cat.get_workspaces("sf")[0]
        self.assertEqual(9, len(self.cat.get_stores()))
        self.assertEqual(2, len(self.cat.get_stores(workspaces=topp)))
        self.assertEqual(2, len(self.cat.get_stores(workspaces=sf)))
        self.assertEqual(2, len(self.cat.get_stores(workspaces='sf')))
        self.assertEqual(2, len(self.cat.get_stores(names='states_shapefile, sfdem')))
        self.assertEqual(2, len(self.cat.get_stores(names=['states_shapefile', 'sfdem'])))
        self.assertEqual("states_shapefile", self.cat.get_stores(names="states_shapefile", workspaces=topp.name)[0].name)
        self.assertEqual("states_shapefile", self.cat.get_stores(names="states_shapefile")[0].name)
        self.assertEqual("sfdem", self.cat.get_stores(names="sfdem", workspaces=sf.name)[0].name)
        self.assertEqual("sfdem", self.cat.get_store("sfdem", workspace="sf").name)
        self.assertIsNone(self.cat.get_store("blah+blah-"))

    def testResources(self):
        topp = self.cat.get_workspaces("topp")[0]
        sf = self.cat.get_workspaces("sf")[0]
        states = self.cat.get_stores(names="states_shapefile", workspaces=topp.name)[0]
        sfdem = self.cat.get_stores(names="sfdem", workspaces=sf.name)[0]
        self.assertEqual(19, len(self.cat.get_resources()))
        self.assertEqual(2, len(self.cat.get_resources(stores=[states.name, sfdem.name], workspaces=[topp.name, sf.name])))
        self.assertEqual(11, len(self.cat.get_resources(workspaces=[topp.name, sf.name])))

        self.assertEqual("states", self.cat.get_resources(names="states", stores=states.name, workspaces=topp.name)[0].name)
        self.assertEqual("states", self.cat.get_resources(names="states", workspaces=topp.name)[0].name)
        self.assertEqual("states", self.cat.get_resource("states", workspace=topp.name).name)
        self.assertIsNone(self.cat.get_resource("blah+1blah-2"))

        states = self.cat.get_resources(names="states", workspaces=topp.name)[0]

        fields = [
            states.title,
            states.abstract,
            states.native_bbox,
            states.latlon_bbox,
            states.projection,
            states.projection_policy
        ]

        self.assertFalse(None in fields, str(fields))
        self.assertFalse(len(states.keywords) == 0)
        self.assertFalse(len(states.attributes) == 0)
        self.assertTrue(states.enabled)

        self.assertEqual("sfdem", self.cat.get_resources(names="sfdem", stores=sfdem.name, workspaces=sf.name)[0].name)
        self.assertEqual("sfdem", self.cat.get_resources(names="sfdem", workspaces=sf.name)[0].name)

    def testResourcesUpdate(self):
        res_dest = self.cat.get_resources()
        count = 0

        for rd in res_dest:
            # only wms layers
            if rd.resource_type != "wmsLayer":
                continue
            # looking for same name
            ro = self.cat.get_resources(names=rd.name)

            if ro is not None:
                rd.title = ro.title
                rd.abstract = ro.abstract
                rd.keywords = ro.keywords
                rd.projection = ro.projection
                rd.native_bbox = ro.native_bbox
                rd.latlon_bbox = ro.latlon_bbox
                rd.projection_policy = ro.projection_policy
                rd.enabled = ro.enabled
                rd.advertised = ro.advertised
                rd.metadata_links = ro.metadata_links or None

                self.cat.save(rd)
                self.cat.reload()
                count += 1

    def testLayers(self):
        if self.gs_version >= "2.13":
            expected = set([
                'sf:roads',
                'sf:sfdem',
                'nurc:mosaic',
                'tiger:giant_polygon',
                'sf:bugsites',
                'topp:states',
                'sf:streams',
                'tiger:poly_landmarks',
                'tiger:poi',
                'topp:tasmania_water_bodies',
                'tiger:tiger_roads',
                'topp:tasmania_roads',
                'nurc:Pk50095',
                'topp:tasmania_cities',
                'nurc:Img_Sample',
                'sf:restricted',
                'nurc:Arc_Sample',
                'sf:archsites',
                'topp:tasmania_state_boundaries'
            ])
        else:
            expected = set([
                "Arc_Sample",
                "Pk50095",
                "Img_Sample",
                "mosaic",
                "sfdem",
                "bugsites",
                "restricted",
                "streams",
                "archsites",
                "roads",
                "tasmania_roads",
                "tasmania_water_bodies",
                "tasmania_state_boundaries",
                "tasmania_cities",
                "states",
                "poly_landmarks",
                "tiger_roads",
                "poi",
                "giant_polygon"
            ])

        actual = set(l.name for l in self.cat.get_layers())
        missing = expected - actual
        extras = actual - expected
        message = f"Actual layer list did not match expected! (Extras: {extras}) (Missing: {missing})"
        self.assert_(len(expected ^ actual) == 0, message)

        states = self.cat.get_layer("states")

        self.assert_("states", states.name)
        self.assert_(isinstance(states.resource, ResourceInfo))
        self.assertEqual(set(s.name for s in states.styles), set(['pophatch', 'polygon']))
        self.assertEqual(states.default_style.name, "population")

    def testLayerGroups(self):
        expected = set(["tasmania", "tiger-ny", "spearfish"])
        actual = set(l.name for l in self.cat.get_layergroups(names=["tasmania", "tiger-ny", "spearfish"]))
        missing = expected - actual
        extras = actual - expected
        message = f"Actual layergroup list did not match expected! (Extras: {extras}) (Missing: {missing})"
        self.assert_(len(expected ^ actual) == 0, message)

        tas = self.cat.get_layergroups(names="tasmania")[0]

        self.assert_("tasmania", tas.name)
        self.assert_(isinstance(tas, LayerGroup))
        if self.gs_version >= "2.13":
            self.assertEqual(tas.layers, [
                'topp:tasmania_state_boundaries',
                'topp:tasmania_water_bodies',
                'topp:tasmania_roads',
                'topp:tasmania_cities'
            ], tas.layers)
        else:
            self.assertEqual(tas.layers, [
                'tasmania_state_boundaries',
                'tasmania_water_bodies',
                'tasmania_roads',
                'tasmania_cities'
            ], tas.layers)
        self.assertEqual(tas.styles, [None, None, None, None], tas.styles)

        # Try to create a new Layer Group into the "topp" workspace
        self.assert_(self.cat.get_workspaces("topp")[0] is not None)
        tas2 = self.cat.create_layergroup("tasmania_reloaded", tas.layers, workspace = "topp")
        self.cat.save(tas2)
        self.assertEqual(1, len(self.cat.get_layergroups(names='tasmania_reloaded', workspaces="topp")))
        tas2 = self.cat.get_layergroups(names='tasmania_reloaded', workspaces="topp")[0]
        self.assert_("tasmania_reloaded", tas2.name)
        self.assert_(isinstance(tas2, LayerGroup))
        self.assertEqual(tas2.workspace, "topp", tas2.workspace)
        if self.gs_version >= "2.13":
            self.assertEqual(tas2.layers, [
                'topp:tasmania_state_boundaries',
                'topp:tasmania_water_bodies',
                'topp:tasmania_roads',
                'topp:tasmania_cities'
            ], tas2.layers)
        else:
            self.assertEqual(tas2.layers, [
                'tasmania_state_boundaries',
                'tasmania_water_bodies',
                'tasmania_roads',
                'tasmania_cities'
            ], tas2.layers)
        self.assertEqual(tas2.styles, [None, None, None, None], tas2.styles)

    def testStyles(self):
        self.assertEqual("population", self.cat.get_styles("population")[0].name)
        self.assertEqual("popshade.sld", self.cat.get_styles("population")[0].filename)
        self.assertEqual("population", self.cat.get_styles("population")[0].sld_name)
        self.assertEqual("population", self.cat.get_style("population").sld_name)
        self.assertIsNone(self.cat.get_style("blah+#5blah-"))
        self.assertEqual(0, len(self.cat.get_styles('non-existing-style')))

    def testEscaping(self):
        # GSConfig is inconsistent about using exceptions vs. returning None
        # when a resource isn't found.
        # But the basic idea is that none of them should throw HTTP errors from
        # misconstructed URLS
        self.cat.get_styles("best style ever")
        self.cat.get_workspaces("best workspace ever")
        self.assertEqual(0, len(self.cat.get_stores(workspaces="best workspace ever", names="best store ever")))
        self.cat.get_layer("best layer ever")
        self.cat.get_layergroups("best layergroup ever")

    def testUnicodeUrl(self):
        """
        Tests that the geoserver.support.url function support unicode strings.
        """

        # Test the url function with unicode
        seg = ['workspaces', 'test', 'datastores', u'operaci\xf3n_repo', 'featuretypes.xml']
        u = build_url(base=self.cat.service_url, seg=seg)
        self.assertEqual(u, f"{self.cat.service_url}/workspaces/test/datastores/operaci%C3%B3n_repo/featuretypes.xml")

        # Test the url function with normal string
        seg = ['workspaces', 'test', 'datastores', 'test-repo', 'featuretypes.xml']
        u = build_url(base=self.cat.service_url, seg=seg)
        self.assertEqual(u, f"{self.cat.service_url}/workspaces/test/datastores/test-repo/featuretypes.xml")


class ModifyingTests(unittest.TestCase):

    def setUp(self):
        self.cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.gs_version = self.cat.get_short_version()

    def testFeatureTypeSave(self):
        # test saving round trip
        rs = self.cat.get_resources("bugsites", workspaces="sf")[0]
        old_abstract = rs.abstract
        new_abstract = "Not the original abstract"
        enabled = rs.enabled

        # Change abstract on server
        rs.abstract = new_abstract
        self.cat.save(rs)
        rs = self.cat.get_resources("bugsites", workspaces="sf")[0]
        self.assertEqual(new_abstract, rs.abstract)
        self.assertEqual(enabled, rs.enabled)

        # Change keywords on server
        rs.keywords = ["bugsites", "gsconfig"]
        enabled = rs.enabled
        self.cat.save(rs)
        rs = self.cat.get_resources("bugsites", workspaces="sf")[0]
        self.assertEqual(["bugsites", "gsconfig"], rs.keywords)
        self.assertEqual(enabled, rs.enabled)

        # Change metadata links on server
        rs.metadata_links = [("text/xml", "TC211", "http://example.com/gsconfig.test.metadata")]
        enabled = rs.enabled
        self.cat.save(rs)
        rs = self.cat.get_resources("bugsites", workspaces="sf")[0]
        self.assertEqual(
            [("text/xml", "TC211", "http://example.com/gsconfig.test.metadata")],
            rs.metadata_links)
        self.assertEqual(enabled, rs.enabled)

        # Restore abstract
        rs.abstract = old_abstract
        self.cat.save(rs)
        rs = self.cat.get_resources("bugsites", workspaces="sf")[0]
        self.assertEqual(old_abstract, rs.abstract)

    def testDataStoreCreate(self):
        ds = self.cat.create_datastore("vector_gsconfig")
        ds.connection_parameters.update(**DBPARAMS)
        self.cat.save(ds)

    def testPublishFeatureType(self):
        # Use the other test and store creation to load vector data into a database
        # @todo maybe load directly to database?
        try:
            self.testDataStoreCreateAndThenAlsoImportData()
        except FailedRequestError:
            pass
        try:
            lyr = self.cat.get_layer('import')
            data_source_name = lyr.resource.native_name
            # Delete the existing layer and resource to allow republishing.
            self.cat.delete(lyr)
            self.cat.delete(lyr.resource)
            ds = self.cat.get_stores("gsconfig_import_test")[0]
            # make sure it's gone
            self.assert_(self.cat.get_layer('import') is None)
            self.cat.publish_featuretype("import", ds, native_crs="EPSG:4326", native_name=data_source_name)
            # and now it's not
            self.assert_(self.cat.get_layer('import') is not None)
        finally:
            # tear stuff down to allow the other test to pass if we run first
            ds = self.cat.get_stores("gsconfig_import_test")[0]
            lyr = self.cat.get_layer('import')
            # Delete the existing layer and resource to allow republishing.
            try:
                if lyr:
                    self.cat.delete(lyr)
                    self.cat.delete(lyr.resource)
                if ds:
                    self.cat.delete(ds)
            except BaseException:
                pass

    def testDataStoreModify(self):
        ds = self.cat.get_stores("sf")[0]
        self.assertFalse("foo" in ds.connection_parameters)
        ds.connection_parameters = ds.connection_parameters
        ds.connection_parameters["foo"] = "bar"
        orig_ws = ds.workspace.name
        self.cat.save(ds)
        ds = self.cat.get_stores("sf")[0]
        self.assertTrue("foo" in ds.connection_parameters)
        self.assertEqual("bar", ds.connection_parameters["foo"])
        self.assertEqual(orig_ws, ds.workspace.name)

    @drop_table('import')
    def testDataStoreCreateAndThenAlsoImportData(self):
        ds = self.cat.create_datastore("gsconfig_import_test")
        ds.connection_parameters.update(**DBPARAMS)
        self.cat.save(ds)
        ds = self.cat.get_stores("gsconfig_import_test")[0]
        self.cat.add_data_to_store(ds, "import", {
            'shp': 'test/data/states.shp',
            'shx': 'test/data/states.shx',
            'dbf': 'test/data/states.dbf',
            'prj': 'test/data/states.prj'
        })

    @drop_table('import2')
    def testVirtualTables(self):
        ds = self.cat.create_datastore("gsconfig_import_test2")
        ds.connection_parameters.update(**DBPARAMS)
        self.cat.save(ds)
        ds = self.cat.get_stores("gsconfig_import_test2")[0]
        self.cat.add_data_to_store(ds, "import2", {
            'shp': 'test/data/states.shp',
            'shx': 'test/data/states.shx',
            'dbf': 'test/data/states.dbf',
            'prj': 'test/data/states.prj'
        })

        geom = JDBCVirtualTableGeometry('the_geom', 'MultiPolygon', '4326')
        ft_name = 'my_jdbc_vt_test'
        epsg_code = 'EPSG:4326'
        sql = "select * from import2 where 'STATE_NAME' = 'Illinois'"
        keyColumn = None
        parameters = None

        jdbc_vt = JDBCVirtualTable(ft_name, sql, 'false', geom, keyColumn, parameters)
        ft = self.cat.publish_featuretype(ft_name, ds, epsg_code, jdbc_virtual_table=jdbc_vt)

    # DISABLED; this test works only in the very particular case
    # "mytiff.tiff" is already present into the GEOSERVER_DATA_DIR
    # def testCoverageStoreCreate(self):
    #     ds = self.cat.create_coveragestore2("coverage_gsconfig")
    #     ds.data_url = "file:test/data/mytiff.tiff"
    #     self.cat.save(ds)

    def testCoverageStoreModify(self):
        cs = self.cat.get_stores("sfdem")[0]
        self.assertEqual("GeoTIFF", cs.type)
        cs.type = "WorldImage"
        self.cat.save(cs)
        cs = self.cat.get_stores("sfdem")[0]
        self.assertEqual("WorldImage", cs.type)

        # not sure about order of test runs here, but it might cause problems
        # for other tests if this layer is misconfigured
        cs.type = "GeoTIFF"
        self.cat.save(cs)

    def testCoverageSave(self):
        # test saving round trip
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        old_abstract = rs.abstract
        new_abstract = "Not the original abstract"

        # # Change abstract on server
        rs.abstract = new_abstract
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEqual(new_abstract, rs.abstract)

        # Restore abstract
        rs.abstract = old_abstract
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEqual(old_abstract, rs.abstract)

        # Change metadata links on server
        rs.metadata_links = [("text/xml", "TC211", "http://example.com/gsconfig.test.metadata")]
        enabled = rs.enabled
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEqual(
            [("text/xml", "TC211", "http://example.com/gsconfig.test.metadata")],
            rs.metadata_links)
        self.assertEqual(enabled, rs.enabled)

        srs_before = set(['EPSG:4326'])
        srs_after = set(['EPSG:4326', 'EPSG:3785'])
        formats = set(['ARCGRID', 'ARCGRID-GZIP', 'GEOTIFF', 'PNG', 'GIF', 'TIFF'])
        formats_after = set(["PNG", "GIF", "TIFF"])

        # set and save request_srs_list
        self.assertEquals(set(rs.request_srs_list), srs_before, str(rs.request_srs_list))
        rs.request_srs_list = rs.request_srs_list + ['EPSG:3785']
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEquals(set(rs.request_srs_list), srs_after, str(rs.request_srs_list))

        # set and save response_srs_list
        self.assertEquals(set(rs.response_srs_list), srs_before, str(rs.response_srs_list))
        rs.response_srs_list = rs.response_srs_list + ['EPSG:3785']
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEquals(set(rs.response_srs_list), srs_after, str(rs.response_srs_list))

        # set and save supported_formats
        self.assertEquals(set(rs.supported_formats), formats, str(rs.supported_formats))
        rs.supported_formats = ["PNG", "GIF", "TIFF"]
        self.cat.save(rs)
        rs = self.cat.get_resources("Arc_Sample", workspaces="nurc")[0]
        self.assertEquals(set(rs.supported_formats), formats_after, str(rs.supported_formats))

    def testWmsStoreCreate(self):
        ws = self.cat.create_wmsstore("wmsstore_gsconfig")
        ws.capabilitiesURL = "http://mesonet.agron.iastate.edu/cgi-bin/wms/iowa/rainfall.cgi?VERSION=1.1.1&REQUEST=GetCapabilities&SERVICE=WMS&"
        ws.type = "WMS"
        self.cat.save(ws)

    def testWmsLayer(self):
        self.cat.create_workspace("wmstest", "http://example.com/wmstest")
        wmstest = self.cat.get_workspaces("wmstest")[0]
        wmsstore = self.cat.create_wmsstore("wmsstore", wmstest)
        wmsstore.capabilitiesURL = "http://mesonet.agron.iastate.edu/cgi-bin/wms/iowa/rainfall.cgi?VERSION=1.1.1&REQUEST=GetCapabilities&SERVICE=WMS&"
        wmsstore.type = "WMS"
        self.cat.save(wmsstore)
        wmsstore = self.cat.get_stores("wmsstore")[0]
        self.assertEqual(1, len(self.cat.get_stores(workspaces=wmstest.name)))
        available_layers = wmsstore.get_resources(available=True)
        for layer in available_layers:
            # sanitize the layer name - validation will fail on newer geoservers
            name = layer.replace(':', '_')
            new_layer = self.cat.create_wmslayer(wmstest, wmsstore, name, nativeName=layer)
        added_layers = wmsstore.get_resources()
        self.assertEqual(len(available_layers), len(added_layers))

        changed_layer = added_layers[0]
        self.assertEqual(True, changed_layer.advertised)
        self.assertEqual(True, changed_layer.enabled)
        changed_layer.advertised = False
        changed_layer.enabled = False
        self.cat.save(changed_layer)
        self.cat._cache.clear()
        changed_layer = wmsstore.get_resources()[0]
        changed_layer.fetch()
        self.assertEqual(False, changed_layer.advertised)
        self.assertEqual(False, changed_layer.enabled)

        # Testing projection and projection policy changes
        changed_layer.projection = "EPSG:900913"
        changed_layer.projection_policy = "REPROJECT_TO_DECLARED"
        self.cat.save(changed_layer)
        self.cat._cache.clear()
        layer = self.cat.get_layer(changed_layer.name)
        self.assertEqual(layer.resource.projection_policy, changed_layer.projection_policy)
        self.assertEqual(layer.resource.projection, changed_layer.projection)

    def testFeatureTypeCreate(self):
        shapefile_plus_sidecars = shapefile_and_friends("test/data/states")
        expected = {
            'shp': 'test/data/states.shp',
            'shx': 'test/data/states.shx',
            'dbf': 'test/data/states.dbf',
            'prj': 'test/data/states.prj'
        }

        self.assertEqual(len(expected), len(shapefile_plus_sidecars))
        for k, v in expected.items():
            self.assertEqual(v, shapefile_plus_sidecars[k])

        sf = self.cat.get_workspaces("sf")[0]
        self.cat.create_featurestore("states_test", shapefile_plus_sidecars, sf.name)
        self.assert_(len(self.cat.get_resources("states_test", workspaces=sf.name)) > 0)

        self.assertRaises(
            ConflictingDataError,
            lambda: self.cat.create_featurestore("states_test", shapefile_plus_sidecars, sf)
        )

        lyr = self.cat.get_layer("states_test")
        self.cat.delete(lyr)
        self.assert_(self.cat.get_layer("states_test") is None)

    def testLayerSave(self):
        # test saving round trip
        lyr = self.cat.get_layer("states")
        old_attribution = lyr.attribution
        new_attribution = {
            'title': 'Not the original attribution',
            'width': '123',
            'height': '321',
            'href': 'http://www.georchestra.org',
            'url': 'https://www.cigalsace.org/portail/cigal/documents/page/mentions-legales/Logo_geOrchestra.jpg',
            'type': 'image/jpeg'
        }

        # change attribution on server
        lyr.attribution = new_attribution
        self.cat.save(lyr)
        lyr = self.cat.get_layer("states")
        self.assertEqual(new_attribution, lyr.attribution)

        # Restore attribution
        lyr.attribution = old_attribution
        self.cat.save(lyr)
        lyr = self.cat.get_layer("states")
        self.assertEqual(old_attribution, lyr.attribution)

        self.assertEqual(lyr.default_style.name, "population")

        old_default_style = lyr.default_style
        lyr.default_style = 'pophatch'
        lyr.styles = [old_default_style]
        self.cat.save(lyr)
        lyr = self.cat.get_layer("states")
        self.assertEqual(lyr.default_style.name, "pophatch")
        self.assertEqual([s.name for s in lyr.styles], ["population"])

    def testStyles(self):
        # check count before tests (upload)
        count = len(self.cat.get_styles())

        # upload new style, verify existence
        self.cat.create_style("fred", open("test/fred.sld").read())
        self.cat._cache.clear()
        fred = self.cat.get_styles(names="fred")[0]
        self.assert_(fred is not None)
        self.assertEqual("Fred", fred.sld_title)

        # replace style, verify changes
        self.cat.create_style("fred", open("test/ted.sld").read(), overwrite=True)
        self.cat._cache.clear()
        fred = self.cat.get_styles("fred")[0]
        self.assert_(fred is not None)
        self.assertEqual("Ted", fred.sld_title)

        # delete style, verify non-existence
        self.cat.delete(fred, purge=True)
        self.cat._cache.clear()
        self.assert_(len(self.cat.get_styles("fred")) == 0)

        # attempt creating new style
        self.cat.create_style("fred", open("test/fred.sld").read())
        self.cat._cache.clear()
        fred = self.cat.get_styles("fred")[0]
        self.assertEqual("Fred", fred.sld_title)

        # compare count after upload
        self.assertEqual(count + 1, len(self.cat.get_styles()))

        # attempt creating a new style without "title"
        self.cat.create_style("notitle", open("test/notitle.sld").read())
        self.cat._cache.clear()
        notitle = self.cat.get_styles("notitle")[0]
        self.assertEqual(None, notitle.sld_title)

    def testWorkspaceStyles(self):
        # upload new style, verify existence
        self.cat.create_style("jed", open("test/fred.sld").read(), workspace="topp")
        self.cat._cache.clear()

        jed = self.cat.get_styles(names="jed", workspaces="blarny")
        self.assert_(len(jed) == 0)
        jed = self.cat.get_styles(names="jed", workspaces="topp")
        self.assert_(len(jed) == 1)
        self.assertEqual("Fred", jed[0].sld_title)

        # replace style, verify changes
        self.cat.create_style("jed", open("test/ted.sld").read(), overwrite=True, workspace="topp")
        self.cat._cache.clear()
        jed = self.cat.get_styles(names="jed", workspaces="topp")
        self.assert_(len(jed) == 1)
        self.assertEqual("Ted", jed[0].sld_title)

        # delete style, verify non-existence
        self.cat.delete(jed[0], purge=True)
        self.assertEqual(0, len(self.cat.get_styles(names="jed", workspaces="topp")))

        # attempt creating new style
        self.cat.create_style("jed", open("test/fred.sld").read(), workspace="topp")
        self.cat._cache.clear()
        jed = self.cat.get_styles(names="jed", workspaces="topp")
        self.assertEqual("Fred", jed[0].sld_title)

    def testLayerWorkspaceStyles(self):
        # upload new style, verify existence
        self.cat.create_style("ned", open("test/fred.sld").read(), overwrite=True, workspace="topp")
        self.cat.create_style("zed", open("test/ted.sld").read(), overwrite=True, workspace="topp")
        self.cat._cache.clear()
        styles = self.cat.get_styles(names="ned, zed", workspaces="topp")
        self.assertEqual(2, len(styles))
        ned, zed = styles

        lyr = self.cat.get_layer("states")
        lyr.default_style = ned
        lyr.styles = [zed]
        self.cat.save(lyr)
        self.assertEqual("topp:ned", lyr.default_style)
        self.assertEqual([zed], lyr.styles)

        lyr.refresh()
        self.assertEqual("topp:ned", lyr.default_style.fqn)
        self.assertEqual([zed.fqn], [s.fqn for s in lyr.styles])

    def testWorkspaceCreate(self):
        ws = self.cat.get_workspaces("acme")
        self.assertEqual(0, len(ws))
        self.cat.create_workspace("acme", "http://example.com/acme")
        ws = self.cat.get_workspaces("acme")[0]
        self.assertEqual("acme", ws.name)

    def testWorkspaceDelete(self):
        self.cat.create_workspace("foo", "http://example.com/foo")
        ws = self.cat.get_workspaces("foo")[0]
        self.cat.delete(ws)
        ws = self.cat.get_workspaces("foo")
        self.assertEqual(0, len(ws))

    def testWorkspaceDefault(self):
        # save orig
        orig = self.cat.get_default_workspace()
        neu = self.cat.create_workspace("neu", "http://example.com/neu")
        try:
            # make sure setting it works
            self.cat.set_default_workspace("neu")
            ws = self.cat.get_default_workspace()
            self.assertEqual('neu', ws.name)
        finally:
            # cleanup and reset to the way things were
            self.cat.delete(neu)
            self.cat.set_default_workspace(orig.name)
            ws = self.cat.get_default_workspace()
            self.assertEqual(orig.name, ws.name)

    def testFeatureTypeDelete(self):
        pass

    def testCoverageDelete(self):
        pass

    def testDataStoreDelete(self):
        states = self.cat.get_stores('states_shapefile')[0]
        self.assert_(states.enabled)
        states.enabled = False
        self.assert_(states.enabled == False)
        self.cat.save(states)

        states = self.cat.get_stores('states_shapefile')[0]
        self.assert_(states.enabled == False)

        states.enabled = True
        self.cat.save(states)

        states = self.cat.get_stores('states_shapefile')[0]
        self.assert_(states.enabled)

    def testLayerGroupSave(self):
        tas = self.cat.get_layergroups("tasmania")[0]

        if self.gs_version >= "2.13":
            self.assertEqual(tas.layers, [
                'topp:tasmania_state_boundaries',
                'topp:tasmania_water_bodies',
                'topp:tasmania_roads',
                'topp:tasmania_cities'
            ], tas.layers)
        else:
            self.assertEqual(tas.layers, [
                'tasmania_state_boundaries',
                'tasmania_water_bodies',
                'tasmania_roads',
                'tasmania_cities'
            ], tas.layers)
        self.assertEqual(tas.styles, [None, None, None, None], tas.styles)

        tas.layers = tas.layers[:-1]
        tas.styles = tas.styles[:-1]

        self.cat.save(tas)

        # this verifies the local state
        if self.gs_version >= "2.13":
            self.assertEqual(tas.layers, [
                'topp:tasmania_state_boundaries',
                'topp:tasmania_water_bodies',
                'topp:tasmania_roads'
            ], tas.layers)
        else:
            self.assertEqual(tas.layers, [
                'tasmania_state_boundaries',
                'tasmania_water_bodies',
                'tasmania_roads'
            ], tas.layers)
        self.assertEqual(tas.styles, [None, None, None], tas.styles)

        # force a refresh to check the remote state
        # tas.refresh()
        if self.gs_version >= "2.13":
            self.assertEqual(tas.layers, [
                'topp:tasmania_state_boundaries',
                'topp:tasmania_water_bodies',
                'topp:tasmania_roads'
            ], tas.layers)
        else:
            self.assertEqual(tas.layers, [
                'tasmania_state_boundaries',
                'tasmania_water_bodies',
                'tasmania_roads'
            ], tas.layers)
        self.assertEqual(tas.styles, [None, None, None], tas.styles)

    def testImageMosaic(self):
        """
            Test case for Issue #110
        """
        # testing the mosaic creation
        name = 'cea_mosaic'
        data = open('test/data/mosaic/cea.zip', 'rb')
        self.cat.create_imagemosaic(name, data)

        # get the layer resource back
        self.cat._cache.clear()
        resource = self.cat.get_layer(name).resource

        self.assert_(resource is not None)

        # delete granule from mosaic
        coverage = name
        store = self.cat.get_stores(name)[0]
        granules = self.cat.list_granules(coverage, store)
        self.assertEqual(1, len(granules['features']))
        granule_id = f"{name}.1"
        self.cat.delete_granule(coverage, store, granule_id)
        granules = self.cat.list_granules(coverage, store)
        self.assertEqual(0, len(granules['features']))

        '''
          testing external Image mosaic creation
        '''
        name = 'cea_mosaic_external'
        path = os.path.join(os.getcwd(), 'test/data/mosaic/external')
        self.cat.create_imagemosaic(name, path, workspace='topp')
        self.cat._cache.clear()
        resource = self.cat.get_layer("external").resource
        self.assert_(resource is not None)

        # add granule to mosaic
        granule_path = os.path.join(os.getcwd(), 'test/data/mosaic/granules/cea_20150102.tif')
        self.cat.add_granule(granule_path, name, workspace='topp')
        granules = self.cat.list_granules("external", name, 'topp')
        self.assertEqual(2, len(granules['features']))

        # add external granule to mosaic
        granule_path = os.path.join(os.getcwd(), 'test/data/mosaic/granules/cea_20150103.zip')
        self.cat.add_granule(granule_path, name, workspace='topp')
        granules = self.cat.list_granules("external", name, 'topp')
        self.assertEqual(3, len(granules['features']))

        # Delete store
        store = self.cat.get_stores(name)[0]
        self.cat.delete(store, purge=True, recurse=True)
        self.cat._cache.clear()

    def testTimeDimension(self):
        sf = self.cat.get_workspaces("sf")[0]
        files = shapefile_and_friends(os.path.join(gisdata.GOOD_DATA, "time", "boxes_with_end_date"))
        self.cat.create_featurestore("boxes_with_end_date", files, sf)

        def get_resource(): return self.cat._cache.clear() or self.cat.get_layer('boxes_with_end_date').resource

        # configure time as LIST
        resource = get_resource()
        timeInfo = DimensionInfo("time", "true", "LIST", None, "ISO8601", None, attribute="date")
        resource.metadata = {'time': timeInfo}
        self.cat.save(resource)
        # and verify
        resource = get_resource()
        timeInfo = resource.metadata['time']
        self.assertEqual("LIST", timeInfo.presentation)
        self.assertEqual(True, timeInfo.enabled)
        self.assertEqual("date", timeInfo.attribute)
        self.assertEqual("ISO8601", timeInfo.units)

        # disable time dimension
        timeInfo = resource.metadata['time']
        timeInfo.enabled = False
        # since this is an xml property, it won't get written unless we modify it
        resource.metadata = {'time': timeInfo}
        self.cat.save(resource)
        # and verify
        resource = get_resource()
        timeInfo = resource.metadata['time']
        self.assertEqual(False, timeInfo.enabled)

        # configure with interval, end_attribute and enable again
        timeInfo.enabled = True
        timeInfo.presentation = 'DISCRETE_INTERVAL'
        timeInfo.resolution = '3 days'
        timeInfo.end_attribute = 'enddate'
        resource.metadata = {'time': timeInfo}
        self.cat.save(resource)
        # and verify
        resource = get_resource()
        timeInfo = resource.metadata['time']
        self.assertEqual(True, timeInfo.enabled)
        self.assertEqual('DISCRETE_INTERVAL', timeInfo.presentation)
        self.assertEqual('3 days', timeInfo.resolution_str())
        self.assertEqual('enddate', timeInfo.end_attribute)


if __name__ == "__main__":
    unittest.main()
