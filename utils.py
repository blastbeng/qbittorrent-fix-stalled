import logging
import os
import sys
import qbittorrentapi
from os.path import dirname
from os.path import join
from pathlib import Path
from dotenv import load_dotenv

import sys
import getopt
import traceback
import yaml
from autoremovetorrents import logger
from autoremovetorrents.task import Task
from autoremovetorrents.version import __version__
from autoremovetorrents.compatibility.open_ import open_

import requests
import json

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
        
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

def fix_stalled(host, port, username, password, seconds):
    try:
        logging.info("--- START fix_stalled START ---")
        conn_info = dict(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        logging.info("Connecting...")
        qbt_client = qbittorrentapi.Client(**conn_info)

        torrents=[]
        for torrent in qbt_client.torrents.info(status_filter="stalled_downloading"):
            torrents.append(torrent)
        for torrent in  qbt_client.torrents.info(status_filter="active"):
            torrents.append(torrent)
        for torrent in  qbt_client.torrents.info(status_filter="queued"):
            torrents.append(torrent)

        fix_prio(qbt_client, torrents, seconds)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)
    finally:
        logging.info("--- END fix_stalled END ---")
          
def log_bottom(torrent):    
    logging.info("Torrent: %s", torrent.info.name)
    logging.info("      - hash:        %s", torrent.info.hash)
    logging.info("      - state:       %s", torrent.info.state)
    logging.info("      - num_seeds:   %s", torrent.info.num_seeds)
    logging.info("      - dl_speed:   %s", torrent.info.num_seeds)
    logging.info("      - time_active: %s", str(torrent.info.time_active))
    logging.info("      - action: %s", "setting bottom priority")

def fix_prio(qbt_client, data, seconds):
    queued_torrent_dict = {}
    parsed_torrents_array = []
    for torrent in data:
        if torrent.state == 'stalledDL' and torrent.info.time_active > seconds:
            if torrent.hash not in parsed_torrents_array:
                parsed_torrents_array.append(torrent.hash)
            log_bottom(torrent)
            qbt_client.torrents.bottom_priority(torrent_hashes=torrent.hash)
        elif torrent.state == 'metaDL' and (torrent.info.num_seeds == 0 or torrent.dlspeed < 100000) and torrent.info.time_active > seconds:
            if torrent.hash not in parsed_torrents_array:
                parsed_torrents_array.append(torrent.hash)
            log_bottom(torrent)
            qbt_client.torrents.bottom_priority(torrent_hashes=torrent.hash)
        elif torrent.state == 'downloading' and (torrent.info.num_seeds == 0 or torrent.dlspeed < 100000) and torrent.info.time_active > seconds:
            if torrent.hash not in parsed_torrents_array:
                parsed_torrents_array.append(torrent.hash)
            log_bottom(torrent)
            qbt_client.torrents.bottom_priority(torrent_hashes=torrent.hash)
        elif torrent.state == 'queuedDL' and torrent.info.completed != 0 and torrent.info.size != 0 and torrent.info.num_complete != 0:
            queued_torrent_dict[torrent.info.hash] = (torrent.info.completed / torrent.info.size) * 100      
        elif torrent.state != 'queuedDL':
            logging.info("Torrent: %s", torrent.info.name)
            logging.info("      - hash:        %s", torrent.info.hash)
            logging.info("      - state:       %s", torrent.state)
            logging.info("      - num_seeds:   %s", torrent.info.num_seeds)
            logging.info("      - dl_speed:   %s", torrent.info.num_seeds)
            logging.info("      - time_active: %s", str(torrent.info.time_active))
            logging.info("      - action: %s", "skipped")
    if queued_torrent_dict != {} and len(queued_torrent_dict) > 0:
        torrent_sorted_dict = dict(reversed(sorted(queued_torrent_dict.items(), key=lambda item: item[1])))
        count = 5
        if len(torrent_sorted_dict) < count:
            count = len(torrent_sorted_dict) - 1
        torrent_final_dict = {A:N for (A,N) in [x for x in torrent_sorted_dict.items()][:count]}
        for key in torrent_final_dict:
            if key not in parsed_torrents_array:
                logging.info("Increasing priority on torrent with hash [ %s ] since its completed percentage is [ %s ]", key, str(torrent_final_dict[key]).split(".")[0])
                qbt_client.torrents.top_priority(torrent_hashes=key)

def autoremovetorrents(view_mode=False, conf_path='./config.yml', task=None, log_path='', debug_mode=False):
    try:
        logger.Logger.init(log_path, file_debug_log = debug_mode, output_debug_log = debug_mode)
        lg = logger.Logger.register(__name__)
        lg.info('Auto Remove Torrents %s' % __version__)
        lg.info('Loading configurations...')
        with open_(conf_path, 'r', encoding='utf-8') as stream:
            result = yaml.safe_load(stream)
        lg.info('Found %d task(s) in the file.' % len(result))

        if task == None:
            for task_name in result:
                Task(task_name, result[task_name], not view_mode).execute()
        else:
            Task(task, result[task], not view_mode).execute()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)

def search_all(host, port, token, mode = ""):
    try:
        logging.info("--- START search_all %s START ---", mode)
        payload = None
        if mode == "":
            raise Exception("Mode is mandatory.")
        if mode == "sonarr":
            url = "http://" + host + ":" + str(port) + "/api/v3/command"
            payload = {'name': 'MissingEpisodeSearch', 'monitored': True}
        elif mode == "radarr":
            url = "http://" + host + ":" + str(port) + "/api/v3/command"
            payload = {'name': 'MoviesSearch', 'monitored': True}
        
        if payload is None:
            raise Exception("Payload is mandatory.")
        else:
            headers = {'X-Api-key': token}
            call_api(url, payload, headers)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)
    finally:
        logging.info("--- START search_all %s END ---", mode)

def call_api(url, payload, headers):
    try:
        response = requests.get(url, params=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            logging.info("Calling API:            %s", url)
            logging.info("Request Payload:        %s", str(payload))
            logging.info("Response Status Code:   %s", str(response.status_code))
        else:
            logging.error("Response Status Code:   %s:", str(response.status_code))
            logging.error("Response Reason:        %s:", response.reason)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("%s %s %s", exc_type, fname, exc_tb.tb_lineno, exc_info=1)