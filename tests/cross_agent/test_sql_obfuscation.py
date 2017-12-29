import json
import os
import pytest

from newrelic.core.database_utils import SQLStatement


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'sql_obfuscation'))

_parameters_list = ['obfuscated', 'dialects', 'sql', 'malformed',
        'pathological']
_parameters = ','.join(_parameters_list)


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'sql_obfuscation.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result


_quoting_styles = {
    'sqlite': 'single',
    'mysql': 'single+double',
    'postgres': 'single+dollar',
    'oracle': 'single+oracle',
    'cassandra': 'single',
}


def get_quoting_styles(dialects):
    return set([_quoting_styles.get(dialect) for dialect in dialects])


class DummyDB(object):
    def __init__(self, quoting_style):
        self.quoting_style = quoting_style


@pytest.mark.parametrize(_parameters, load_tests())
def test_sql_obfuscation(obfuscated, dialects, sql, malformed, pathological):

    if malformed or pathological:
        pytest.skip()

    quoting_styles = get_quoting_styles(dialects)

    for quoting_style in quoting_styles:
        database = DummyDB(quoting_style)
        statement = SQLStatement(sql, database)
        actual_obfuscated = statement.obfuscated
        assert actual_obfuscated in obfuscated
