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

import json

_test_bedrock_chat_completion_body = json.dumps(
    {"inputText": "Command: Write me a blog about making strong business decisions as a leader.\n\nBlog:"}
)


def test_bedrock_chat_completion(bedrock_server):
    response = bedrock_server.invoke_model(
        body=_test_bedrock_chat_completion_body,
        modelId="amazon.titan-text-express-v1",
        accept="application/json",
        contentType="application/json",
    )

    print(f"titan large response: {response}")
    response_body = json.loads(response.get("body").read())
    print(f"titan large body: {response_body}")

    text = response_body.get("results")[0].get("outputText")
    assert text
    print(text)
