import dcos.http
import json
import pytest
import re
import shakedown

from tests.test_utils import (
    PACKAGE_NAME,
    check_health,
    get_marathon_config,
    get_task_count,
    install,
    marathon_api_url,
    request,
    run_dcos_cli_cmd,
    uninstall,
    spin
)


def setup_module(module):
    uninstall()
    install()
    check_health()


def teardown_module(module):
    uninstall()


@pytest.mark.sanity
def test_no_colocation_in_podtypes():
    # check that no two 'cassandras' and no two 'worlds' are colocated on the same agent
    all_tasks = shakedown.get_service_tasks(PACKAGE_NAME)
    print(all_tasks)
    cassandra_agents = []
    world_agents = []
    for task in all_tasks:
        if task['name'].startswith('cassandra-'):
            cassandra_agents.append(task['slave_id'])
        elif task['name'].startswith('world-'):
            world_agents.append(task['slave_id'])
        else:
            assert False, "Unknown task: " + task['name']
    assert len(cassandra_agents) == len(set(cassandra_agents))
    assert len(world_agents) == len(set(world_agents))


@pytest.mark.sanity
def test_bump_cassandra_cpus():
    check_health()
    cassandra_ids = get_task_ids('cassandra')
    print('cassandra ids: ' + str(cassandra_ids))

    config = get_marathon_config()
    cpus = float(config['env']['CASSANDRA_CPUS'])
    config['env']['CASSANDRA_CPUS'] = str(cpus + 0.1)
    request(
        dcos.http.put,
        marathon_api_url('apps/' + PACKAGE_NAME),
        json=config)

    tasks_updated('cassandra', cassandra_ids)
    check_health()


@pytest.mark.sanity
def test_bump_cassandra_nodes():
    check_health()

    cassandra_ids = get_task_ids('cassandra')
    print('cassandra ids: ' + str(cassandra_ids))

    config = get_marathon_config()
    nodeCount = int(config['env']['CASSANDRA_COUNT']) + 1
    config['env']['CASSANDRA_COUNT'] = str(nodeCount)
    request(
        dcos.http.put,
        marathon_api_url('apps/' + PACKAGE_NAME),
        json=config)

    check_health()
    tasks_not_updated('cassandra', cassandra_ids)


@pytest.mark.sanity
def test_pods_list():
    stdout = run_dcos_cli_cmd('cassandra pods list')
    jsonobj = json.loads(stdout)
    assert len(jsonobj) == get_task_count()
    # expect: X instances of 'cassandra-#' followed by Y instances of 'world-#',
    # in alphanumerical order
    first_world = -1
    for i in range(len(jsonobj)):
        entry = jsonobj[i]
        if first_world < 0:
            if entry.startswith('world-'):
                first_world = i
        if first_world == -1:
            assert jsonobj[i] == 'cassandra-{}'.format(i)
        else:
            assert jsonobj[i] == 'world-{}'.format(i - first_world)


@pytest.mark.sanity
def test_pods_status_all():
    stdout = run_dcos_cli_cmd('cassandra pods status')
    jsonobj = json.loads(stdout)
    assert len(jsonobj) == get_task_count()
    for k, v in jsonobj.items():
        assert re.match('(cassandra|world)-[0-9]+', k)
        assert len(v) == 1
        task = v[0]
        assert len(task) == 3
        assert re.match('(cassandra|world)-[0-9]+-server__[0-9a-f-]+', task['id'])
        assert re.match('(cassandra|world)-[0-9]+-server', task['name'])
        assert task['state'] == 'TASK_RUNNING'


@pytest.mark.sanity
def test_pods_status_one():
    stdout = run_dcos_cli_cmd('cassandra pods status cassandra-0')
    jsonobj = json.loads(stdout)
    assert len(jsonobj) == 1
    task = jsonobj[0]
    assert len(task) == 3
    assert re.match('cassandra-0-server__[0-9a-f-]+', task['id'])
    assert task['name'] == 'cassandra-0-server'
    assert task['state'] == 'TASK_RUNNING'


@pytest.mark.sanity
def test_pods_info():
    stdout = run_dcos_cli_cmd('cassandra pods info world-1')
    jsonobj = json.loads(stdout)
    assert len(jsonobj) == 1
    task = jsonobj[0]
    assert len(task) == 2
    assert task['info']['name'] == 'world-1-server'
    assert task['info']['taskId']['value'] == task['status']['taskId']['value']
    assert task['status']['state'] == 'TASK_RUNNING'


@pytest.mark.sanity
def test_pods_restart():
    cassandra_ids = get_task_ids('cassandra-0')

    # get current agent id:
    stdout = run_dcos_cli_cmd('cassandra pods info cassandra-0')
    old_agent = json.loads(stdout)[0]['info']['slaveId']['value']

    stdout = run_dcos_cli_cmd('cassandra pods restart cassandra-0')
    jsonobj = json.loads(stdout)
    assert len(jsonobj) == 2
    assert jsonobj['pod'] == 'cassandra-0'
    assert len(jsonobj['tasks']) == 1
    assert jsonobj['tasks'][0] == 'cassandra-0-server'

    tasks_updated('cassandra', cassandra_ids)
    check_health()

    # check agent didn't move:
    stdout = run_dcos_cli_cmd('cassandra pods info cassandra-0')
    new_agent = json.loads(stdout)[0]['info']['slaveId']['value']
    assert old_agent == new_agent


@pytest.mark.sanity
def test_pods_replace():
    world_ids = get_task_ids('world-0')

    # get current agent id:
    stdout = run_dcos_cli_cmd('cassandra pods info world-0')
    old_agent = json.loads(stdout)[0]['info']['slaveId']['value']

    jsonobj = json.loads(run_dcos_cli_cmd('cassandra pods replace world-0'))
    assert len(jsonobj) == 2
    assert jsonobj['pod'] == 'world-0'
    assert len(jsonobj['tasks']) == 1
    assert jsonobj['tasks'][0] == 'world-0-server'

    tasks_updated('world-0', world_ids)
    check_health()

    # check agent moved:
    stdout = run_dcos_cli_cmd('cassandra pods info world-0')
    new_agent = json.loads(stdout)[0]['info']['slaveId']['value']
    # TODO: enable assert if/when agent is guaranteed to change (may randomly move back to old agent)
    # assert old_agent != new_agent


def get_task_ids(prefix):
    tasks = shakedown.get_service_tasks(PACKAGE_NAME)
    prefixed_tasks = [t for t in tasks if t['name'].startswith(prefix)]
    task_ids = [t['id'] for t in prefixed_tasks]
    return task_ids


def tasks_updated(prefix, old_task_ids):
    def fn():
        try:
            return get_task_ids(prefix)
        except dcos.errors.DCOSHTTPException:
            return []

    def success_predicate(task_ids):
        print('Old task ids: ' + str(old_task_ids))
        print('New task ids: ' + str(task_ids))
        success = True

        for id in task_ids:
            print('Checking ' + id)
            if id in old_task_ids:
                success = False

        if not len(task_ids) >= len(old_task_ids):
            success = False

        print('Waiting for update to ' + prefix)
        return (
            success,
            'Task type:' + prefix + ' not updated'
        )

    return spin(fn, success_predicate)


def tasks_not_updated(prefix, old_task_ids):
    def fn():
        try:
            return get_task_ids(prefix)
        except dcos.errors.DCOSHTTPException:
            return []

    def success_predicate(task_ids):
        print('Old task ids: ' + str(old_task_ids))
        print('New task ids: ' + str(task_ids))
        success = True

        for id in old_task_ids:
            print('Checking ' + id)
            if id not in task_ids:
                success = False

        if not len(task_ids) >= len(old_task_ids):
            success = False

        print('Determining no update occurred for ' + prefix)
        return (
            success,
            'Task type:' + prefix + ' not updated'
        )

    return spin(fn, success_predicate)
