#!/usr/bin/env python3
import sys
import asyncio
import httpx
import subprocess
import uuid
from a2a.client import create_client, ClientConfig
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import Message, Role, Part, SendMessageRequest
from a2a.utils.constants import TransportProtocol
from google.protobuf.json_format import MessageToDict

BASE_URL = 'https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/640123829561/locations/us-east1/reasoningEngines/1108086718961025024/api/a2a/app'

async def query(prompt: str):
    token = subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()
    headers = {'Authorization': f'Bearer {token}'}
    async with httpx.AsyncClient(headers=headers, timeout=120) as http_client:
        config = ClientConfig(
            httpx_client=http_client,
            supported_protocol_bindings=[TransportProtocol.JSONRPC, TransportProtocol.HTTP_JSON],
        )
        client = await create_client(BASE_URL, config)
        client._transport = JsonRpcTransport(http_client, client._card, BASE_URL)
        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text=prompt)],
        )
        print(f"[user]: {prompt}")
        async for chunk in client.send_message(SendMessageRequest(message=msg)):
            d = MessageToDict(chunk)
            if 'statusUpdate' in d and 'message' in d['statusUpdate']:
                m = d['statusUpdate']['message']
                for part in m.get('parts', []):
                    if 'data' in part:
                        call = part['data']
                        name = call.get('name')
                        if 'args' in call:
                            print(f"[tool_call: {name}({call['args']})]")
                        elif 'response' in call:
                            print(f"[tool_response: {name} -> {call['response']}]")
                    elif 'text' in part:
                        print(f"[sample-agent]: {part['text']}")
            elif 'artifactUpdate' in d and 'artifact' in d['artifactUpdate']:
                for part in d['artifactUpdate']['artifact'].get('parts', []):
                    if 'text' in part:
                        print(f"[sample-agent]: {part['text']}")

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else "What is the weather in SF?"
    asyncio.run(query(prompt))
