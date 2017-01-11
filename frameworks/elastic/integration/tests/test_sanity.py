import pytest

from tests.test_utils import *

DEFAULT_NUMBER_OF_SHARDS = 1
DEFAULT_NUMBER_OF_REPLICAS = 1
DEFAULT_SETTINGS_MAPPINGS = {
    "settings": {
        "index.unassigned.node_left.delayed_timeout": "0",
        "number_of_shards": DEFAULT_NUMBER_OF_SHARDS,
        "number_of_replicas": DEFAULT_NUMBER_OF_REPLICAS},
    "mappings": {
        DEFAULT_INDEX_TYPE: {
            "properties": {
                "name": {"type": "keyword"},
                "role": {"type": "keyword"}}}}}


def setup_module(module):
    uninstall()
    gc_frameworks()
    shakedown.install_package_and_wait(package_name=PACKAGE_NAME, options_file=None, timeout_sec=WAIT_TIME_IN_SECONDS)


def setup_function(function):
    wait_for_dcos_tasks_health(DEFAULT_TASK_COUNT)
    wait_for_expected_nodes_to_exist()


def teardown_module(module):
    uninstall()


@pytest.fixture
def default_populated_index():
    delete_index(DEFAULT_INDEX_NAME)
    create_index(DEFAULT_INDEX_NAME, DEFAULT_SETTINGS_MAPPINGS)
    create_document(DEFAULT_INDEX_NAME, DEFAULT_INDEX_TYPE, 1, {"name": "Loren", "role": "developer"})


@pytest.mark.sanity
def test_service_health():
    check_dcos_service_health()


@pytest.mark.sanity
def test_indexing(default_populated_index):
    indices_stats = get_elasticsearch_indices_stats(DEFAULT_INDEX_NAME)
    assert indices_stats["_all"]["primaries"]["docs"]["count"] == 1
    doc = get_document(DEFAULT_INDEX_NAME, DEFAULT_INDEX_TYPE, 1)
    assert doc["_source"]["name"] == "Loren"


@pytest.mark.sanity
def test_commercial_api_available(default_populated_index):
    query = {
        "query": {
            "match": {
                "name": "*"
            }
        },
        "vertices": [
            {
                "field": "name"
            }
        ],
        "connections": {
            "vertices": [
                {
                    "field": "role"
                }
            ]
        }
    }
    response = graph_api(DEFAULT_INDEX_NAME, query)
    assert response["failures"] == []


@pytest.mark.recovery
def test_losing_and_regaining_index_health(default_populated_index):
    check_elasticsearch_index_health(DEFAULT_INDEX_NAME, "green")
    shakedown.kill_process_on_host("data-0-server.{}.mesos".format(PACKAGE_NAME), "data__.*Elasticsearch")
    check_elasticsearch_index_health(DEFAULT_INDEX_NAME, "yellow")
    check_elasticsearch_index_health(DEFAULT_INDEX_NAME, "green")


@pytest.mark.recovery
def test_master_reelection():
    initial_master = get_elasticsearch_master()
    shakedown.kill_process_on_host("{}.{}.mesos".format(initial_master, PACKAGE_NAME), "master__.*Elasticsearch")
    check_new_elasticsearch_master_elected(initial_master)


@pytest.mark.recovery
def test_plugin_install_and_uninstall(default_populated_index):
    plugin_name = 'analysis-phonetic'
    config = get_elasticsearch_config()
    config['env']['ELASTICSEARCH_PLUGINS'] = plugin_name
    marathon_update(config)
    check_plugin_installed(plugin_name)

    config = get_elasticsearch_config()
    config['env']['ELASTICSEARCH_PLUGINS'] = ""
    marathon_update(config)
    check_plugin_uninstalled(plugin_name)


@pytest.mark.recovery
def test_unchanged_scheduler_restarts_without_restarting_tasks():
    initial_task_ids = get_task_ids()
    shakedown.kill_process_on_host(get_marathon_host(), "scheduler.Main")
    wait_for_dcos_tasks_health(DEFAULT_TASK_COUNT)
    current_task_ids = get_task_ids()
    assert initial_task_ids == current_task_ids


@pytest.mark.recovery
def test_bump_node_counts():
    config = get_elasticsearch_config()
    data_nodes = int(config['env']['DATA_NODE_COUNT'])
    config['env']['DATA_NODE_COUNT'] = str(data_nodes + 1)
    ingest_nodes = int(config['env']['INGEST_NODE_COUNT'])
    config['env']['INGEST_NODE_COUNT'] = str(ingest_nodes + 1)
    coordinator_nodes = int(config['env']['COORDINATOR_NODE_COUNT'])
    config['env']['COORDINATOR_NODE_COUNT'] = str(coordinator_nodes + 1)
    marathon_update(config)

    wait_for_dcos_tasks_health(DEFAULT_TASK_COUNT + 3)
