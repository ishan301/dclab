#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import numpy as np
import os
from os.path import join, exists, isdir, dirname, abspath
import sys
import tempfile

# Add parent directory to beginning of path variable
sys.path.insert(0, dirname(dirname(abspath(__file__))))

import dclab


from helper_methods import example_data_dict

filter_data="""[Polygon 00000000]
X Axis = Area
Y Axis = Defo
Name = polygon filter 0
point00000000 = 6.344607717656481e-03 7.703315881326352e-01
point00000001 = 7.771010748302133e-01 7.452006980802792e-01
point00000002 = 8.025596093384512e-01 6.806282722513089e-03
point00000003 = 6.150993521573982e-01 1.015706806282723e-03
"""

def test_polygon_import():
    dclab.PolygonFilter.clear_all_filters()
    ddict = example_data_dict(size=1000, keys=["Area", "Defo"])
    ds = dclab.RTDC_DataSet(ddict=ddict)

    # save polygon data
    with tempfile.NamedTemporaryFile(mode="w") as temp:
        temp.write(filter_data)
        temp.flush()
        
        # Add polygon filter
        pf = dclab.PolygonFilter(filename=temp.name)
        ds.PolygonFilterAppend(pf)
        
        ds.ApplyFilter()

        assert np.sum(ds._filter) == 330

        dclab.PolygonFilter.import_all(temp.name)

        assert len(dclab.PolygonFilter.instances) == 2


def test_polygon_save():
    dclab.PolygonFilter.clear_all_filters()
    
    with tempfile.NamedTemporaryFile(mode="w") as temp:
        temp.write(filter_data)
        temp.flush()
        
        # Add polygon filter
        pf = dclab.PolygonFilter(filename=temp.name)
        
        with tempfile.NamedTemporaryFile(mode="w") as temp2:
            pf.save(temp2, ret_fobj=True)
            temp2.flush()
            
            pf2 = dclab.PolygonFilter(filename=temp2.name)
            
            assert np.allclose(pf.points, pf2.points)

    with tempfile.NamedTemporaryFile(mode="w") as temp3:
        dclab.PolygonFilter.save_all(temp3)

    # ensure backwards compatibility: the names of the three filters should be the same
    names = dclab.polygon_filter.GetPolygonFilterNames()
    assert len(names) == 2
    assert names.count(names[0]) == 2


def test_polygon_remove():
    dclab.PolygonFilter.clear_all_filters()
    
    with tempfile.NamedTemporaryFile(mode="w") as temp:
        temp.write(filter_data)
        temp.flush()
        
        # Add polygon filter
        pf = dclab.PolygonFilter(filename=temp.name)    
    
    dclab.PolygonFilter.remove(pf.unique_id)
    assert len(dclab.PolygonFilter.instances) == 0


if __name__ == "__main__":
    # Run all tests
    loc = locals()
    for key in list(loc.keys()):
        if key.startswith("test_") and hasattr(loc[key], "__call__"):
            loc[key]()
    