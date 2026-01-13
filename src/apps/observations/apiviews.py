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
from datetime import datetime
import tempfile, os, zipfile

from stations.models import Station
from observations.models import Observation

class ObservationDownloadAPIView(APIView):
    throttle_classes = [AnonRateThrottle]

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
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&instrument_id=1&start_date=2024-01-01&end_date=2024-01-31"

        WGET EXAMPLES:
        
        wget -O output.zip \
        "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?station_id=S000028&start_date=2024-01-01&end_date=2024-01-31"

        RESPONSE:
        - Single file: Returns the observation file directly
        - Multiple files: Returns a ZIP archive containing all matching observations
        - No matches: HTTP 404 with error message
        - Invalid parameters: HTTP 400 with error details
        '''
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

        # VALIDATION: Check required date parameters
        if not (start_date and end_date):
            return Response({"detail": "Missing start_date or end_date parameters"}, status=status.HTTP_400_BAD_REQUEST)

        # VALIDATION: Parse and validate date format (YYYY-MM-DD)
        # Example valid dates: "2024-01-01", "2024-12-31"
        # Example invalid dates: "01/01/2024", "2024-1-1", "24-01-01"
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"detail": "Dates must be in YYYY-MM-DD format"}, status=status.HTTP_400_BAD_REQUEST)

        # VALIDATION: Ensure logical date range
        if end_dt < start_dt:
            return Response({"detail": "End date must be after start date"}, status=status.HTTP_400_BAD_REQUEST)

        # INITIAL QUERY: Filter observations by date range
        # This filters on the observation's start and end dates
        observations_in_range = Observation.objects.filter(
            startDate__gte=start_dt,
            endDate__lte=end_dt
        )

        # VALIDATION: Ensure mutual exclusivity between station_id and lat/lon filtering
        # This prevents conflicting filter criteria that could lead to unexpected results
        if station_id and (lat_min or lat_max or lon_min or lon_max):
            return Response({"detail": "Invalid parameters: must choose either station_id or latitude and longitude range"})

        # STATION FILTERING: Filter by specific station ID (case-insensitive)
        # Example test case: station_id="S000028" should match station with ID "s000028" or "S000028"
        if station_id:
            observations_in_range = observations_in_range.filter(
                station__station_id__iexact=station_id
            )
        # GEOGRAPHIC FILTERING: Filter by latitude/longitude bounding box
        # All four coordinates must be provided for geographic filtering
        # Example test cases:
        # - lat_min=32.0, lat_max=34.0, lon_min=-87.0, lon_max=-85.0 (Alabama region)
        # - lat_min=25.0, lat_max=49.0, lon_min=-125.0, lon_max=-66.0 (Continental US)
        # - lat_min=40.0, lat_max=41.0, lon_min=-74.0, lon_max=-73.0 (NYC area)
        elif lat_min and lat_max and lon_min and lon_max:
            try:
                # Convert to float to ensure proper numeric comparison
                lat_min_f = float(lat_min)
                lat_max_f = float(lat_max)
                lon_min_f = float(lon_min)
                lon_max_f = float(lon_max)
                
                # VALIDATION: Check coordinate bounds and logical consistency
                # Latitude must be between -90 and 90 degrees
                if not (-90 <= lat_min_f <= 90 and -90 <= lat_max_f <= 90):
                    return Response({"detail": "Latitude values must be between -90 and 90 degrees"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Longitude must be between -180 and 180 degrees
                if not (-180 <= lon_min_f <= 180 and -180 <= lon_max_f <= 180):
                    return Response({"detail": "Longitude values must be between -180 and 180 degrees"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Min values must be less than or equal to max values
                if lat_min_f > lat_max_f:
                    return Response({"detail": "lat_min must be less than or equal to lat_max"}, status=status.HTTP_400_BAD_REQUEST)
                
                if lon_min_f > lon_max_f:
                    return Response({"detail": "lon_min must be less than or equal to lon_max"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Apply geographic filter using validated coordinates
                observations_in_range = observations_in_range.filter(
                    station__latitude__gte=lat_min_f,
                    station__latitude__lte=lat_max_f,
                    station__longitude__gte=lon_min_f,
                    station__longitude__lte=lon_max_f
                )
            except (ValueError, TypeError):
                return Response({"detail": "Latitude and longitude values must be valid numbers"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "Invalid parameters: must include either station_id or latitude and longitude range"}, status=status.HTTP_400_BAD_REQUEST)
        
        # INSTRUMENT FILTERING: Filter by specific instrument ID if provided
        # Example test case: instrument_id=1 should return only observations from instrument with ID 1
        if instrument_id:
            try:
                instrument_id_int = int(instrument_id)
                observations_in_range = observations_in_range.filter(
                    instrument__id=instrument_id_int
                )
            except (ValueError, TypeError):
                return Response({"detail": "instrument_id must be a valid integer"}, status=status.HTTP_400_BAD_REQUEST)
        
        # FREQUENCY FILTERING: Filter by center frequency if provided
        # Note: This filters on the centerFrequency field value in MHz
        if frequency:
            try:
                frequency_decimal = float(frequency)
                # Validate frequency range (assuming reasonable RF frequencies in MHz)
                if frequency_decimal <= 0 or frequency_decimal > 300000:  # 0 Hz to 300 GHz
                    return Response({"detail": "Frequency must be a positive value in MHz (0-300000)"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Filter observations by center frequency
                # Note: The relationship is observations -> centerFrequency (ManyToMany) -> centerFrequency field
                observations_in_range = observations_in_range.filter(
                    centerFrequency__centerFrequency=frequency_decimal
                )
            except (ValueError, TypeError):
                return Response({"detail": "Frequency must be a valid decimal number in MHz"}, status=status.HTTP_400_BAD_REQUEST)

        # CHECK RESULTS: Verify that observations were found
        if not observations_in_range.exists():
            return Response({"detail": "Observation data not found."}, status=status.HTTP_404_NOT_FOUND)

        # RETRIEVE MATCHING OBSERVATIONS
        observations = list(observations_in_range.all())

        print(f"Found {len(observations)} observations matching criteria")
        for i, obs in enumerate(observations):
            print(f"  Observation {i+1}: {obs.fileName} | Path: {obs.path} | Start: {obs.startDate.date()} | End: {obs.endDate.date()}")

        # MULTIPLE FILES: Create ZIP archive when multiple observations found
        if len(observations) > 1:
            temp_dir = tempfile.gettempdir()
            # Create descriptive filename based on search criteria
            if station_id:
                zip_filename = f"observations_{station_id}_{start_date}_{end_date}.zip"
            else:
                zip_filename = f"observations_region_{start_date}_{end_date}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            print(f"Creating ZIP archive: {zip_path}")
            
            files_added = 0
            files_processed = 0
            
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for obs in observations:
                        files_processed += 1
                        print(f"Processing observation {files_processed}/{len(observations)}: {obs.fileName}")
                        
                        # VALIDATION: Only process ZIP files within date range # Removed since file formats may change?
                        #file_extension = obs.fileName[-4:]
                        #if file_extension == '.zip':
                            
                            # CONSTRUCT FILE PATH: Build full path to observation file
                        file_path = '/'.join(obs.path.split('/')[:-1]) + '/' + obs.fileName
                            # TEST CASE - developer is linux username
                        #file_path = "/home/developer/S000028/magData/" + obs.fileName
                        print(f"  File path: {file_path}")
                            
                            # VALIDATION: Check file exists before adding to ZIP
                        if os.path.exists(file_path):
                            try:
                                zipf.write(file_path, arcname=obs.fileName)
                                files_added += 1
                                print(f"  ✓ Successfully added to ZIP")
                            except Exception as add_error:
                                print(f"  ✗ Error adding file to ZIP: {add_error}")
                        else:
                            print(f"  ✗ File not found at path")
                        #else:
                        #    print(f"  ✗ File skipped (invalid extension or date range)")
                            
            except Exception as e:
                print(f"Error creating ZIP file: {str(e)}")
                return Response({"detail": f"Failed to generate zip file: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            print(f"ZIP creation completed: {files_added}/{files_processed} files added to archive")
            
            # Check if any files were actually added
            if files_added == 0:
                return Response({"detail": "No valid observation files found to include in archive"},
                                status=status.HTTP_404_NOT_FOUND)

            # RETURN ZIP FILE: Send ZIP archive as download with custom headers
            response = FileResponse(open(zip_path, 'rb'),
                                as_attachment=True,
                                filename=zip_filename,
                                content_type="application/zip")
            
            # Add custom headers visible to user
            response['X-Files-Discovered'] = str(len(observations))
            response['X-Files-Processed'] = str(files_processed)
            response['X-Files-Added'] = str(files_added)
            response['X-Archive-Type'] = 'multiple-files'
            
            return response

        # SINGLE FILE: Return observation file directly
        else:
            obs = observations[0]
            #file_extension = obs.fileName[-4:]
            
            # VALIDATION: Check file is within date range and is a ZIP file # Removed since file formats may change?
            #if not file_extension == '.zip':
            #    return Response({"detail": "Observation file not found or invalid."},
            #                    status=status.HTTP_404_NOT_FOUND)

            # CONSTRUCT FILE PATH: Build full path to observation file
            file_path = '/'.join(obs.path.split('/')[:-1]) + '/' + obs.fileName
            # TEST CASE - developer is linux username
            #file_path = "/home/developer/S000028/magData/" + obs.fileName
            print(f"Serving single file: {file_path}")
            
            # VALIDATION: Verify file exists on filesystem
            if not os.path.exists(file_path):
                return Response({"detail": "Observation file not found on filesystem."},
                                status=status.HTTP_404_NOT_FOUND)
            
            # RETURN SINGLE FILE: Send observation file as download with custom headers
            response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True,
                                filename=obs.fileName,
                                content_type="application/zip")
            
            # Add custom headers visible to user
            response['X-Files-Discovered'] = '1'
            response['X-Files-Processed'] = '1'
            response['X-Files-Added'] = '1'
            response['X-Archive-Type'] = 'single-file'
            
            return response