import uvicorn

from settings import settings
from tpdingding.app import app
from tpdingding.middleware.track import init_logger

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_config=init_logger(settings))
