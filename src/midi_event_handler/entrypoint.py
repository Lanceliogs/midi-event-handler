import uvicorn
from argparse import ArgumentParser
from pathlib import Path
from midi_event_handler.core.config.loader import (
     RUNTIME_PATH, load_mapping_yaml
)
from midi_event_handler.tools import logtools
import shutil

log = logtools.get_logger(__name__)

def main():
     parser = ArgumentParser(prog="meh-app")
     parser.add_argument("--host", type=str, default="0.0.0.0")
     parser.add_argument("--port", type=int, default=8000)
     parser.add_argument("--reload", action="store_true")
     parser.add_argument("--local", action="store_true", help="Short for host=127.0.0.1 and port=8000")
     parser.add_argument("--mapping", type=Path, help="Path to mapping.yaml")

     args = parser.parse_args()
     host = args.host if not args.local else "127.0.0.1"
     port = args.port if not args.local else 8000

     RUNTIME_PATH.mkdir(exist_ok=True)
     if args.mapping:
          log.info("Using mapping from CLI: %s", args.mapping)
          shutil.copy(args.mapping, RUNTIME_PATH / "mapping.yaml")

     uvicorn.run(
          "midi_event_handler.web.app:app",
          host=host,
          port=port,
          log_config="logging_configs/config.yaml",
          reload=args.reload
     )
    
if __name__ == "__main__":
     main()
