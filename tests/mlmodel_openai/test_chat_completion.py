# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import openai
import pytest
from testing_support.fixtures import (  # function_not_called,; override_application_settings,
    function_not_called,
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction, add_custom_attribute
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_event_payload import (
    validate_ml_event_payload,
)
from testing_support.validators.validate_ml_events import validate_ml_events
from testing_support.validators.validate_ml_events_outside_transaction import (
    validate_ml_events_outside_transaction,
)

import newrelic.core.otlp_utils
from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_ml_event
from newrelic.core.config import global_settings
from newrelic.packages import six

_test_openai_chat_completion_sync_messages = (
    {"role": "system", "content": "You are a scientist."},
    {"role": "user", "content": "What is 212 degrees Fahrenheit converted to Celsius?"},
)


def set_trace_info():
    txn = current_transaction()
    if txn:
        txn._trace_id = "trace-id"
    trace = current_trace()
    if trace:
        trace.guid = "span-id"


sync_chat_completion_recorded_events = [
    (
        {'type': 'LlmChatCompletionSummary'},
        {
            'id': None, # UUID that varies with each run
            'appName': 'Python Agent Test (mlmodel_openai)',
            'conversation_id': 'my-awesome-id',
            'transaction_id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            'api_key_last_four_digits': 'sk-CRET',
            'response_time': None, # Response time varies each test run
            'request.model': 'gpt-3.5-turbo',
            'response.model': 'gpt-3.5-turbo-0613',
            'response.organization': 'new-relic-nkmd8b',
            'response.usage.completion_tokens': 11,
            'response.usage.total_tokens': 64,
            'response.usage.prompt_tokens': 53,
            'request.temperature': 0.7,
            'request.max_tokens': 100,
            'response.choices.finish_reason': 'stop',
            'response.api_type': 'None',
            'response.headers.llmVersion': '2020-10-01',
            'response.headers.ratelimitLimitRequests': 200,
            'response.headers.ratelimitLimitTokens': 40000,
            'response.headers.ratelimitResetTokens': "90ms",
            'response.headers.ratelimitResetRequests': "7m12s",
            'response.headers.ratelimitRemainingTokens': 39940,
            'response.headers.ratelimitRemainingRequests': 199,
            'vendor': 'openAI',
            'ingest_source': 'Python',
            'number_of_messages': 3,
            'api_version': '2020-10-01'
        },
    ),
    (
        {'type': 'LlmChatCompletionMessage'},
        {
            'id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            'transaction_id': None,
            'content': 'You are a scientist.',
            'role': 'system',
            'completion_id': None,
            'sequence': 0,
            'model': 'gpt-3.5-turbo-0613',
            'vendor': 'openAI',
            'ingest_source': 'Python'
        },
    ),
    (
        {'type': 'LlmChatCompletionMessage'},
        {
            'id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            'transaction_id': None,
            'content': 'What is 212 degrees Fahrenheit converted to Celsius?',
            'role': 'user',
            'completion_id': None,
            'sequence': 1,
            'model': 'gpt-3.5-turbo-0613',
            'vendor': 'openAI',
            'ingest_source': 'Python'
        },
    ),
    (
        {'type': 'LlmChatCompletionMessage'},
        {
            'id': None,
            'span_id': "span-id",
            'trace_id': "trace-id",
            'transaction_id': None,
            'content': '212 degrees Fahrenheit is equal to 100 degrees Celsius.',
            'role': 'assistant',
            'completion_id': None,
            'sequence': 2,
            'model': 'gpt-3.5-turbo-0613',
            'vendor': 'openAI',
            'ingest_source': 'Python'
        }
    ),
]


@reset_core_stats_engine()
@validate_ml_events(sync_chat_completion_recorded_events)
# One summary event, one system message, one user message, and one response message from the assistant
@validate_ml_event_count(count=4)
@background_task()
def test_openai_chat_completion_sync_in_txn():
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_chat_completion_sync_outside_txn():
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")
    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


disabled_ml_settings = {
    "machine_learning.enabled": False,
    "machine_learning.inference_events_value.enabled": False,
    "ml_insights_events.enabled": False
}


@override_application_settings(disabled_ml_settings)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_chat_completion_sync_disabled_settings():
    set_trace_info()
    openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=_test_openai_chat_completion_sync_messages,
        temperature=0.7,
        max_tokens=100
    )


def test_openai_chat_completion_async(loop):
    loop.run_until_complete(
        openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=_test_openai_chat_completion_sync_messages,
        )
    )
