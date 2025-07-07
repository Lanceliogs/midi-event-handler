import uvicorn

def main():
     uvicorn.run(
          "midi_event_handler.web.app:app",
          host="0.0.0.0",
          port=8000,
          log_config="logging_configs/config.yaml",
          reload=True
     )
    