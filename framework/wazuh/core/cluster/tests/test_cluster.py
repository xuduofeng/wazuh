# Copyright (C) 2015-2020, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import sys
from datetime import datetime
from time import time
from unittest.mock import patch, mock_open, MagicMock

import pytest

from wazuh.core import common

with patch('wazuh.common.wazuh_uid'):
    with patch('wazuh.common.wazuh_gid'):
        sys.modules['wazuh.rbac.orm'] = MagicMock()
        import wazuh.rbac.decorators

        del sys.modules['wazuh.rbac.orm']
        from wazuh.tests.util import RBAC_bypasser

        wazuh.rbac.decorators.expose_resources = RBAC_bypasser
        import wazuh.core.cluster.utils
        import wazuh.core.cluster.cluster
        from wazuh import WazuhException

# Valid configurations
default_cluster_configuration = {
    'cluster': {
        'disabled': 'yes',
        'node_type': 'master',
        'name': 'wazuh',
        'node_name': 'node01',
        'key': '',
        'port': 1516,
        'bind_addr': '0.0.0.0',
        'nodes': ['NODE_IP'],
        'hidden': 'no'
    }
}

custom_cluster_configuration = {
    'cluster': {
        'disabled': 'no',
        'node_type': 'master',
        'name': 'wazuh',
        'node_name': 'node01',
        'key': 'a' * 32,
        'port': 1516,
        'bind_addr': '0.0.0.0',
        'nodes': ['172.10.0.100'],
        'hidden': False
    }
}

custom_incomplete_configuration = {
    'cluster': {
        'key': 'a' * 32,
        'node_name': 'master'
    }
}


def test_read_empty_configuration():
    """
    Test reading an empty cluster configuration
    """
    with patch('wazuh.core.cluster.utils.get_ossec_conf') as m:
        wazuh.core.cluster.utils.read_config.cache_clear()
        m.side_effect = WazuhException(1106)
        configuration = wazuh.core.cluster.utils.read_config()
        configuration['disabled'] = 'yes' if configuration['disabled'] else 'no'
        assert configuration == default_cluster_configuration['cluster']


@pytest.mark.parametrize('read_config', [
    default_cluster_configuration,
    custom_cluster_configuration,
    custom_incomplete_configuration
])
def test_read_configuration(read_config):
    """
    Tests reading the cluster configuration from ossec.conf
    """
    with patch('wazuh.core.cluster.utils.get_ossec_conf') as m:
        m.return_value = read_config.copy()
        configuration = wazuh.core.cluster.utils.read_config()
        configuration['disabled'] = 'yes' if configuration['disabled'] else 'no'
        wazuh.core.cluster.utils.read_config.cache_clear()
        for k in read_config['cluster'].keys():
            assert configuration[k] == read_config['cluster'][k]

        # values not present in the read user configuration will be filled with default values
        if 'disabled' not in read_config and read_config != {}:
            default_cluster_configuration['disabled'] = 'no'
        for k in default_cluster_configuration.keys() - read_config.keys():
            assert configuration[k] == default_cluster_configuration[k]


@pytest.mark.parametrize('read_config', [
    {'cluster': {'disabled': 'yay'}},
    {'cluster': {'key': '', 'nodes': ['192.158.35.13']}},
    {'cluster': {'key': 'a' * 15, 'nodes': ['192.158.35.13']}},
    {'cluster': {'port': 'string', 'key': 'a' * 32, 'nodes': ['192.158.35.13']}},
    {'cluster': {'port': 90, 'key': 'a' * 32, 'nodes': ['192.158.35.13']}},
    {'cluster': {'port': 70000, 'key': 'a' * 32, 'nodes': ['192.158.35.13']}},
    {'cluster': {'node_type': 'random', 'key': 'a' * 32, 'nodes': ['192.158.35.13']}},
    {'cluster': {'nodes': ['NODE_IP'], 'key': 'a' * 32}},
    {'cluster': {'nodes': ['localhost'], 'key': 'a' * 32}},
    {'cluster': {'nodes': ['0.0.0.0'], 'key': 'a' * 32}},
    {'cluster': {'nodes': ['127.0.1.1'], 'key': 'a' * 32}}
])
def test_checking_configuration(read_config):
    """
    Checks wrong configurations to check the proper exceptions are raised
    """
    with patch('wazuh.core.cluster.utils.get_ossec_conf') as m:
        m.return_value = read_config.copy()
        with pytest.raises(WazuhException, match=r'.* 3004 .*'):
            configuration = wazuh.core.cluster.utils.read_config()
            wazuh.core.cluster.cluster.check_cluster_config(configuration)


agent_groups = b"default,windows-servers"


@patch('os.listdir', return_value=['005', '006'])
@patch('wazuh.core.cluster.cluster.stat')
def test_merge_info(stat_mock, listdir_mock):
    """
    Tests merge agent info function
    """
    stat_mock.return_value.st_mtime = time()
    stat_mock.return_value.st_size = len(agent_groups)

    with patch('builtins.open', mock_open(read_data=agent_groups)) as m:
        wazuh.core.cluster.cluster.merge_info('agent-groups', 'worker1', file_type='-shared')
        m.assert_any_call(common.ossec_path + '/queue/cluster/worker1/agent-groups-shared.merged', 'wb')
        m.assert_any_call(common.ossec_path + '/queue/agent-groups/005', 'rb')
        m.assert_any_call(common.ossec_path + '/queue/agent-groups/006', 'rb')
        handle = m()
        expected = f'{len(agent_groups)} 005 ' \
                   f'{datetime.utcfromtimestamp(stat_mock.return_value.st_mtime)}\n'.encode() + agent_groups
        handle.write.assert_any_call(expected)


@pytest.mark.parametrize('agent_info, exception', [
    (f"23 005 2019-03-29 14:57:29.610934\n{agent_groups}".encode(), None),
    (f"2i58 006 2019-03-29 14:57:29.610934\n{agent_groups}".encode(), ValueError)
])
@patch('wazuh.core.cluster.cluster.stat')
def test_unmerge_info(stat_mock, agent_info, exception):
    stat_mock.return_value.st_size = len(agent_info)
    with patch('builtins.open', mock_open(read_data=agent_info)) as m:
        agent_groups = list(
            wazuh.core.cluster.cluster.unmerge_info('agent-groups', '/random/path', 'agent-groups-shared.merged'))
        assert len(agent_groups) == (1 if exception is None else 0)


def test_update_cluster_control_with_failed():
    """Check if cluster_control json is updated as expected"""
    ko_files = {
        'missing': {'/test_file0': 'test',
                    '/test_file3': 'ok'},
        'shared': {'/test_file1': 'test'},
        'extra': {'/test_file2': 'test'}
    }
    wazuh.core.cluster.cluster.update_cluster_control_with_failed(['/test_file0', '/test_file1', 'test_file2'], ko_files)

    assert ko_files == {'missing': {'/test_file3': 'ok'}, 'shared': {}, 'extra': {'/test_file2': 'test', '/test_file1': 'test'}}
