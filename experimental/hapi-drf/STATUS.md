As of Sept. 2026
Working:
- S000116/drf appears as a logical HAPI dataset
- Observation discovery works
- CSV manifest works
- Native DRF ZIP creation works locally
- x_drf_zip is accepted by the enhanced HAPI server
- application/zip response headers work
- Content-Disposition filename works

Still being tested:
- End-to-end ZIP byte streaming from data.py through HAPI to client
- Large archive behavior
- mag regression tests
- doppler regression tests
- splash-page DRF example
