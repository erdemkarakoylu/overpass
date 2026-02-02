from pathlib import Path

import earthaccess
import xarray as xr
import numpy as np
import pandas as pd
from loguru import logger

from tqdm import tqdm

class PaceExtractor:
    def __init__(self, output_dir="pace_data", batch_size=50):
        """
        Initializes the extractor with a focus on batch processing and resumption.
        
        Args:
            output_dir: Directory where checkpoints and final NetCDF files are stored.
            batch_size: Number of granules to process before saving a checkpoint.
        """
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized PaceExtractor with output directory: {self.output_dir}")
    
    def find_granules(self, product_type:str, lat:float, lon:float, temporal_range:tuple[str, str]):
        """
        Wraps earthaccess.search_data to return a list of granules.
        Args:
            product_type: 'Rrs' for standard AOP or 'Rrc' for Rayleigh Corrected.
            lat, lon: Station coordinates.
            temporal_range: Tuple of (start_date, end_date) e.g., ("2024-04-11", "2025-12-31").
        """
        short_name = "PACE_OCI_L2_AOP" if product_type == "Rrs" else "PACE_OCI_L2_RRC"
        logger.info(f"Searching for {product_type} granules at ({lat}, {lon}) for {temporal}...")
        results = earthaccess.search_data(
            short_name=short_name,
            point=(lon, lat),
            temporal=temporal_range,
            count=-1
        )
        logger.info(f"Found {len(results)} granules for {product_type}.")
        return results

    def _get_checkpoint_path(self, station_code:str, product_type:str, batch_index:int) -> Path:
        """Helper to generate standardized checkpoint filenames."""
        batch_num = batch_index // self.batch_size
        return self.output_dir / f"checkpoint_{station_code}_{product_type}_b{batch_num:04d}.nc"


    def _extract_granule_pixel(self, file_obj, lat: float, lon: float, var_name: str) -> xr.Dataset:
        """
        Auxiliary: Opens a single PACE NetCDF and extracts the closest pixel spectra.
        Handles the OCI hierarchical group structure.
        """
        with xr.open_dataset(file_obj, group='navigation_data') as ds_nav, \
             xr.open_dataset(file_obj, group='geophysical_data') as ds_geo, \
             xr.open_dataset(file_obj, group='sensor_band_parameters') as ds_band:

            # Find closes pixel using Euclidean distance on 2D lat/lon arrays
            dist = np.sqrt((ds_nav.latitude - lat)**2 + (ds_nav.longitude - lon)**2)
            idx = dist.argmin()
            iy, ix = np.unravel_index(idx.values, dist.shape)

            return xr.Dataset(
                {
                    var_name: (["wavelength"],ds_geo[var_name].isel(number_of_lines=iy, pixels_per_line=ix).values)},
                    coords = {
                        'wavelength': ds_band.wavelength.values,
                        'time': pd.to_datetime(ds_nav.attrs['time_coverage_start']),
                        'l2_flags': ds_geo.l2_flags.isel(number_of_lines=iy, pixels_per_line=ix).values,
                        'lat': ds_nav.latitude.isel(number_of_lines=iy, pixels_per_line=ix).values,
                        'lon': ds_nav.longitude.isel(number_of_lines=iy, pixels_per_line=ix).values
                    }
            )
        
    
    def extract_and_save(self, station_code:str, granules, lat: float, lon: float, product_type: str):
        """
        Orchestrates the extraction process with checkpoint resumption and batch saving.
        """

        final_path = self.output_dir / f"{station_code}_{product_type}_final.nc"
        if final_path.exists():
            logger.info(f"[{station_code}] {product_type}: Final file exists. Skipping.")
            return final_path
        
        # Determine how many granules are already processed via checkpoints
        checkpoints = sorted(list(
                self.output_dir.glob(
                    f"checkpoint_{station_code}_{product_type}_b*.nc")
                ))
        total_granules = len(granules)
        processed_count = len(checkpoints) * self.batch_size

        if processed_count >= total_granules and total_granules > 0:
            logger.info(
                f"[{station_code}] - All granules present in checkpoints. Finalizing...")
            return self._finalize_station(station_code, product_type, final_path)
        
        logger.info(
            f"[{station_code}] {product_type}: Processed {processed_count} / {total_granules}. Resuming...")
        
        remaining_granules = granules[processed_count:]
        var_name = "Rrs" if product_type == "Rrs" else "Rrc"
        current_batch = []
        
        # Open S3/HTTP streams
        files = earthaccess.open(remaining_granules)
        for i, f in enumerate(
            tqdm(files, initial=processed_count, total=total_granules, desc=f"OCI {station_code}")):
            try:
                ds_pixel = self._extract_granule_pixel(f, lat, lon, var_name)
                current_batch.append(ds_pixel)

                global_idx = processed_count + i + 1
                # Save checkpoint if batch is full or it's the last granule
                if (global_idx % self.batch_size == 0) or (global_idx == total_granules):
                    batch_path = self._get_checkpoint_path(station_code, product_type, global_idx)
                    xr.concat(current_batch, dim='time').to_netcdf(batch_path)
                    logger.info(f"Saved Checkpoint: {batch_path.name} ({global_idx}/{total_granules})")
                    current_batch = []
            except Exception as e:
                logger.error(f"Failed Granule {processed_count + i}: {e}")
                continue

        return self._finalize_station(station_code, product_type, final_path)

    def _finalize_station(self, station_code: str, product_type: str, final_path: Path) -> Path|None:
        """
        Merges all checkpoint NetCDF files into a single sorted time-series and cleans up.
        """
        checkpoints = sorted(list(
            self.output_dir.glob(
                f"checkpoint_{station_code}_{product_type}_b*.nc")
        ))
                
        if not checkpoints:
            logger.warning(f"[{station_code}] - No batches found to finalize.")
            return None
        
        logger.info(f"[{station_code}] - Merging {len(checkpoints)} checkpoints...")
        
        # Open and concatenate all batches
        with xr.open_mfdataset(checkpoints, combine='nested', concat_dim="time") as ds:
            final_ds = ds.sortby('time').load() # Load into memory for final save
            final_ds.attrs['station_code'] = station_code
            final_ds.to_netcdf(final_path)
        
        # Delete checkpoints only after successful final_save
        for cp in checkpoints:
            cp.unlink()
        
        logger.success(f"[{station_code}] {product_type} - Data saved to: {final_path.name}")
        
        return final_path



def filter_rrc(ds):
    """
    Utility: Masks Land, Cloud, and Saturation based on standard PACE L2 flags.
    """
    mask = (ds.l2_flags & (1<<1 | 1<<3 | 1<<5)) == 0
    return ds.where(mask)