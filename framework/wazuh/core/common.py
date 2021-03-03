# Copyright (C) 2015-2020, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import json
import os
import subprocess
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from grp import getgrnam
from pwd import getpwnam
from typing import Dict, Any
from copy import deepcopy
from functools import lru_cache

try:
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'wazuh.json'), 'r') as f:
        metadata = json.load(f)
except (FileNotFoundError, PermissionError):
    metadata = {
        'install_type': 'server',
        'installation_date': '',
        'wazuh_version': ''
    }


@lru_cache(maxsize=None)
def find_wazuh_path():
    """
    Gets the path where Wazuh is installed dinamically

    :return: str path where Wazuh is installed or empty string if there is no framework in the environment
    """
    abs_path = os.path.abspath(os.path.dirname(__file__))
    allparts = []
    while 1:
        parts = os.path.split(abs_path)
        if parts[0] == abs_path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == abs_path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            abs_path = parts[0]
            allparts.insert(0, parts[1])

    wazuh_path = ''
    try:
        for i in range(0, allparts.index('framework')):
            wazuh_path = os.path.join(wazuh_path, allparts[i])
    except ValueError:
        pass

    return wazuh_path


def call_wazuh_control(option) -> str:
    wazuh_control = os.path.join(find_wazuh_path(), "bin", "wazuh-control")
    try:
        proc = subprocess.Popen([wazuh_control, option], stdout=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        return stdout.decode()
    except:
        return None


def get_wazuh_info(field) -> str:
    wazuh_info = call_wazuh_control("info")
    if not wazuh_info:
        return "ERROR"

    if not field:
        return wazuh_info

    env_variables = wazuh_info.rsplit("\n")
    env_variables.remove("")
    wazuh_env_vars = dict()
    for env_variable in env_variables:
        key, value = env_variable.split("=")
        wazuh_env_vars[key] = value.replace("\"", "")

    return wazuh_env_vars[field]


@lru_cache(maxsize=None)
def get_wazuh_version() -> str:
    return get_wazuh_info("WAZUH_VERSION")


@lru_cache(maxsize=None)
def get_wazuh_revision() -> str:
    return get_wazuh_info("WAZUH_REVISION")


@lru_cache(maxsize=None)
def get_wazuh_type() -> str:
    return get_wazuh_info("WAZUH_TYPE")


ossec_path = find_wazuh_path()

install_type = metadata['install_type']
wazuh_version = metadata['wazuh_version']
installation_date = metadata['installation_date']
ossec_conf = os.path.join(ossec_path, 'etc', 'ossec.conf')
internal_options = os.path.join(ossec_path, 'etc', 'internal_options.conf')
local_internal_options = os.path.join(ossec_path, 'etc', 'local_internal_options.conf')
ossec_log = os.path.join(ossec_path, 'logs', 'ossec.log')
client_keys = os.path.join(ossec_path, 'etc', 'client.keys')
stats_path = os.path.join(ossec_path, 'stats')
groups_path = os.path.join(ossec_path, 'queue', 'agent-groups')
multi_groups_path = os.path.join(ossec_path, 'var', 'multigroups')
shared_path = os.path.join(ossec_path, 'etc', 'shared')
backup_path = os.path.join(ossec_path, 'backup')
database_path = os.path.join(ossec_path, 'var', 'db')
database_path_global = os.path.join(database_path, 'global.db')
wdb_socket_path = os.path.join(ossec_path, 'queue', 'db', 'wdb')
wdb_path = os.path.join(ossec_path, 'queue', 'db')
api_config_path = os.path.join(ossec_path, 'api', 'configuration', 'api.yaml')
database_path_agents = os.path.join(database_path, 'agents')
os_pidfile = os.path.join('var', 'run')
analysisd_stats = os.path.join(ossec_path, 'var', 'run', 'wazuh-analysisd.state')
remoted_stats = os.path.join(ossec_path, 'var', 'run', 'wazuh-remoted.state')
ar_conf_path = os.path.join(ossec_path, 'etc', 'shared', 'ar.conf')

# Ruleset
# Ruleset paths
ruleset_path = os.path.join(ossec_path, 'ruleset')
ruleset_rules_path = os.path.join(ruleset_path, 'rules')
ruleset_decoders_path = os.path.join(ruleset_path, 'decoders')
ruleset_lists_path = os.path.join(ruleset_path, 'lists')
user_lists_path = os.path.join(ossec_path, 'etc', 'lists')
user_rules_path = os.path.join(ossec_path, 'etc', 'rules')
user_decoders_path = os.path.join(ossec_path, 'etc', 'decoders')
# Ruleset vars
RULES_EXTENSION = '.xml'
DECODERS_EXTENSION = '.xml'
LISTS_EXTENSION = ''
COMPILED_LISTS_EXTENSION = '.cdb'

# Queues
ARQUEUE = os.path.join(ossec_path, 'queue', 'alerts', 'ar')
EXECQ = os.path.join(ossec_path, 'queue', 'alerts', 'execq')

# Socket
AUTHD_SOCKET = os.path.join(ossec_path, 'queue', 'sockets', 'auth')
REQUEST_SOCKET = os.path.join(ossec_path, 'queue', 'sockets', 'request')
LOGTEST_SOCKET = os.path.join(ossec_path, 'queue', 'sockets', 'logtest')
UPGRADE_SOCKET = os.path.join(ossec_path, 'queue', 'tasks', 'upgrade')

TASKS_SOCKET = os.path.join(ossec_path, 'queue', 'tasks', 'task')

# Wdb
MAX_SOCKET_BUFFER_SIZE = 64 * 1024  # 64KB
MAX_QUERY_FILTERS_RESERVED_SIZE = MAX_SOCKET_BUFFER_SIZE - 4 * 1024  # MAX_BUFFER_SIZE - 4KB

# Agent upgrading variables
wpk_repo_url_4_x = "packages.wazuh.com/4.x/wpk/"
wpk_repo_url_3_x = "packages.wazuh.com/wpk/"

# Agent component stats required version
AGENT_COMPONENT_STATS_REQUIRED_VERSION = {'logcollector': 'v4.2.0',
                                          'agent': 'v4.2.0'}

wpk_chunk_size = 512

open_retries = 10  # Retries until get open ok message
open_sleep = 5  # Seconds between retries

upgrade_result_retries = 60  # Retries until get upgrade_result ok message
upgrade_result_sleep = 5  # Seconds between retries

agent_info_retries = 100  # Retries to detect when agent_info file is updated
agent_info_sleep = 2  # Seconds between retries

# Common variables
database_limit = 500
maximum_database_limit = 1000
limit_seconds = 1800  # 600*3

_wazuh_uid = None
_wazuh_gid = None

# Version variables (legacy, required, etc)
AR_LEGACY_VERSION = 'Wazuh v4.2.0'
ACTIVE_CONFIG_VERSION = 'Wazuh v3.7.0'

# Command variables
CHECK_CONFIG_COMMAND = 'check-manager-configuration'
RESTART_WAZUH_COMMAND = 'restart-wazuh'


def wazuh_uid():
    return getpwnam("wazuh").pw_uid if globals()['_wazuh_uid'] is None else globals()['_wazuh_uid']


def wazuh_gid():
    return getgrnam("wazuh").gr_gid if globals()['_wazuh_gid'] is None else globals()['_wazuh_gid']


# Multigroup variables
max_groups_per_multigroup = 256

# Context variables
rbac: ContextVar[Dict] = ContextVar('rbac', default={'rbac_mode': 'black'})
current_user: ContextVar[str] = ContextVar('current_user', default='')
broadcast: ContextVar[bool] = ContextVar('broadcast', default=False)
cluster_nodes: ContextVar[list] = ContextVar('cluster_nodes', default=list())

_context_cache = dict()


def context_cached(key: str = '') -> Any:
    """Save the result of the decorated function in a cache.

    Next calls to the decorated function returns the saved result saving time and resources. The cache gets
    invalidated at the end of the request.

    Parameters
    ----------
    key : str
        Part of the cache entry identifier. The identifier will be the key + args + kwargs.

    Returns
    -------
    Any
        The result of the first call to the decorated function.
    """

    def decorator(func) -> Any:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cached_key = json.dumps({'key': key, 'args': args, 'kwargs': kwargs})
            if cached_key not in _context_cache:
                _context_cache[cached_key] = ContextVar(cached_key, default=None)
            if _context_cache[cached_key].get() is None:
                result = func(*args, **kwargs)
                _context_cache[cached_key].set(result)
            return deepcopy(_context_cache[cached_key].get())

        return wrapper

    return decorator


def reset_context_cache() -> None:
    """Reset context cache.
    """

    for context_var in _context_cache.values():
        context_var.set(None)


def get_context_cache() -> dict:
    """Get the context cache.

    Returns
    -------
    dict
        Dictionary with the context variables representing the cache.
    """

    return _context_cache
