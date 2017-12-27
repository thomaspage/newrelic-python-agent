import pytest
import psycopg2
import psycopg2.extensions
import psycopg2.extras
try:
    from psycopg2 import sql
except ImportError:
    sql = None

from testing_support.fixtures import (validate_transaction_metrics,
    validate_database_trace_inputs, override_application_settings)
from testing_support.util import instance_hostname
from utils import DB_SETTINGS, PSYCOPG2_VERSION

from newrelic.api.background_task import background_task


# Settings
_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}


# Metrics
_base_scoped_metrics = (
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1),
)

_base_rollup_metrics = (
        ('Datastore/all', 12),
        ('Datastore/allOther', 12),
        ('Datastore/Postgres/all', 12),
        ('Datastore/Postgres/allOther', 12),
        ('Datastore/operation/Postgres/select', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/select', 1),
        ('Datastore/operation/Postgres/insert', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/insert', 1),
        ('Datastore/operation/Postgres/update', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/update', 1),
        ('Datastore/operation/Postgres/delete', 1),
        ('Datastore/statement/Postgres/datastore_psycopg2/delete', 1),
        ('Datastore/operation/Postgres/drop', 1),
        ('Datastore/operation/Postgres/create', 1),
        ('Datastore/statement/Postgres/now/call', 1),
        ('Datastore/statement/Postgres/pg_sleep/call', 1),
        ('Datastore/operation/Postgres/call', 2),
        ('Datastore/operation/Postgres/commit', 2),
        ('Datastore/operation/Postgres/rollback', 1),
)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

if PSYCOPG2_VERSION > (2, 4):
    _enable_scoped_metrics.append(('Function/psycopg2:connect', 1))
    _disable_scoped_metrics.append(('Function/psycopg2:connect', 1))
else:
    _enable_scoped_metrics.append(('Function/psycopg2._psycopg:connect', 1))
    _disable_scoped_metrics.append(('Function/psycopg2._psycopg:connect', 1))


_host = instance_hostname(DB_SETTINGS['host'])
_port = DB_SETTINGS['port']

_instance_metric_name = 'Datastore/instance/Postgres/%s/%s' % (_host, _port)

_enable_rollup_metrics.append(
        (_instance_metric_name, 11)
)

_disable_rollup_metrics.append(
        (_instance_metric_name, None)
)


# Query
def _execute(connection, cursor, row_type, wrapper):
    unicode_type = psycopg2.extensions.UNICODE
    psycopg2.extensions.register_type(unicode_type)
    psycopg2.extensions.register_type(unicode_type, connection)
    psycopg2.extensions.register_type(unicode_type, cursor)

    sql = """drop table if exists datastore_psycopg2"""
    cursor.execute(wrapper(sql))

    sql = """create table datastore_psycopg2 (a integer, b real, c text)"""
    cursor.execute(wrapper(sql))

    sql = """insert into datastore_psycopg2 values (%s, %s, %s)"""
    params = [(1, 1.0, '1.0'), (2, 2.2, '2.2'), (3, 3.3, '3.3')]
    cursor.executemany(wrapper(sql), params)

    sql = """select * from datastore_psycopg2"""
    cursor.execute(wrapper(sql))

    for row in cursor:
        assert isinstance(row, row_type)

    sql = """update datastore_psycopg2 set a=%s, b=%s, c=%s where a=%s"""
    params = (4, 4.0, '4.0', 1)
    cursor.execute(wrapper(sql), params)

    sql = """delete from datastore_psycopg2 where a=2"""
    cursor.execute(wrapper(sql))

    connection.commit()

    cursor.callproc('now')
    cursor.callproc('pg_sleep', (0.25,))

    connection.rollback()
    connection.commit()


def _exercise_db(cursor_factory=None, use_cur_context=False, row_type=tuple,
        wrapper=str):
    connection = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])
    kwargs = {'cursor_factory': cursor_factory} if cursor_factory else {}

    try:
        if use_cur_context:
            with connection.cursor(**kwargs) as cursor:
                _execute(connection, cursor, row_type, wrapper)
        else:
            cursor = connection.cursor(**kwargs)
            _execute(connection, cursor, row_type, wrapper)
    finally:
        connection.close()


_test_matrix = ['wrapper,use_cur_context', [(str, False)]]


if PSYCOPG2_VERSION >= (2, 5):
    # with statement support for connections/cursors added in 2.5 and up
    _test_matrix[1].append((str, True))

if PSYCOPG2_VERSION >= (2, 7):
    # Composable SQL is expected to be available in versions 2.7 and up
    assert sql, (
            "Composable sql (from psycopg2 import sql) is expected to load"
            "but is not loading")

    # exercise with regular SQL wrapper
    _test_matrix[1].append((sql.SQL, True))
    _test_matrix[1].append((sql.SQL, False))

    # exercise with "Composed" SQL object
    _test_matrix[1].append((lambda q: sql.Composed([sql.SQL(q)]), True))
    _test_matrix[1].append((lambda q: sql.Composed([sql.SQL(q)]), False))


# Tests
@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_enable_instance(wrapper, use_cur_context):
    _exercise_db(cursor_factory=None, use_cur_context=use_cur_context,
            row_type=tuple, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_disable_instance(wrapper, use_cur_context):
    _exercise_db(cursor_factory=None, use_cur_context=use_cur_context,
            row_type=tuple, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_dict_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_enable_instance(wrapper, use_cur_context):
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, use_cur_context=use_cur_context,
            row_type=dict, wrapper=wrapper)


@pytest.mark.parametrize(*_test_matrix)
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
        'test_cursor:test_execute_via_cursor_dict_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@background_task()
def test_execute_via_cursor_dict_disable_instance(wrapper, use_cur_context):
    dict_factory = psycopg2.extras.RealDictCursor
    _exercise_db(cursor_factory=dict_factory, use_cur_context=use_cur_context,
            row_type=dict, wrapper=wrapper)
