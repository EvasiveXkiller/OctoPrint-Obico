import os
import logging
import subprocess
import time
import hashlib
import sys

from threading import Thread
import backoff
import json
import socket
import psutil
from octoprint.util import to_unicode

try:
    import queue
except ImportError:
    import Queue as queue

from .utils import ExpoBackoff, pi_version, is_port_open, wait_for_port, wait_for_port_to_close, run_in_thread
from .ws import WebSocketClient
from .lib import alert_queue
from .janus_config_builder import RUNTIME_JANUS_ETC_DIR

_logger = logging.getLogger('octoprint.plugins.obico')

# Base port for Janus. Each instance will get a unique offset based on its basedir.
JANUS_BASE_PORT = 17730
# Port gap between instances (needs room for ws, admin_ws, video, videortcp, data ports)
JANUS_PORT_GAP = 20

def get_octoprint_basedir():
    """
    Try to determine the OctoPrint basedir from various sources.
    This is used to ensure each OctoPrint instance gets unique Janus ports.
    """
    # Method 1: Check command line arguments for --basedir
    for i, arg in enumerate(sys.argv):
        if arg == '--basedir' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith('--basedir='):
            return arg.split('=', 1)[1]
    
    # Method 2: Check environment variable
    basedir = os.environ.get('OCTOPRINT_BASEDIR', '')
    if basedir:
        return basedir
    
    # Method 3: Check process command line (for when running as service)
    try:
        proc = psutil.Process(os.getpid())
        cmdline = proc.cmdline()
        for i, arg in enumerate(cmdline):
            if arg == '--basedir' and i + 1 < len(cmdline):
                return cmdline[i + 1]
            if arg.startswith('--basedir='):
                return arg.split('=', 1)[1]
    except:
        pass
    
    # Method 4: Default OctoPrint location
    default_path = os.path.expanduser('~/.octoprint')
    if os.path.exists(default_path):
        return default_path
    
    return ''

def get_instance_port_offset():
    """
    Calculate a unique port offset for this OctoPrint instance based on its basedir.
    This ensures multiple instances get different ports even when sharing the same Python environment.
    """
    basedir = get_octoprint_basedir()
    
    if basedir:
        # Use SHA256 for better distribution, take 16 hex chars for enough entropy
        hash_val = int(hashlib.sha256(basedir.encode()).hexdigest()[:16], 16)
        # Use modulo 10 to get 10 possible slots, each 20 ports apart
        # This supports up to 10 instances on ports 17730-17930
        slot = hash_val % 10
        offset = slot * JANUS_PORT_GAP
        _logger.debug(f'Instance basedir: {basedir}, slot: {slot}, port offset: {offset}')
        return offset
    
    return 0

def calculate_janus_ports():
    """
    Calculate Janus ports for this instance.
    First tries instance-based offset, then falls back to PID file detection.
    """
    base_port = JANUS_BASE_PORT + get_instance_port_offset()
    
    # Also check if the calculated port is already in use via PID file
    # This handles edge cases where hash collision occurs
    for i in range(5):  # Try up to 5 different port ranges
        test_port = base_port + (i * JANUS_PORT_GAP)
        pid_file = f'/tmp/obico-janus-{test_port}.pid'
        
        if not os.path.exists(pid_file):
            return test_port
        
        # PID file exists - check if process is actually running
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            if not psutil.pid_exists(pid):
                # Stale PID file - we can use this port
                os.remove(pid_file)
                return test_port
        except (ValueError, FileNotFoundError, PermissionError):
            # Invalid or inaccessible PID file - try to remove and use
            try:
                os.remove(pid_file)
            except:
                pass
            return test_port
    
    # Fallback: return the base port and hope for the best
    _logger.warning(f'Could not find available Janus port, using {base_port}')
    return base_port

# Calculate ports at module load time
JANUS_WS_PORT = calculate_janus_ports()
JANUS_ADMIN_WS_PORT = JANUS_WS_PORT + 1

_logger.info(f'Janus ports for this instance: WS={JANUS_WS_PORT}, Admin={JANUS_ADMIN_WS_PORT} (basedir: {get_octoprint_basedir()})')

def janus_pid_file_path():
    return f'/tmp/obico-janus-{JANUS_WS_PORT}.pid'

class JanusConn:

    def __init__(self, plugin, janus_server):
        self.plugin = plugin
        self.janus_server = janus_server
        self.janus_ws = None
        self.shutting_down = False

    def start(self, janus_bin_path, ld_lib_path):

        def run_janus_forever():
            try:
                janus_cmd = '{janus_bin_path} --stun-server=stun.l.google.com:19302 --configs-folder {config_folder}'.format(janus_bin_path=janus_bin_path, config_folder=RUNTIME_JANUS_ETC_DIR)
                env = {}
                if ld_lib_path:
                    env={'LD_LIBRARY_PATH': ld_lib_path + ':' + os.environ.get('LD_LIBRARY_PATH', '')}
                _logger.debug('Popen: {} {}'.format(env, janus_cmd))
                janus_proc = subprocess.Popen(janus_cmd.split(), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                with open(janus_pid_file_path(), 'w') as pid_file:
                    pid_file.write(str(janus_proc.pid))

                while True:
                    line = to_unicode(janus_proc.stdout.readline(), errors='replace')
                    if line:
                        _logger.debug('JANUS: ' + line.rstrip())
                    else:  # line == None means the process quits
                        _logger.warn('Janus quit with exit code {}'.format(janus_proc.wait()))
                        return
            except Exception as ex:
                self.plugin.sentry.captureException()

        self.kill_janus_if_running()
        run_in_thread(run_janus_forever)
        self.wait_for_janus()
        self.start_janus_ws()

    def connected(self):
        return self.janus_ws and self.janus_ws.connected()

    def pass_to_janus(self, msg):
        if self.connected():
            self.janus_ws.send(msg)

    def wait_for_janus(self):
        time.sleep(0.2)
        wait_for_port(self.janus_server, JANUS_WS_PORT)

    def start_janus_ws(self):

        def on_close(ws, **kwargs):
            _logger.warn('Janus WS connection closed!')

        self.janus_ws = WebSocketClient(
            'ws://{}:{}/'.format(self.janus_server, JANUS_WS_PORT),
            on_ws_msg=self.process_janus_msg,
            on_ws_close=on_close,
            subprotocols=['janus-protocol'],
            waitsecs=30)

    def kill_janus_if_running(self):
        try:
            # It is possible that orphaned janus process is running (maybe previous python process was killed -9?).
            # Ensure the process is killed before launching a new one
            with open(janus_pid_file_path(), 'r') as pid_file:
                subprocess.run(['kill', pid_file.read()], check=True)
            wait_for_port_to_close(self.janus_server, JANUS_WS_PORT)
        except Exception as e:
            _logger.warning('Failed to shutdown Janus - ' + str(e))

        try:
            os.remove(janus_pid_file_path())
        except:
            pass

    def shutdown(self):
        self.shutting_down = True

        if self.janus_ws is not None:
            self.janus_ws.close()

        self.janus_ws = None

        self.kill_janus_if_running()

    def process_janus_msg(self, ws, raw_msg):
        try:
            msg = json.loads(raw_msg)
            _logger.debug('Relaying Janus msg')
            _logger.debug(msg)
            self.plugin.send_ws_msg_to_server(dict(janus=raw_msg))
        except:
            self.plugin.sentry.captureException()
