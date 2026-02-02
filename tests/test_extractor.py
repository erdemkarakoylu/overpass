import pytest
import xarray as xr
import numpy as np
from pathlib import Path
from pace_extractor import PaceExtractor

def test_directory_creation(tmp_path):
    # tmp_path is a built-in pytest fixture that is a pathlib.Path object
    ex = PaceExtractor(output_dir=tmp_path / "test_data")
    assert (tmp_path / "test_data").exists()

def test_resume_logic(tmp_path):
    ex = PaceExtractor(output_dir=tmp_path, batch_size=2)
    test_file = tmp_path / "TEST_Rrs_final.nc"
    
    # Create a dummy final file
    ds = xr.Dataset({"Rrs": (["w"], [1, 2])}, coords={"w": [400, 500]})
    ds.to_netcdf(test_file)
    
    # This should return immediately without trying to "download"
    result = ex.extract_and_save("TEST", [], 0, 0, "Rrs")
    assert result is not None