# app_builder/utils/server_restart.py

import os
import sys
import signal
import time
import subprocess
from django.conf import settings


class ServerRestartManager:
    """
    Manages server restart after app creation.
    """

    @staticmethod
    def restart_server():
        """
        Restart the Django development server gracefully.
        """
        # For development server
        if 'runserver' in sys.argv:
            # Send SIGTERM to current process group
            os.kill(os.getpgrp(), signal.SIGTERM)
            time.sleep(1)

            # Start new server
            subprocess.Popen(
                [sys.executable] + sys.argv,
                start_new_session=True
            )

        # For production servers (gunicorn, uwsgi, etc.)
        # You would need to implement specific restart logic
        # based on your production setup

    @staticmethod
    def check_server_health(max_attempts=30, delay=2):
        """
        Check if server is responsive after restart.
        """
        import requests

        health_url = f"http://localhost:8000/admin/"  # Adjust as needed

        for attempt in range(max_attempts):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code < 500:
                    return True
            except:
                pass

            time.sleep(delay)

        return False