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
"""utils to centralize global variabl settings configurable by env vars."""
import os
import tempfile

# envs that can be override by os.environ envs
GSHOSTNAME = 'localhost'
GSPORT = '8080'
GSSSHPORT = '8443'
GSUSER = 'admin'
GSPASSWORD = 'geoserver'
GS_BASE_DIR = tempfile.gettempdir()


def geoserverLocation():
    """get GSHOSTNAME and GSPORT or use default localhost:8080."""
    server = GSHOSTNAME
    port = GSPORT
    server = os.getenv('GSHOSTNAME', server)
    port = os.getenv('GSPORT', port)
    return f'{server}:{port}'


def geoserverLocationSsh():
    """get GSSSHPORT and GSSSHPORT or use default localhost:8443."""
    location = geoserverLocation().split(":")[0]
    sshport = GSSSHPORT
    sshport = os.getenv('GSSSHPORT', sshport)
    return f'{location}:{sshport}'


def serverLocationBasicAuth():
    """Set server URL for http connection."""
    return f"http://{geoserverLocation()}/geoserver"


def serverLocationPkiAuth():
    """Set server URL for https connection."""
    return f"https://{geoserverLocationSsh()}/geoserver"


GSPARAMS = dict(
    GSURL=f"{serverLocationBasicAuth()}/rest",
    GSUSER=GSUSER,
    GSPASSWORD=GSPASSWORD,
    GEOSERVER_HOME='',
    DATA_DIR='',
    GS_VERSION='',
    GS_BASE_DIR=GS_BASE_DIR
)
GSPARAMS.update([(k, os.getenv(k)) for k in GSPARAMS if k in os.environ])

DBPARAMS = dict(
    host=os.getenv("DBHOST", "localhost"),
    port=os.getenv("DBPORT", "5432"),
    dbtype=os.getenv("DBTYPE", "postgis"),
    database=os.getenv("DATABASE", "db"),
    user=os.getenv("DBUSER", "postgres"),
    passwd=os.getenv("DBPASS", "postgres")
)
print('*** GSPARAMS ***')
print(GSPARAMS)
print('*** DBPARAMS ***')
print(DBPARAMS)
