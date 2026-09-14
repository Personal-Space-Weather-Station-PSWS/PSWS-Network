import os
import sys
import logging
import subprocess

logger = logging.getLogger(__name__)

def exec(script, args="", stream=None):
  if stream is not None:
    return _stream(script, args, stream=stream)
  else:
    # Note that if stream_stdout=False, stdout will not be streamed either,
    # even if stream_stderr=True.
    return _read(script, args)


def _read(script, args=""):

  if not os.path.exists(script):
    content = "Execution script not found"
    logger.error(f"{content}: {script}")
    return None, {"code": 1500, "message": content}

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": True,
    }
    result = subprocess.run(call, **kwargs)
    if result.stderr:
      print(f"Script stderr: \n{result.stderr}")
    return result.stdout, None
  except Exception as e:
    message = "Execution of script failed"
    error = {
      "code": 1500,
      "message": message,
      "message_console": str(getattr(e, "stderr", None)),
      "exception": e
    }
    return None, error


def _stream(script, args="", stream=None):

  if not os.path.exists(script):
    content = "Execution script not found"
    return None, {"code": 1500, "message": content}

  stream_stderr = stream.get('stderr', False)
  chunk_size = stream.get('chunk_size', 1000000)

  call = [sys.executable, script, *args.split()]
  logger.info(f"Executing: {' '.join(call)}")
  try:
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "bufsize": -1 if chunk_size > 0 else 1,
        "text": True,
    }
    proc = subprocess.Popen(call, **kwargs)
  except Exception as e:
    message = "Execution of script failed"
    error = {
      "code": 1500,
      "message": message,
      "message_console": str(getattr(e, "stderr", None)),
      "exception": e
    }
    return None, error

  def stream_output():

    if stream_stderr:
      import threading
      def _drain_stderr():
        for line in proc.stderr:
          print(f"Script stderr: {line.rstrip()}")
        proc.stderr.close()
      stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
      stderr_thread.start()

    try:
      if chunk_size > 0:
        # stream stdout lines or chunks as they arrive
        for chunk in iter(lambda: proc.stdout.read(chunk_size), ''):
          yield chunk
      else:
        for line in proc.stdout:
          yield line
      proc.stdout.close()

      if stream_stderr:
        # Print stderr lines as stdout is streamed
        stderr_thread.join()
      else:
        # Print stderr lines after stdout has been streamed
        for line in proc.stderr:
          print(f"Script stderr: {line.rstrip()}")
        proc.stderr.close()

      returncode = proc.wait()
      if returncode != 0:
        emsg = f"Script exited with code {returncode}"
        logger.error(emsg)
        yield emsg

    finally:
      if proc.poll() is None:
        proc.kill()

  return stream_output, None
