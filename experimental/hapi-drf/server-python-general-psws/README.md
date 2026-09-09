# Usage

```
conda deactivate
conda env remove -y -n psws-python-3.11
conda create -y -n psws-python-3.11 python=3.11
conda activate psws-python-3.11
```

Install `server-python-general`

```
git clone https://github.com/rweigel/server-python-general
cd server-python-general
pip install -e .
```

Install `server-python-general-psws` plug-in
```
cd ../
git clone https://github.com/rweigel/server-python-general-psws
```

Test the plug-in

```
pip install requests pandas
cd server-python-general-psws
python test.py --config config.json
```

Start the PSWS server

```
cd server-python-general-psws
hapiserver --config config.json
```

For additional command-line options, see

```
hapiserver --help
```

# Development

Assumes magnetometer data in directories as under `data/` - each subdir corresponds to data from a station with ID in `catalog.csv`.

The responses to HAPI endpoints are implemented as Python scripts that return the response to `stdout`.

Return response to `/hapi/catalog` request

```
python bin/catalog.py
```

Return response to `/hapi/info` request

```
python bin/info.py S000028
```

Return response to `/hapi/data` request

```
python bin/data.py W2NAF 2025-10-20 2025-10-21
```
