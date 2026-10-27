import sys
import os

# Make sure webapp/ is importable
sys.path.insert(0, os.path.dirname(__file__))

from webapp.app import app, socketio

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)
