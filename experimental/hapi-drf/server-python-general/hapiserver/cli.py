def cli(config=None):
  import argparse

  # Define the text for the header
  description = """
  HAPI Server
  -----------
  Example usage:
    python hapiserver.py --config CONFIG_FILE.json

  Pass additional Uvicorn arguments as needed
    python hapiserver.py --config CONFIG_FILE.json [Uvicorn options]
  For Uvicorn options, see:
    python -m uvicorn --help
  """

  import utilrsw.uvicorn

  # Get default server clargs from utilrsw.uvicorn
  clargs_uvicorn = utilrsw.uvicorn.cli()


  config_help = "Path to JSON configuration file. Relative paths in configuration"
  config_help += "file are interpreted as relative to the directory "
  config_help += "hapiserver.py is executed from."

  clargs = {
    "config": {
      "help": config_help,
      "type": str,
      "required": True
    },
    **clargs_uvicorn,
    "debug": {
      "help": "Verbose logging.",
      "action": "store_true",
      "default": False
    },
    "log-level": {
      "help": "Set the logging level. Overrides debug flag if set.",
      "type": str,
      "default": None
    }
  }

  if config is not None:
    clargs['config']['default'] = config
    clargs['config']['required'] = False

  parser_kwargs = {
    "description": description,
    "formatter_class": argparse.RawDescriptionHelpFormatter
  }

  parser = argparse.ArgumentParser()
  parser = argparse.ArgumentParser(**parser_kwargs)

  for k, v in clargs.items():
    parser.add_argument(f'--{k}', **v)

  configs = utilrsw.uvicorn.cli(parser=parser)

  return configs
