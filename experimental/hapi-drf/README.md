# PSWS HAPI Digital RF Extension - W. Engelke, Sept. 2026

This directory contains the development version of an enhanced HAPI server
used by the Personal Space Weather Station (PSWS) Network.

The purpose of this work is to extend HAPI so that native Digital RF (DRF)
datasets can be downloaded in addition to conventional HAPI CSV data.

## Background

PSWS stores large quantities of digitized radio-frequency data using
Digital RF (DRF), a structured HDF5-based format.

A PSWS DRF Observation is approximately 24 hours of RF data. An Observation
is not a single HDF5 file; it is a directory tree containing Digital RF
channels, time directories, metadata, and HDF5 files.

Because the directory structure is part of the Digital RF dataset, a native
Observation must be packaged as a ZIP archive before being transferred.

## HAPI Dataset Model

A station's DRF holdings are represented by one logical HAPI dataset, for
example:

    S000116/drf

Individual daily Observations are NOT placed in the HAPI catalog. There are
more than 150,000 such Observations, so exposing each one as a separate HAPI
dataset would make the catalog impractical.

The HAPI start and stop times select the Observation or Observations to
retrieve.

## Standard HAPI Representation

A normal HAPI data request without a custom format returns a small CSV
manifest describing the matching Observation(s).

Example:

    /hapi/data?dataset=S000116/drf&start=2026-05-23T00:00:00Z&stop=2026-05-24T00:00:00Z

Example result:

    2026-05-23T00:00:00Z,OBS2026-05-23T00-00

## Native Digital RF Download

The custom HAPI output format is:

    x_drf_zip

Example:

    /hapi/data?dataset=S000116/drf&start=2026-05-23T00:00:00Z&stop=2026-05-24T00:00:00Z&format=x_drf_zip

The server:

1. Finds complete DRF Observations overlapping the requested time interval.
2. Preserves each Observation directory tree unchanged.
3. Creates a temporary ZIP archive.
4. Streams the ZIP through the HAPI `/data` endpoint.
5. Deletes the temporary server-side ZIP after transmission.

No server-side extraction of individual Digital RF subchannels is performed.
Users can select or process subchannels after downloading the native DRF
dataset.

## Repository Contents

This development area contains snapshots and modifications from two related
codebases:

    server-python-general/
        Generic Python HAPI server.

    server-python-general-psws/
        PSWS-specific HAPI provider.

    docs/
        Design notes, test procedures, and open questions.

    deploy/
        Development service configuration.

    patches/
        Patches used during development.

See `UPSTREAM_PROVENANCE.md` for the original repositories and commit
information.

## Development Status

This is experimental development code and is not yet intended for production
deployment.

Verified so far:

- PSWS `/drf` logical datasets
- DRF Observation discovery by requested time
- CSV Observation manifest
- Creation of valid native DRF ZIP archives
- `format=x_drf_zip` recognition
- `application/zip` HTTP response type
- `Content-Disposition` download filename

Work still being verified includes:

- End-to-end streaming of the complete ZIP through HAPI
- Large Observation downloads
- Magnetometer CSV regression tests
- Doppler CSV regression tests
- HAPI splash-page examples
- Final integration with the upstream HAPI server

## Development Branch

    feature/hapi-drf-native-download

EOF
