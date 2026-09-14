import hapiserver
import utilrsw.uvicorn

configs = hapiserver.cli()

utilrsw.uvicorn.run("hapiserver.app", configs)
