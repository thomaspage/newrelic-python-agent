import os
import pytest
import time
import socket
from newrelic.packages import requests
from testing_support.fixtures import TerminatingPopen

pytest.importorskip('aiohttp')


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_gunicorn_gaiohttp_worker(nr_enabled):

    nr_admin = os.path.join(os.environ['TOX_ENVDIR'], 'bin', 'newrelic-admin')
    gunicorn = os.path.join(os.environ['TOX_ENVDIR'], 'bin', 'gunicorn')
    cmd = [nr_admin, 'run-program', gunicorn, '-b', '127.0.0.1:8000', '-k',
            'gaiohttp', 'app:application']

    env = {
        'NEW_RELIC_ENABLED': 'true',
        'NEW_RELIC_HOST': 'staging-collector.newrelic.com',
        'NEW_RELIC_LICENSE_KEY': '84325f47e9dec80613e262be4236088a9983d501',
        'NEW_RELIC_APP_NAME': 'Python Agent Test (gunicorn)',
        'NEW_RELIC_LOG': 'stderr',
        'NEW_RELIC_LOG_LEVEL': 'debug',
        'NEW_RELIC_STARTUP_TIMEOUT': '10.0',
        'NEW_RELIC_SHUTDOWN_TIMEOUT': '10.0',
    }

    with TerminatingPopen(cmd, env=env):
        for _ in range(10):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('127.0.0.1', 8000))
                break
            except socket.error:
                pass

            time.sleep(0.1)
        else:
            assert False, "Server never started"

        resp = requests.get('http://127.0.0.1:8000')
        assert resp.status_code == 200
        assert resp.text == 'PONG'
