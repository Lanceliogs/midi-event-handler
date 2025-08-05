import uvicorn
from argparse import ArgumentParser
from pathlib import Path
from midi_event_handler.core.config.loader import (
     RUNTIME_PATH, load_mapping_yaml
)
from midi_event_handler.core.config import get_logging_config
from midi_event_handler.web.app import app

import shutil
import builtins
import logging

is_compiled = '__compiled__' in globals()
log = logging.getLogger(__name__)

def run_app(host="127.0.0.1", port=8000, local=False, mapping=None, reload=False):
     if local:
          host = "127.0.0.1"
          port = 8000

     RUNTIME_PATH.mkdir(exist_ok=True)
     if mapping:
          log.info("Using mapping from CLI: %s", mapping)
          shutil.copy(mapping, RUNTIME_PATH / "mapping.yaml")
     
     # First mapping load
     try:
          load_mapping_yaml()
     except FileNotFoundError:
          log.exception("No mapping YAML file. First launch?")

     try:
          uvicorn.run(
                    app,
                    host=host,
                    port=port,
                    log_config=get_logging_config(),
                    reload=reload and not is_compiled
          )
     except SystemExit as e:
          log.info(f"Expected SystemExit: {e}")
     except:
          log.exception("Unhandled exception")


def main():
     parser = ArgumentParser(prog="meh-app")
     parser.add_argument("--host", type=str, default="0.0.0.0")
     parser.add_argument("--port", type=int, default=8000)
     parser.add_argument("--reload", action="store_true")
     parser.add_argument("--local", action="store_true", help="Short for host=127.0.0.1 and port=8000")
     parser.add_argument("--mapping", type=Path, help="Path to mapping.yaml")
     args = parser.parse_args()

     run_app(host=args.host, port=args.port,
             local=args.local, mapping=args.mapping,
             reload=args.reload)

if __name__ == "__main__":
     main()

