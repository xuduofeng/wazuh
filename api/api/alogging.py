# Copyright (C) 2015-2019, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2
import logging
import re

from aiohttp.abc import AbstractAccessLogger
from werkzeug.exceptions import Unauthorized

from api.authentication import decode_token
from wazuh.core.wlogging import WazuhLogger

# compile regex when the module is imported so it's not necessary to compile it everytime log.info is called
request_pattern = re.compile(r'\[.+\]|\s+\*\s+')

# Variable used to specify an unknown user
UNKNOWN_USER_STRING = "unknown_user"


class AccessLogger(AbstractAccessLogger):

    def log(self, request, response, time):
        # With permanent redirect or not found responses, we have no token information,
        # decode the JWT Token to get the username
        if response.status == 308 or response.status == 404:
            try:
                user = decode_token(request.headers["authorization"][7:])["sub"]
            except Unauthorized:
                user = UNKNOWN_USER_STRING
        else:
            user = request.get("user", UNKNOWN_USER_STRING)

        self.logger.info(f'{user} '
                         f'{request.remote} '
                         f'"{request.method} {request.path}" '
                         f'done in {time:.3f}s: {response.status}')


class APILogger(WazuhLogger):
    """
    Defines the logger used by wazuh-apid
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(*args, **kwargs, tag='{asctime} {levelname}: {message}')

    def setup_logger(self):
        """
        Set ups API logger. In addition to super().setup_logger() this method adds:
            * Sets up log level based on the log level defined in API configuration file.
        """
        super().setup_logger()

        if self.debug_level == 'debug2':
            debug_level = logging.DEBUG2
        elif self.debug_level == 'debug':
            debug_level = logging.DEBUG
        elif self.debug_level == 'critical':
            debug_level = logging.CRITICAL
        elif self.debug_level == 'error':
            debug_level = logging.ERROR
        elif self.debug_level == 'warning':
            debug_level = logging.WARNING
        else:  # self.debug_level == 'info'
            debug_level = logging.INFO

        self.logger.setLevel(debug_level)
