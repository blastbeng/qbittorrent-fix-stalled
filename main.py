import logging
import os
import random
import requests
import shutil
import sys
import utils
import autoremovetorrents

from dotenv import load_dotenv
from flask import Flask
from flask import Response
from flask import make_response
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from flask_restx import Resource
from flask_restx import reqparse
from os.path import dirname
from os.path import join
from pathlib import Path
from threading import Thread, Timer
from flask_apscheduler import APScheduler

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


host=os.environ.get("HOST")
port=int(os.environ.get("PORT"))
username=os.environ.get("USER")
password=os.environ.get("PASS")
seconds_inactive=int(os.environ.get("SECONDS_INACTIVE"))
autoremove_loop_minutes=int(os.environ.get("AUTOREMOVE_LOOP_MINUTES"))

sonarr_port=int(os.environ.get("SONARR_PORT"))
sonarr_token=os.environ.get("SONARR_TOKEN")
sonarr_search_loop_minutes=int(os.environ.get("SONARR_SEARCH_LOOP_MINUTES"))
radarr_port=int(os.environ.get("RADARR_PORT"))
radarr_token=os.environ.get("RADARR_TOKEN")
radarr_search_loop_minutes=int(os.environ.get("RADARR_SEARCH_LOOP_MINUTES"))

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
        
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

def create_app():
    app = Flask(__name__)
    def run_on_start(*args, **argv):
      Timer(120, utils.search_all, args=(host, sonarr_port, sonarr_token, "sonarr")).start()
      Timer(180, utils.search_all, args=(host, radarr_port, radarr_token, "radarr")).start()
    run_on_start()
    return app

app = create_app()
class Config:    
    SCHEDULER_API_ENABLED = True

scheduler = APScheduler()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["30/minute"],
    storage_uri="memory://",
)

app.config.from_object(Config())
api = Api(app)

nsutils = api.namespace('utils', 'qbittorrent fix stalled')

@limiter.limit("1/second")
@nsutils.route('/healthcheck')
class Healthcheck(Resource):
  def get (self):
    return "OK"

@limiter.limit("1/second")
@nsutils.route('/fixstalled/')
@nsutils.route('/fixstalled/<int:seconds>')
class FixStalled(Resource):
  def get (self, seconds = seconds_inactive):
    response = make_response("Starting thread fix_stalled. Watch the logs for errors.", 200)
    daemon = Thread(target=utils.fix_stalled, args=(host, port, username, password, seconds,), daemon=True, name="fix_stalled")
    daemon.start()
    return response

@limiter.limit("1/second")
@nsutils.route('/autoremovetorrents/')
class AutoremoveTorrents(Resource):
  def get (self):
    response = make_response("Starting thread autoremovetorrents. Watch the logs for errors.", 200)
    daemon = Thread(target=utils.autoremovetorrents, args=(), daemon=True, name="autoremovetorrents")
    daemon.start()
    return response

@limiter.limit("1/second")
@nsutils.route('/sonarrsearchall/')
class SonarrSearchAll(Resource):
  def get (self):
    response = make_response("Starting thread sonarrsearchall. Watch the logs for errors.", 200)
    daemon = Thread(target=utils.search_all, args=(host, sonarr_port, sonarr_token, "sonarr"), daemon=True, name="sonarrsearchall")
    daemon.start()
    return response

@limiter.limit("1/second")
@nsutils.route('/radarrsearchall/')
class RadarrSearchAll(Resource):
  def get (self):
    response = make_response("Starting thread radarrsearchall. Watch the logs for errors.", 200)
    daemon = Thread(target=utils.search_all, args=(host, radarr_port, radarr_token, "radarr"), daemon=True, name="radarrsearchall")
    daemon.start()
    return response

@scheduler.task('interval', id='fix_stalled', seconds=seconds_inactive)
def fix_stalled():
  utils.fix_stalled(host, port, username, password, seconds_inactive)

@scheduler.task('interval', id='autoremovetorrents', minutes=autoremove_loop_minutes)
def autoremovetorrents():
  utils.autoremovetorrents()

@scheduler.task('interval', id='sonarrsearchall', minutes=sonarr_search_loop_minutes)
def sonarrsearchall():
  utils.search_all(host, sonarr_port, sonarr_token, "sonarr")

@scheduler.task('interval', id='radarrsearchall', minutes=radarr_search_loop_minutes)
def radarrsearchall():
  utils.search_all(host, radarr_port, radarr_token, "radarr")


limiter.init_app(app)
scheduler.init_app(app)
scheduler.start()

if __name__ == '__main__':
  app.run()
