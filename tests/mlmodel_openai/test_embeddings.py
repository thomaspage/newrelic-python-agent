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
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_ml_event_count import validate_ml_event_count
from testing_support.validators.validate_ml_events import validate_ml_events

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute


def test_openai_embedding_sync():
    openai.Embedding.create(input="This is an embedding test.", model="text-embedding-ada-002")


enabled_ml_insights_events = {"ml_insights_events.enabled": True}
disabled_ml_insights_events = {"ml_insights_events.enabled": False}


@override_application_settings(enabled_ml_insights_events)
@reset_core_stats_engine()
@validate_ml_events(
    [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_openai)",
                "conversation_id": "",
                "transaction_id": None,  # Varies with each run.
                "span_id": "span-id",
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "api_key_last_four_digits": "sk-CRET",
                "request.model": "text-embedding-ada-002",
                "response.model": "text-embedding-ada-002-v2",
                "response.organization": "new-relic-nkmd8b",
                "response.usage.total_tokens": 6,
                "response.usage.prompt_tokens": 6,
                "response.api_type": "None",
                "vendor": "openAI",
                # instrumentation.provider is attached to all ml_events and asserted in the payload tests
                "response.headers.llmVersion": "2020-10-01",
                "response.headers.ratelimitLimitRequests": 200,
                "response.headers.ratelimitLimitTokens": 150000,
                "response.headers.ratelimitResetTokens": "2ms",
                "response.headers.ratelimitResetRequests": "19m45.394s",
                "response.headers.ratelimitRemainingTokens": 149994,
                "response.headers.ratelimitRemainingRequests": 197,
                "duration": None,  # Varies with each run.
            },
        ),
    ]
)
@validate_ml_event_count(count=1)
@background_task()
def test_openai_embedding_async_conversation_id_unset(loop, set_trace_info):
    set_trace_info()

    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@override_application_settings(enabled_ml_insights_events)
@reset_core_stats_engine()
@validate_ml_events(
    [
        (
            {"type": "LlmEmbedding"},
            {
                "id": None,  # UUID that varies with each run
                "appName": "Python Agent Test (mlmodel_openai)",
                "conversation_id": "my-awesome-id",
                "transaction_id": None,  # Varies with each run.
                "span_id": "span-id",
                "trace_id": "trace-id",
                "input": "This is an embedding test.",
                "api_key_last_four_digits": "sk-CRET",
                "request.model": "text-embedding-ada-002",
                "response.model": "text-embedding-ada-002-v2",
                "response.organization": "new-relic-nkmd8b",
                "response.usage.total_tokens": 6,
                "response.usage.prompt_tokens": 6,
                "response.api_type": "None",
                "vendor": "openAI",
                # instrumentation.provider is attached to all ml_events and asserted in the payload tests
                "response.headers.llmVersion": "2020-10-01",
                "response.headers.ratelimitLimitRequests": 200,
                "response.headers.ratelimitLimitTokens": 150000,
                "response.headers.ratelimitResetTokens": "2ms",
                "response.headers.ratelimitResetRequests": "19m45.394s",
                "response.headers.ratelimitRemainingTokens": 149994,
                "response.headers.ratelimitRemainingRequests": 197,
                "duration": None,  # Varies with each run.
            },
        ),
    ]
)
@validate_ml_event_count(count=1)
@background_task()
def test_openai_embedding_async_conversation_id_set(loop, set_trace_info):
    set_trace_info()
    add_custom_attribute("conversation_id", "my-awesome-id")

    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@override_application_settings(enabled_ml_insights_events)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
def test_openai_embedding_async_outside_transaction(loop):
    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )


@override_application_settings(disabled_ml_insights_events)
@reset_core_stats_engine()
@validate_ml_event_count(count=0)
@background_task()
def test_openai_embedding_async_disabled_ml_insights_events(loop):
    loop.run_until_complete(
        openai.Embedding.acreate(input="This is an embedding test.", model="text-embedding-ada-002")
    )
