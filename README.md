# PACE Station Extractor

A robust Python utility to search, download, and extract hyperspectral Remote Sensing Reflectance ($R_{rs}$) and Rayleigh-Corrected Reflectance ($R_{rc}$) from NASA PACE OCI Level 2 data for fixed sampling stations.

## Features
- **Resume Capability**: Skips stations and product types that have already been successfully processed.
- **Batch Processing**: Periodically saves data to disk during long extractions to prevent memory-related kernel crashes.
- **Hyperspectral Support**: Extracts the full OCI spectra (UV to NIR) for specific coordinates.
- **Product Choice**: Easily switch between standard $R_{rs}$ and coastal-optimized $R_{rc}$.

## Prerequisites
- **Python 3.12**: This project is optimized for 3.12. (Note: Issues have been observed with NASA data backends on Python 3.13).
- **NASA Earthdata Account**: You must have a login to access PACE data.

## Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/pace-station-extractor.git](https://github.com/your-username/pace-station-extractor.git)
   cd pace-station-extractor
   ```

2. Optionally create and activate an environment (Conda or venv):
```bash
conda create -n pace_env python=3.12
conda activate pace_env
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage
1. Login: Authenticate with NASA Earthdata
```python
import earthaccess
earthaccess.login()
```
2. Run Extraction: Use the PaceExtractor class in your notebook or script:
```python
from pace_station_extractor import PaceExtractor
extractor = PaceExtractor(output_dir="my_pace_files", batch_size=20)
granules = extractor.find_granules("Rrc", lat=32.867, lon=-117.257, temporal=("2024-04-11", "2024-12-31"))
extractor.extract_and_save("SIO", granules, lat=32.867, lon=-117.257, product_type="Rrc")
```
3. Run: Execute the extraction script
4. Review: Check the output files for your data

## Project Structure
* `pace_extractor.py`: Main extraction logic
* `main.py`: Entry point for processing multiple stations from a CSV.
* `requirements.txt`: Python dependencies
* `README.md`: This file