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

import os
import pprint

import pytest
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from _mock_external_bedrock_server import (
    MockExternalBedrockServer,
    extract_shortened_prompt,
)

from newrelic.common.object_wrapper import wrap_function_wrapper

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "ml_insights_event.enabled": True,
}
collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (mlmodel_bedrock)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (mlmodel_bedrock)"],
)

BEDROCK_AUDIT_LOG_FILE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "bedrock_audit.log")
BEDROCK_AUDIT_LOG_CONTENTS = {}


@pytest.fixture(autouse=True, scope="session")
def bedrock_server():
    """
    This fixture will either create a mocked backend for testing purposes, or will
    set up an audit log file to log responses of the real Bedrock backend to a file.
    The behavior can be controlled by setting NEW_RELIC_TESTING_RECORD_BEDROCK_RESPONSES=1 as
    an environment variable to run using the real Bedrock backend. (Default: mocking)
    """
    import boto3

    from newrelic.core.config import _environ_as_bool

    if not _environ_as_bool("NEW_RELIC_TESTING_RECORD_BEDROCK_RESPONSES", False):
        # Use mocked Bedrock backend and prerecorded responses
        with MockExternalBedrockServer() as server:
            client = boto3.client(
                "bedrock-runtime",
                "us-east-1",
                endpoint_url="http://localhost:%d" % server.port,
                aws_access_key_id="NOT-A-REAL-SECRET",
                aws_secret_access_key="NOT-A-REAL-SECRET",
            )

            yield client
    else:
        # Use real Bedrock backend and record responses
        assert (
            os.environ["AWS_ACCESS_KEY_ID"] and os.environ["AWS_SECRET_ACCESS_KEY"]
        ), "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required."

        # Construct real client
        client = boto3.client(
            "bedrock-runtime",
            "us-east-1",
        )

        # Apply function wrappers to record data
        # wrap_function_wrapper("bedrock.api_requestor", "APIRequestor.request", wrap_bedrock_api_requestor_request)
        yield client  # Run tests

        # Write responses to audit log
        with open(BEDROCK_AUDIT_LOG_FILE, "w") as audit_log_fp:
            pprint.pprint(BEDROCK_AUDIT_LOG_CONTENTS, stream=audit_log_fp)


# Intercept outgoing requests and log to file for mocking
RECORDED_HEADERS = set(["x-request-id", "content-type"])


def wrap_bedrock_api_requestor_request(wrapped, instance, args, kwargs):
    params = bind_request_params(*args, **kwargs)
    if not params:
        return wrapped(*args, **kwargs)

    prompt = extract_shortened_prompt(params)

    # Send request
    result = wrapped(*args, **kwargs)

    # Clean up data
    data = result[0].data
    headers = result[0]._headers
    headers = dict(
        filter(
            lambda k: k[0].lower() in RECORDED_HEADERS or k[0].lower().startswith("x-ratelimit"),
            headers.items(),
        )
    )

    # Log response
    BEDROCK_AUDIT_LOG_CONTENTS[prompt] = headers, data  # Append response data to audit log
    return result


def bind_request_params(method, url, params=None, *args, **kwargs):
    return params
