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

def shapefile_and_friends(path):
    return {ext: f"{path}.{ext}" for ext in ['shx', 'shp', 'dbf', 'prj']}
