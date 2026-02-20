# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status
from django.http import FileResponse
from datetime import datetime, timezone, timedelta
import tempfile, os, re, zipfile

from apps.stations.models import Station
from apps.observations.models import Observation

# Allowed base directories for observation files
ALLOWED_BASE_DIRS = [
    '/home',
]


def _validate_within_allowed_dirs(resolved_path):
    """Return True if *resolved_path* is inside one of ALLOWED_BASE_DIRS."""
    return any(
        resolved_path.startswith(os.path.realpath(base) + os.sep)
        for base in ALLOWED_BASE_DIRS
    )


def _safe_observation_path(obs):
    """
    Construct and validate a filesystem path from an observation record.

    Observation storage varies by data type:

      magData / csvData – obs.path is the directory that contains
      the file and obs.fileName is the actual file name.
      Disk location: <obs.path>/<obs.fileName>

    * spectrum (DRF) – obs.path is the observation directory
      (e.g. /home/S000028/OBS2024-01-01T00-00) and obs.fileName
      equals the directory's basename.  The observation is the whole
      directory tree, not a single file.

    Returns a (resolved_path, is_directory) tuple when the path is
    valid and within ALLOWED_BASE_DIRS, or (None, False) on failure.
    """
    try:
        # Spectrum / DRF observations: path IS the directory, fileName
        # matches the directory name.  Check for this pattern first.
        resolved_dir = os.path.realpath(obs.path)
        if (
            os.path.isdir(resolved_dir)
            and os.path.basename(resolved_dir) == obs.fileName
        ):
            if _validate_within_allowed_dirs(resolved_dir):
                return resolved_dir, True
            writeLog(
                f"PATH VALIDATION FAILED (directory) for observation {obs.id}: "
                f"{resolved_dir} is outside allowed directories"
            )
            return None, False

        # magData / csvData: path is the parent directory, fileName is
        # the actual file.  Construct: <obs.path>/<obs.fileName>
        raw_path = os.path.join(obs.path, obs.fileName)
        resolved = os.path.realpath(raw_path)
        if _validate_within_allowed_dirs(resolved):
            return resolved, False

    except (TypeError, AttributeError):
        pass

    writeLog(
        f"PATH VALIDATION FAILED for observation {obs.id}: "
        f"attempted path outside allowed directories"
    )
    return None, False

def writeLog(theMessage):
    timestamp = datetime.now(timezone.utc).isoformat()[0:19]
    #log_dir = '/var/log/api'
    #os.makedirs(log_dir, exist_ok=True)
    f = open("/srv/PSWS-Network/logs/observations_api.log", "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()


def _dir_size(path):
    """Return the total size in bytes of all files under path (recursive)."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


def _add_directory_to_zip(zipf, dir_path, arc_prefix):
    """
    Recursively add every file inside dir_path to the open ZipFile
    zipf, storing them under arc_prefix/ inside the archive.
    Returns the number of files added.
    """
    count = 0
    for dirpath, _dirnames, filenames in os.walk(dir_path):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            arcname = os.path.join(arc_prefix, os.path.relpath(full, dir_path))
            zipf.write(full, arcname=arcname)
            count += 1
    return count


def _zip_directory_to_tempfile(dir_path, arc_prefix):
    """
    Create a temporary ZIP of the directory at dir_path.
    Returns the path to the temporary ZIP file.
    The caller is responsible for cleaning up t      he temp file.
    """
    tmpf = tempfile.NamedTemporaryFile(
        prefix="obs_dir_", suffix=".zip", delete=False
    )
    zip_path = tmpf.name
    tmpf.close()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        _add_directory_to_zip(zipf, dir_path, arc_prefix)
    return zip_path

class ObservationDownloadAPIView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    # Size threshold for multiple file downloads (in bytes)
    MAX_MULTI_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

    def get(self, request, format=None):
        '''
        Download observations API endpoint with filtering capabilities.
        
        AUTHENTICATION: No authentication required - publicly accessible with rate limiting
        
        REQUIRED PARAMETERS:
        - start_date: YYYY-MM-DD format (e.g. "2024-01-01")
        - end_date: YYYY-MM-DD format (e.g. "2024-12-31")
        
        LOCATION FILTERING (choose one):
        - station_id: Specific station identifier (e.g. "S000028")
        OR
        - lat_min, lat_max, lon_min, lon_max: Geographic bounding box
        
        OPTIONAL FILTERS:
        - instrument_id: Filter by specific instrument (integer)
        - frequency: Filter by center frequency in MHz (decimal)
        
        EXAMPLE CURL COMMANDS:
        
        1. Download by station ID:
        curl -o output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&start_date=2024-01-01&end_date=2024-01-31"
        
        2. Download by geographic region (Alabama):
        curl -o output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?lat_min=32.0&lat_max=35.0&lon_min=-88.0&lon_max=-84.0&start_date=2024-01-01&end_date=2024-01-31"
        
        3. Download with frequency filter:
        curl -o output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&frequency=10&start_date=2024-01-01&end_date=2024-01-31"

        4. Download with instrument filter:
        curl -o output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&instrument_id=31&start_date=2024-01-01&end_date=2024-01-31"

        WGET EXAMPLES:
        
        wget -O output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&start_date=2024-01-01&end_date=2024-01-31"

        RESPONSE:
        - Single file: Returns the observation file directly
        - Multiple files: Returns a ZIP archive containing all matching observations
        - No matches: HTTP 404 with error message
        - Invalid parameters: HTTP 400 with error details
        '''
        # Log incoming request
        writeLog("="*80)
        writeLog("NEW API REQUEST RECEIVED")
        writeLog(f"Client IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        writeLog(f"User Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
        writeLog(f"Query Parameters: {dict(request.query_params)}")
        
        # REQUIRED PARAMETERS: Extract and validate date range
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # LOCATION PARAMETERS: Extract station ID or geographic coordinates
        station_id = request.query_params.get("station_id")  # Single station filter
        
        # Geographic bounding box coordinates (all four required for geo filtering)
        lat_min = request.query_params.get("lat_min")
        lat_max = request.query_params.get("lat_max") 
        lon_min = request.query_params.get("lon_min")
        lon_max = request.query_params.get("lon_max")

        # OPTIONAL FILTER PARAMETERS
        instrument_id = request.query_params.get("instrument_id")
        frequency = request.query_params.get("frequency")

        writeLog(f"Extracted parameters - start_date: {start_date}, end_date: {end_date}, "
                        f"station_id: {station_id}, lat_min: {lat_min}, lat_max: {lat_max}, "
                        f"lon_min: {lon_min}, lon_max: {lon_max}, instrument_id: {instrument_id}, "
                        f"frequency: {frequency}")

        # VALIDATION: Check required date parameters
        if not (start_date and end_date):
            writeLog("VALIDATION FAILED: Missing start_date or end_date parameters")
            return Response({"detail": "Missing start_date or end_date parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # VALIDATION: Parse and validate date format (YYYY-MM-DD)
        # Example valid dates: "2024-01-01", "2024-12-31"
        # Example invalid dates: "01/01/2024", "2024-1-1", "24-01-01"
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            writeLog(f"Date parsing successful - start_dt: {start_dt}, end_dt: {end_dt}")
        except ValueError as e:
            writeLog(f"VALIDATION FAILED: Invalid date format - {e}")
            return Response({"detail": "Dates must be in YYYY-MM-DD format"}, status=status.HTTP_400_BAD_REQUEST)

        # VALIDATION: Ensure logical date range
        if end_dt < start_dt:
            writeLog(f"VALIDATION FAILED: End date {end_dt} is before start date {start_dt}")
            return Response({"detail": "End date must be after start date"}, status=status.HTTP_400_BAD_REQUEST)

        # INITIAL QUERY: Filter observations by date range
        # The user supplies calendar dates (YYYY-MM-DD) which parse to midnight
        # (00:00:00).  Observation endDate values are typically set to end-of-day
        # (e.g. 23:59).  Push end_dt to the very end of the requested day so
        # that "start_date=2024-01-01&end_date=2024-01-01" captures the full day.
        end_dt_inclusive = end_dt + timedelta(days=1, microseconds=-1)
        writeLog(f"Querying observations between {start_dt} and {end_dt_inclusive}")
        observations_in_range = Observation.objects.filter(
            startDate__gte=start_dt,
            endDate__lte=end_dt_inclusive
        )
        writeLog(f"Initial date range query returned {observations_in_range.count()} observations")

        # VALIDATION: Ensure mutual exclusivity between station_id and lat/lon filtering
        # This prevents conflicting filter criteria that could lead to unexpected results
        if station_id and (lat_min or lat_max or lon_min or lon_max):
            writeLog("VALIDATION FAILED: Both station_id and lat/lon parameters provided")
            return Response({"detail": "Invalid parameters: must choose either station_id or latitude and longitude range"}, status=status.HTTP_400_BAD_REQUEST)

        # STATION FILTERING: Filter by specific station ID (case-insensitive)
        # Example test case: station_id="S000028" should match station with ID "s000028" or "S000028"
        if station_id:
            writeLog(f"Applying station filter: {station_id}")
            observations_in_range = observations_in_range.filter(
                station__station_id__iexact=station_id
            )
            writeLog(f"After station filter: {observations_in_range.count()} observations")
            
            # Check if station exists
            if not observations_in_range.exists():
                # Verify if the station exists at all
                station_exists = Station.objects.filter(station_id__iexact=station_id).exists()
                if not station_exists:
                    writeLog(f"Station '{station_id}' not found in database")
                else:
                    writeLog(f"Station '{station_id}' exists but has no observations in date range")
        # GEOGRAPHIC FILTERING: Filter by latitude/longitude bounding box
        # All four coordinates must be provided for geographic filtering
        # Example test cases:
        # - lat_min=32.0, lat_max=34.0, lon_min=-87.0, lon_max=-85.0 (Alabama region)
        # - lat_min=25.0, lat_max=49.0, lon_min=-125.0, lon_max=-66.0 (Continental US)
        # - lat_min=40.0, lat_max=41.0, lon_min=-74.0, lon_max=-73.0 (NYC area)
        elif lat_min and lat_max and lon_min and lon_max:
            writeLog(f"Applying geographic filter: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
            try:
                # Convert to float to ensure proper numeric comparison
                lat_min_f = float(lat_min)
                lat_max_f = float(lat_max)
                lon_min_f = float(lon_min)
                lon_max_f = float(lon_max)
                
                writeLog(f"Parsed geographic coordinates: lat [{lat_min_f}, {lat_max_f}], lon [{lon_min_f}, {lon_max_f}]")
                
                # VALIDATION: Check coordinate bounds and logical consistency
                # Latitude must be between -90 and 90 degrees
                if not (-90 <= lat_min_f <= 90 and -90 <= lat_max_f <= 90):
                    writeLog(f"VALIDATION FAILED: Latitude values out of bounds - lat_min: {lat_min_f}, lat_max: {lat_max_f}")
                    return Response({"detail": "Latitude values must be between -90 and 90 degrees"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Longitude must be between -180 and 180 degrees
                if not (-180 <= lon_min_f <= 180 and -180 <= lon_max_f <= 180):
                    writeLog(f"VALIDATION FAILED: Longitude values out of bounds - lon_min: {lon_min_f}, lon_max: {lon_max_f}")
                    return Response({"detail": "Longitude values must be between -180 and 180 degrees"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Min values must be less than or equal to max values
                if lat_min_f > lat_max_f:
                    writeLog(f"VALIDATION FAILED: lat_min ({lat_min_f}) > lat_max ({lat_max_f})")
                    return Response({"detail": "lat_min must be less than or equal to lat_max"}, status=status.HTTP_400_BAD_REQUEST)
                
                if lon_min_f > lon_max_f:
                    writeLog(f"VALIDATION FAILED: lon_min ({lon_min_f}) > lon_max ({lon_max_f})")
                    return Response({"detail": "lon_min must be less than or equal to lon_max"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Apply geographic filter using validated coordinates
                observations_in_range = observations_in_range.filter(
                    station__latitude__gte=lat_min_f,
                    station__latitude__lte=lat_max_f,
                    station__longitude__gte=lon_min_f,
                    station__longitude__lte=lon_max_f
                )
                writeLog(f"After geographic filter: {observations_in_range.count()} observations")
            except (ValueError, TypeError) as e:
                writeLog(f"VALIDATION FAILED: Invalid lat/lon values - {e}")
                return Response({"detail": "Latitude and longitude values must be valid numbers"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            writeLog("VALIDATION FAILED: No valid location filter provided (neither station_id nor complete lat/lon range)")
            return Response({"detail": "Invalid parameters: must include either station_id or latitude and longitude range"}, status=status.HTTP_400_BAD_REQUEST)
        
        # INSTRUMENT FILTERING: Filter by specific instrument ID if provided
        # Example test case: instrument_id=1 should return only observations from instrument with ID 1
        if instrument_id:
            writeLog(f"Applying instrument filter: {instrument_id}")
            try:
                instrument_id_int = int(instrument_id)
                observations_in_range = observations_in_range.filter(
                    instrument__id=instrument_id_int
                )
                writeLog(f"After instrument filter: {observations_in_range.count()} observations")
            except (ValueError, TypeError) as e:
                writeLog(f"VALIDATION FAILED: Invalid instrument_id - {e}")
                return Response({"detail": "instrument_id must be a valid integer"}, status=status.HTTP_400_BAD_REQUEST)
        
        # FREQUENCY FILTERING: Filter by center frequency if provided
        # Note: This filters on the centerFrequency field value in MHz
        if frequency:
            writeLog(f"Applying frequency filter: {frequency} MHz")
            try:
                frequency_decimal = float(frequency)
                # Validate frequency range (assuming reasonable RF frequencies in MHz)
                if frequency_decimal <= 0 or frequency_decimal > 99.999:  # >0 Hz to  <=99.999 MHz
                    writeLog(f"VALIDATION FAILED: Frequency out of range - {frequency_decimal} MHz")
                    return Response({"detail": "Frequency must be a positive value in MHz (0-99.999)"}, status=status.HTTP_400_BAD_REQUEST)

                # Filter observations by center frequency
                # Note: The relationship is observations -> centerFrequency (ManyToMany) -> centerFrequency field
                observations_in_range = observations_in_range.filter(
                    centerFrequency__centerFrequency=frequency_decimal
                )
                writeLog(f"After frequency filter: {observations_in_range.count()} observations")
            except (ValueError, TypeError) as e:
                writeLog(f"VALIDATION FAILED: Invalid frequency value - {e}")
                return Response({"detail": "Frequency must be a valid decimal number in MHz"}, status=status.HTTP_400_BAD_REQUEST)

        # CHECK RESULTS: Verify that observations were found
        if not observations_in_range.exists():
            writeLog("NO OBSERVATIONS FOUND matching the specified criteria")
            return Response({"detail": "Observation data not found."}, status=status.HTTP_404_NOT_FOUND)

        # RETRIEVE MATCHING OBSERVATIONS
        observations = list(observations_in_range.all())

        writeLog(f"FOUND {len(observations)} observations matching criteria")
        print(f"Found {len(observations)} observations matching criteria")
        for i, obs in enumerate(observations):
            log_msg = f"  Observation {i+1}: {obs.fileName} | Path: {obs.path} | Start: {obs.startDate.date()} | End: {obs.endDate.date()}"
            writeLog(log_msg)
            print(log_msg)

        # SIZE VALIDATION: Check total size for multiple files
        if len(observations) > 1:
            writeLog(f"Multiple files detected ({len(observations)}), checking total size...")
            total_size = 0
            existing_files_count = 0
            
            print(f"Checking total size (threshold: {self.MAX_MULTI_FILE_SIZE / (1024*1024):.0f} MB)...")
            
            for obs in observations:
                # Use database size if available, otherwise check file on disk
                file_size = 0
                
                if hasattr(obs, 'size') and obs.size:
                    file_size = obs.size
                    log_msg = f"  {obs.fileName}: {file_size / (1024*1024):.2f} MB (from database)"
                    writeLog(log_msg)
                    print(log_msg)
                else:
                    # Construct file path to check on disk (with path traversal protection)
                    file_path, is_dir = _safe_observation_path(obs)
                    if file_path is None:
                        log_msg = f"  {obs.fileName}: Path validation failed, skipping from size calculation"
                        writeLog(log_msg)
                        print(log_msg)
                        continue
                    if is_dir:
                        if os.path.isdir(file_path):
                            file_size = _dir_size(file_path)
                            log_msg = f"  {obs.fileName}: {file_size / (1024*1024):.2f} MB (directory, from disk)"
                            writeLog(log_msg)
                            print(log_msg)
                        else:
                            log_msg = f"  {obs.fileName}: Directory not found at {file_path}, skipping from size calculation"
                            writeLog(log_msg)
                            print(log_msg)
                            continue
                    elif os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        log_msg = f"  {obs.fileName}: {file_size / (1024*1024):.2f} MB (from disk)"
                        writeLog(log_msg)
                        print(log_msg)
                    else:
                        log_msg = f"  {obs.fileName}: File not found at {file_path}, skipping from size calculation"
                        writeLog(log_msg)
                        print(log_msg)
                        continue
                
                total_size += file_size
                existing_files_count += 1
            
            log_msg = f"Total size of {existing_files_count} existing files: {total_size / (1024*1024):.2f} MB"
            writeLog(log_msg)
            print(log_msg)
            
            # Check if total size exceeds threshold
            if total_size > self.MAX_MULTI_FILE_SIZE:
                writeLog(f"SIZE LIMIT EXCEEDED: {total_size / (1024*1024):.2f} MB > {self.MAX_MULTI_FILE_SIZE / (1024*1024):.0f} MB")
                return Response({
                    "detail": "Request exceeds maximum file size limit for multiple file downloads.",
                    "error_info": {
                        "requested_size_mb": round(total_size / (1024*1024), 2),
                        "threshold_mb": round(self.MAX_MULTI_FILE_SIZE / (1024*1024), 0),
                        "files_count": existing_files_count,
                        "suggestion": "Please use a smaller date range or download individual files."
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        # MULTIPLE FILES: Create ZIP archive when multiple observations found
        if len(observations) > 1:
            writeLog("Creating ZIP archive for multiple files")
            temp_dir = tempfile.gettempdir()
            # Create descriptive filename based on search criteria (sanitize user inputs)
            safe_station = re.sub(r'[^\w\-]', '', station_id) if station_id else None
            safe_start = re.sub(r'[^\w\-]', '', start_date)
            safe_end = re.sub(r'[^\w\-]', '', end_date)
            if safe_station:
                zip_filename = f"observations_{safe_station}_{safe_start}_{safe_end}.zip"
            else:
                zip_filename = f"observations_region_{safe_start}_{safe_end}.zip"
            # Create a unique temp file for the zip to avoid permission/overwrite issues
            tmpf = tempfile.NamedTemporaryFile(prefix="observations_", suffix=".zip", dir=temp_dir, delete=False)
            zip_path = tmpf.name
            tmpf.close()
            log_msg = f"Creating ZIP archive: {zip_path}"
            writeLog(log_msg)
            print(log_msg)
            
            files_added = 0
            files_processed = 0
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for obs in observations:
                        files_processed += 1
                        log_msg = f"Processing observation {files_processed}/{len(observations)}: {obs.fileName}"
                        writeLog(log_msg)
                        print(log_msg)
                        
                        # CONSTRUCT FILE PATH: Build full path to observation file (with path traversal protection)
                        file_path, is_dir = _safe_observation_path(obs)
                        if file_path is None:
                            log_msg = f"  ✗ Path validation failed for {obs.fileName}"
                            writeLog(log_msg)
                            print(log_msg)
                            continue
                        # TEST CASE - developer is linux username
                        #file_path = "/home/developer/S000028/magData/" + obs.fileName
                        log_msg = f"  File path: {file_path} ({'directory' if is_dir else 'file'})"
                        writeLog(log_msg)
                        print(log_msg)

                        if is_dir:
                            # Spectrum / DRF observation: zip directory contents into archive
                            if os.path.isdir(file_path):
                                try:
                                    added = _add_directory_to_zip(zipf, file_path, obs.fileName)
                                    files_added += 1
                                    log_msg = f"  ✓ Added directory ({added} files inside) to ZIP as {obs.fileName}/"
                                    writeLog(log_msg)
                                    print(log_msg)
                                except Exception as add_error:
                                    log_msg = f"  ✗ Error adding directory to ZIP: {add_error}"
                                    writeLog(log_msg)
                                    print(log_msg)
                            else:
                                log_msg = f"  ✗ Directory not found at path"
                                writeLog(log_msg)
                                print(log_msg)
                        else:
                            # Regular file (magData zip, csvData, etc.)
                            if os.path.exists(file_path):
                                # Try opening the file first to surface permission errors early
                                try:
                                    with open(file_path, 'rb') as ftest:
                                        # If open succeeds, add to zip
                                        zipf.write(file_path, arcname=obs.fileName)
                                        files_added += 1
                                        log_msg = f"  ✓ Successfully added to ZIP"
                                        writeLog(log_msg)
                                        print(log_msg)
                                except Exception as add_error:
                                    log_msg = f"  ✗ Error adding file to ZIP: {add_error}"
                                    writeLog(log_msg)
                                    print(log_msg)
                            else:
                                log_msg = f"  ✗ File not found at path"
                                writeLog(log_msg)
                                print(log_msg)
                            
            except Exception as e:
                log_msg = f"CRITICAL ERROR creating ZIP file: {str(e)}"
                writeLog(log_msg)
                print(log_msg)
                return Response({"detail": f"Failed to generate zip file"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            log_msg = f"ZIP creation completed: {files_added}/{files_processed} files added to archive"
            writeLog(log_msg)
            print(log_msg)
            
            # Check if any files were actually added
            if files_added == 0:
                writeLog("NO FILES ADDED to ZIP archive - all files missing from filesystem or unreadable")
                # Clean up the temp zip file if created
                try:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                except Exception:
                    pass
                return Response({"detail": "No valid observation files found to include in archive"},
                                status=status.HTTP_404_NOT_FOUND)

            # RETURN ZIP FILE: Send ZIP archive as download with custom headers
            writeLog(f"Successfully returning ZIP archive with {files_added} files")
            try:
                zip_handle = open(zip_path, 'rb')
            except Exception as open_zip_err:
                writeLog(f"ERROR: Unable to open generated zip for reading: {open_zip_err}")
                return Response({"detail": "Failed to read generated zip file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            response = FileResponse(zip_handle,
                                as_attachment=True,
                                filename=zip_filename,
                                content_type="application/zip")
            
            # Add custom headers visible to user
            response['X-Files-Discovered'] = str(len(observations))
            response['X-Files-Processed'] = str(files_processed)
            response['X-Files-Added'] = str(files_added)
            response['X-Archive-Type'] = 'multiple-files'
            
            writeLog("Request completed successfully - ZIP file sent")
            writeLog("="*80)
            return response

        # SINGLE FILE: Return observation file directly
        else:
            writeLog("Single file response - processing")
            obs = observations[0]
            
            # CONSTRUCT FILE PATH: Build full path to observation file (with path traversal protection)
            file_path, is_dir = _safe_observation_path(obs)
            if file_path is None:
                writeLog(f"PATH VALIDATION FAILED for single file: {obs.fileName}")
                return Response({"detail": "Observation file path is invalid."},
                                status=status.HTTP_400_BAD_REQUEST)
            # TEST CASE - developer is linux username
            #file_path = "/home/developer/S000028/magData/" + obs.fileName
            log_msg = f"Serving single observation: {file_path} ({'directory' if is_dir else 'file'})"
            writeLog(log_msg)
            print(log_msg)

            if is_dir:
                # Spectrum / DRF observation directory — zip on-the-fly and return
                if not os.path.isdir(file_path):
                    writeLog(f"DIRECTORY NOT FOUND on filesystem: {file_path}")
                    return Response({"detail": "Observation directory not found on filesystem."},
                                    status=status.HTTP_404_NOT_FOUND)
                try:
                    zip_tmp = _zip_directory_to_tempfile(file_path, obs.fileName)
                except Exception as zip_err:
                    writeLog(f"ERROR: Failed to zip observation directory: {zip_err}")
                    return Response({"detail": "Failed to create zip from observation directory."},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                download_name = obs.fileName + ".zip"
                writeLog(f"Successfully zipped directory, returning as {download_name}")
                try:
                    zip_handle = open(zip_tmp, 'rb')
                except Exception as fh_err:
                    writeLog(f"ERROR: Unable to open zipped directory for reading: {fh_err}")
                    return Response({"detail": "Permission denied reading generated zip."},
                                    status=status.HTTP_403_FORBIDDEN)
                response = FileResponse(zip_handle,
                                    as_attachment=True,
                                    filename=download_name,
                                    content_type="application/zip")
                response['X-Files-Discovered'] = '1'
                response['X-Files-Processed'] = '1'
                response['X-Files-Added'] = '1'
                response['X-Archive-Type'] = 'single-directory-zipped'

                writeLog("Request completed successfully - directory zipped and sent")
                writeLog("="*80)
                return response

            # Regular file (magData zip, csvData, etc.)
            if not os.path.exists(file_path):
                writeLog(f"FILE NOT FOUND on filesystem: {file_path}")
                return Response({"detail": "Observation file not found on filesystem."},
                                status=status.HTTP_404_NOT_FOUND)
            
            # RETURN SINGLE FILE: Send observation file as download with custom headers
            try:
                file_handle = open(file_path, 'rb')
            except Exception as fh_err:
                writeLog(f"ERROR: Unable to open observation file for reading: {fh_err}")
                return Response({"detail": "Permission denied reading the observation file."}, status=status.HTTP_403_FORBIDDEN)

            writeLog(f"Successfully returning single file: {obs.fileName}")
            response = FileResponse(file_handle,
                                as_attachment=True,
                                filename=obs.fileName,
                                content_type="application/zip")
            
            # Add custom headers visible to user
            response['X-Files-Discovered'] = '1'
            response['X-Files-Processed'] = '1'
            response['X-Files-Added'] = '1'
            response['X-Archive-Type'] = 'single-file'
            
            writeLog("Request completed successfully - single file sent")
            writeLog("="*80)
            return response