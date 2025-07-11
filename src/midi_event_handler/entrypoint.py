import uvicorn
from argparse import ArgumentParser

def main():
     parser = ArgumentParser(prog="meh-app")
     parser.add_argument("--host", type=str, default="0.0.0.0")
     parser.add_argument("--port", type=int, default=8000)
     parser.add_argument("--reload", action="store_true")
     parser.add_argument("--local", action="store_true", help="Short for host=127.0.0.1 and port=8000")

     args = parser.parse_args()
     host = args.host if not args.local else "127.0.0.1"
     port = args.port if not args.local else 8000

     uvicorn.run(
          "midi_event_handler.web.app:app",
          host=host,
          port=port,
          log_config="logging_configs/config.yaml",
          reload=args.reload
     )
    
if __name__ == "__main__":
     main()
