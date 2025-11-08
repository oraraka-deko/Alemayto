#!/usr/bin/env python3
"""
Test script for new permission-based messaging endpoints
"""

import requests
import base64
from nacl.signing import SigningKey
from nacl.public import PrivateKey, SealedBox
from nacl.encoding import Base64Encoder

# Server URL
BASE_URL = "http://localhost:5000"

def test_permission_workflow():
    """Test the complete permission-based messaging workflow"""
    
    print("\n=== Testing Permission-Based Messaging Workflow ===\n")
    
    # Step 1: Create two clients (Alice and Bob)
    print("Step 1: Registering two clients (Alice and Bob)...")
    
    # Alice's keys
    alice_signing_key = SigningKey.generate()
    alice_public_key_b64 = base64.b64encode(bytes(alice_signing_key.verify_key)).decode()
    
    response = requests.post(f"{BASE_URL}/register", json={
        'public_key': alice_public_key_b64,
        'display_name': 'Alice'
    })
    alice_data = response.json()
    alice_link_token = alice_data['link_token']
    alice_fetch_token = alice_data['fetch_token']
    print(f"✓ Alice registered: {alice_link_token}")
    
    # Bob's keys
    bob_signing_key = SigningKey.generate()
    bob_public_key_b64 = base64.b64encode(bytes(bob_signing_key.verify_key)).decode()
    
    response = requests.post(f"{BASE_URL}/register", json={
        'public_key': bob_public_key_b64,
        'display_name': 'Bob'
    })
    bob_data = response.json()
    bob_link_token = bob_data['link_token']
    bob_fetch_token = bob_data['fetch_token']
    print(f"✓ Bob registered: {bob_link_token}")
    
    # Step 2: Bob checks if Alice exists
    print("\nStep 2: Bob checking if Alice's contact exists...")
    response = requests.post(f"{BASE_URL}/check_contact", json={
        'link_token': alice_link_token
    })
    contact_info = response.json()
    print(f"✓ Contact exists: {contact_info['exists']}")
    print(f"  Nickname: {contact_info.get('nickname')}")
    
    # Step 3: Bob requests permission to message Alice
    print("\nStep 3: Bob requesting permission to message Alice...")
    response = requests.post(f"{BASE_URL}/request_message_permission", json={
        'from_link_token': bob_link_token,
        'to_link_token': alice_link_token,
        'from_nickname': 'Bob'
    })
    request_data = response.json()
    request_id = request_data['request_id']
    print(f"✓ Permission request sent: Request ID {request_id}")
    
    # Step 4: Alice fetches her message requests
    print("\nStep 4: Alice fetching message requests...")
    response = requests.post(f"{BASE_URL}/get_message_requests", 
        json={'link_token': alice_link_token},
        headers={'Authorization': f'Bearer {alice_fetch_token}'}
    )
    requests_data = response.json()
    print(f"✓ Found {len(requests_data['data'])} pending request(s)")
    for req in requests_data['data']:
        print(f"  From: {req['from_nickname']} ({req['from_link_token']})")
    
    # Step 5: Alice accepts Bob's request
    print("\nStep 5: Alice accepting Bob's request...")
    response = requests.post(f"{BASE_URL}/respond_message_request", 
        json={
            'link_token': alice_link_token,
            'request_id': request_id,
            'action': 'accept'
        },
        headers={'Authorization': f'Bearer {alice_fetch_token}'}
    )
    accept_data = response.json()
    print(f"✓ Request {accept_data['status']}")
    
    # Step 6: Bob tries to send message to Alice (should succeed now)
    print("\nStep 6: Bob sending encrypted message to Alice...")
    
    # Create encryption keys for the message
    alice_encryption_key = PrivateKey.generate()
    alice_public_encryption_key = alice_encryption_key.public_key
    
    # Bob encrypts a message for Alice
    message = b"Hello Alice! This is Bob. Permission granted!"
    sealed_box = SealedBox(alice_public_encryption_key)
    encrypted = sealed_box.encrypt(message)
    encrypted_b64 = base64.b64encode(encrypted).decode()
    
    response = requests.post(f"{BASE_URL}/send", json={
        'link_token': alice_link_token,
        'from_link_token': bob_link_token,
        'encrypted_message': encrypted_b64
    })
    
    if response.status_code == 201:
        print(f"✓ Message sent successfully (ID: {response.json()['id']})")
    else:
        print(f"✗ Failed to send message: {response.json()}")
    
    # Step 7: Test - Try another user without permission (should fail)
    print("\nStep 7: Testing permission enforcement...")
    
    charlie_signing_key = SigningKey.generate()
    charlie_public_key_b64 = base64.b64encode(bytes(charlie_signing_key.verify_key)).decode()
    
    response = requests.post(f"{BASE_URL}/register", json={
        'public_key': charlie_public_key_b64,
        'display_name': 'Charlie'
    })
    charlie_data = response.json()
    charlie_link_token = charlie_data['link_token']
    print(f"✓ Charlie registered: {charlie_link_token}")
    
    # Charlie tries to send without permission
    response = requests.post(f"{BASE_URL}/send", json={
        'link_token': alice_link_token,
        'from_link_token': charlie_link_token,
        'encrypted_message': encrypted_b64
    })
    
    if response.status_code == 403:
        print(f"✓ Permission correctly denied for Charlie")
        print(f"  Error: {response.json()['error']}")
    else:
        print(f"✗ Permission check failed - Charlie was allowed to send")
    
    # Step 8: Anonymous sending (backward compatible - no from_link_token)
    print("\nStep 8: Testing anonymous sending (backward compatible)...")
    response = requests.post(f"{BASE_URL}/send", json={
        'link_token': alice_link_token,
        'encrypted_message': encrypted_b64
    })
    
    if response.status_code == 201:
        print(f"✓ Anonymous message sent successfully")
    else:
        print(f"✗ Anonymous sending failed")
    
    print("\n=== Permission Workflow Test Complete ===\n")

if __name__ == '__main__':
    test_permission_workflow()
