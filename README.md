# Overpass

A robust Python utility to search, download, and extract hyperspectral Remote Sensing Reflectance ($R_{rs}$) and Rayleigh-Corrected Reflectance ($R_{rc}$) from NASA PACE OCI Level 2 data for fixed sampling stations.

## Features
- **Structured Logging**: Uses `loguru` for clear, checkpoint-aware status reporting.
- **Resume Capability**: Automatically skips stations and products that are already complete by checking for final files and checkpoints.
- **Batch Processing**: Periodically saves data to disk during long extractions to prevent memory-related kernel crashes.
- **Hyperspectral Support**: Extracts full OCI spectra (UV to NIR) for specific coordinates.
- **Coastal Optimized**: Provides utilities to handle $R_{rc}$ data and custom flag filtering for turbid waters.

## Prerequisites
- **Python 3.12**: This project is strictly optimized for 3.12 due to stability issues with NASA backends on Python 3.13.
- **NASA Earthdata Account**: [Register here](https://urs.earthdata.nasa.gov/) to access PACE data.

## Installation


### 1. Create Environment
```bash
conda create -n overpass_env python=3.12 -y
conda activate overpass_env
```

### 2. Clone & Install
```bash
git clone [https://github.com/your-username/overpass.git](https://github.com/your-username/overpass.git)
cd overpass
pip install -r requirements.txt
pip install -e .
```

## Usage

### 1. Login to Earthdata
```python
import earthaccess
earthaccess.login()
```

### 2. Extract Data
```python
from overpass import OverpassExtractor, filter_rrc

# Initialize extractor (saves a checkpoint every 20 scenes)
extractor = OverpassExtractor(output_dir="data_output", batch_size=20)

# Station Coordinates (e.g., Scripps Pier)
lat, lon = 32.867, -117.257

# Search for Rayleigh-Corrected granules
granules = extractor.find_granules("Rrc", lat, lon, temporal=("2024-04-11", "2026-01-30"))

# Extract and Save (handles batching and resuming automatically)
final_path = extractor.extract_and_save("SIO", granules, lat, lon, "Rrc")
```

### 3. Coastal Filtering
```python
import xarray as xr

if final_path:
    ds = xr.open_dataset(final_path)
    # Use the helper to mask land, clouds, and saturated pixels
    # This keeps valid coastal spectra that standard L2 flags might over-mask
    ds_clean = filter_rrc(ds)
```

## Project Structure
- `overpass.py`: Core library containing `OverpassExtractor` class and `filter_rrc` utility.
- `main.py`: Entry point for batch processing stations from a CSV (e.g., CalHABMAP).
- `tests/`: Unit tests using dummy data to verify checkpoint and resume logic.

## License
MIT