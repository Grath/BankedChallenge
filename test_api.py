import json
import pytest
import requests
import time
from faker import Faker
from urllib.parse import urlparse
from uuid import uuid4

fake = Faker()


def test_successful_transaction():
    create_resp = requests.post("https://demo.banked.com/new/api/create-demo-payment",
                                json={"line_items": "single", "region": "AU", "customer": "new-customer", "checkoutV3Header": True})
    assert create_resp.status_code == 200
    create_json = json.loads(create_resp.text)
    assert "url" in create_json
    assert "id" in create_json
    token_query = urlparse(create_json["url"]).query
    sessions_resp = requests.post(f"https://api.banked.com/checkout/v3/sessions?checkout_region=au&{token_query}",
                                  headers={"Idempotency-Key":str(uuid4())},
                                  json={"locale": None, "payment_id": create_json["id"]})
    assert sessions_resp.status_code == 201
    sessions_json = json.loads(sessions_resp.text)
    assert "actions" in sessions_json
    for action in sessions_json["actions"]:
        if action["action"] == "select_provider":
            for provider in action["data"]["providers"]:
                if provider["name"] == "Mock Bank AU":
                    provider_id = provider["id"]
                    break
            else:
                pytest.fail(f"Mock Bank AU provider not found in sessions response, got:\n{json.dumps(sessions_json, indent=2)}")

            select_provider_resp = requests.patch(f"{action['href']}?checkout_region=au&{token_query}",
                                                  headers={"Idempotency-Key":str(uuid4())},
                                                  json={"provider_id": provider_id})
            break
    else:
        pytest.fail(f"There is no select_provider action in sessions response, got:\n{json.dumps(sessions_json, indent=2)}")
    assert select_provider_resp.status_code == 200
    select_provider_json = json.loads(select_provider_resp.text)
    assert "actions" in select_provider_json
    for action in select_provider_json["actions"]:
        if action["action"] == "initiate_authorisation":
            initiate_authorisation_resp = requests.patch(f"{action['href']}?checkout_region=au&{token_query}",
                                                         headers={"Idempotency-Key": str(uuid4())},
                                                         json={"terms_accepted": True, "remember_me": False, "masked_details": False,
                                                               "supplemental_checkout_attributes": {
                                                                   "ACCOUNT_NAME": fake.name(),
                                                                   "ACCOUNT_NUMBER": "12345678",
                                                                   "BSB_NUMBER": "111114"
                                                               }})
            break
    else:
        pytest.fail(f"There is no initiate_authorisation action in select_provider response, got:\n{json.dumps(select_provider_json, indent=2)}")
    assert initiate_authorisation_resp.status_code == 200
    for wait in range(20):
        initiate_authorisation_json = json.loads(initiate_authorisation_resp.text)
        checkout_resp = requests.get(f"https://api.banked.com/checkout/v3/sessions/{initiate_authorisation_json['id']}?checkout_region=au&{token_query}")
        assert checkout_resp.status_code == 200
        checkout_json = json.loads(checkout_resp.text)
        assert "payment" in checkout_json
        if checkout_json["payment"]["state"] not in ["awaiting_authorisation", "pending"]:
            break
        time.sleep(wait)
    assert checkout_json["payment"]["state"] == "sent"

