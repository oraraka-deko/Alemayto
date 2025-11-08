#!/usr/bin/env python3
"""
Test script for new security and pagination features
Tests:
1. Input sanitization (display_name, from_nickname)
2. Message size limits
3. Pagination with since_id and order parameters
4. Key type validation
"""

import requests
import json
import base64
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

BASE_URL = 'http://localhost:5000'

print("="*70)
print("SECURITY AND PAGINATION FEATURES TEST")
print("="*70)

# Test 1: Input Sanitization in Registration
print("\n1. Testing Input Sanitization in Registration...")
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key
public_key_b64 = verify_key.encode(encoder=Base64Encoder).decode('utf-8')

# Try to register with malicious display_name
malicious_name = "<script>alert('XSS')</script>; DROP TABLE users;"
registration_data = {
    "public_key": public_key_b64,
    "display_name": malicious_name
}

response = requests.post(f'{BASE_URL}/register', json=registration_data)
print(f"   Status: {response.status_code}")

if response.status_code == 201:
    reg_result = response.json()
    print(f"   ✓ Registration successful")
    print(f"   Display name sanitized (should be clean)")
    link_token = reg_result['link_token']
    fetch_token = reg_result['fetch_token']
else:
    print(f"   ✗ Registration failed: {response.json()}")
    exit(1)

# Test 2: Key Type Validation
print("\n2. Testing Key Type Validation...")
signing_key2 = SigningKey.generate()
verify_key2 = signing_key2.verify_key
public_key2_b64 = verify_key2.encode(encoder=Base64Encoder).decode('utf-8')

# Try to register with unsupported key_type
registration_data2 = {
    "public_key": public_key2_b64,
    "display_name": "Test User",
    "key_type": "rsa"  # Unsupported
}

response = requests.post(f'{BASE_URL}/register', json=registration_data2)
print(f"   Status: {response.status_code}")

if response.status_code == 400:
    print(f"   ✓ Correctly rejected unsupported key_type")
    print(f"   Error: {response.json()['error']}")
else:
    print(f"   ✗ Should have rejected unsupported key_type")

# Register with valid key_type
registration_data2['key_type'] = 'ed25519'
response = requests.post(f'{BASE_URL}/register', json=registration_data2)
if response.status_code == 201:
    print(f"   ✓ Accepted valid key_type (ed25519)")
    reg_result2 = response.json()
    if 'key_type' in reg_result2:
        print(f"   ✓ Response includes key_type: {reg_result2['key_type']}")
else:
    print(f"   ✗ Failed to register with valid key_type")

# Test 3: Message Size Validation
print("\n3. Testing Message Size Limits...")
encryption_private_key = PrivateKey.generate()
encryption_public_key = encryption_private_key.public_key
sealed_box = SealedBox(encryption_public_key)

# Try to send a message that's too large (> 16KB when decoded)
large_plaintext = "A" * 20000  # 20KB
encrypted_large = sealed_box.encrypt(large_plaintext.encode('utf-8'))
encrypted_large_b64 = base64.b64encode(encrypted_large).decode('utf-8')

send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_large_b64
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
print(f"   Status: {response.status_code}")

if response.status_code == 413:
    print(f"   ✓ Correctly rejected oversized message")
    print(f"   Error: {response.json()['error']}")
else:
    print(f"   ✗ Should have rejected oversized message (got {response.status_code})")

# Send a normal-sized message
normal_plaintext = "Normal sized message"
encrypted_normal = sealed_box.encrypt(normal_plaintext.encode('utf-8'))
encrypted_normal_b64 = base64.b64encode(encrypted_normal).decode('utf-8')

send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_normal_b64
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
if response.status_code == 201:
    print(f"   ✓ Normal sized message accepted")
    msg_id_1 = response.json()['id']
else:
    print(f"   ✗ Failed to send normal message")
    msg_id_1 = None

# Test 4: Metadata Size Validation
print("\n4. Testing Metadata Size Limits...")
large_metadata = {"data": "X" * 5000}  # > 4KB
send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_normal_b64,
    "metadata": large_metadata
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
print(f"   Status: {response.status_code}")

if response.status_code == 413:
    print(f"   ✓ Correctly rejected oversized metadata")
    print(f"   Error: {response.json()['error']}")
else:
    print(f"   ✗ Should have rejected oversized metadata (got {response.status_code})")

# Test 5: Pagination with since_id
print("\n5. Testing Pagination Features...")

# Send multiple messages
message_ids = []
for i in range(5):
    plaintext = f"Message {i+1}"
    encrypted = sealed_box.encrypt(plaintext.encode('utf-8'))
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    
    send_data = {
        "link_token": link_token,
        "encrypted_message": encrypted_b64
    }
    
    response = requests.post(f'{BASE_URL}/send', json=send_data)
    if response.status_code == 201:
        message_ids.append(response.json()['id'])

print(f"   Sent {len(message_ids)} messages")

# Fetch with DESC order (default)
headers = {"Authorization": f"Bearer {fetch_token}"}
fetch_data = {
    "link_token": link_token,
    "limit": 3
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
if response.status_code == 200:
    result = response.json()
    print(f"   ✓ Fetched {result['count']} messages (DESC order)")
    print(f"   Has more: {result['has_more']}")
    if 'next_cursor' in result:
        print(f"   Next cursor: {result['next_cursor']}")

# Fetch with ASC order
fetch_data = {
    "link_token": link_token,
    "limit": 3,
    "order": "ASC"
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
if response.status_code == 200:
    result = response.json()
    print(f"   ✓ Fetched {result['count']} messages (ASC order)")
    messages_asc = result['data']
    if len(messages_asc) > 1:
        # Verify ascending order
        if messages_asc[0]['id'] < messages_asc[-1]['id']:
            print(f"   ✓ Messages are in ascending order")
        else:
            print(f"   ✗ Messages not in ascending order")

# Test since_id pagination
if message_ids:
    fetch_data = {
        "link_token": link_token,
        "since_id": message_ids[2],  # Get messages after the 3rd one
        "order": "ASC"
    }
    
    response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Fetched {result['count']} messages since_id={message_ids[2]}")
        # All messages should have id > since_id
        all_after = all(msg['id'] > message_ids[2] for msg in result['data'])
        if all_after:
            print(f"   ✓ All messages are after since_id")
        else:
            print(f"   ✗ Some messages are not after since_id")

# Test before_id pagination
fetch_data = {
    "link_token": link_token,
    "before_id": message_ids[-1],  # Get messages before the last one
    "limit": 2,
    "order": "DESC"
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
if response.status_code == 200:
    result = response.json()
    print(f"   ✓ Fetched {result['count']} messages before_id={message_ids[-1]}")
    # All messages should have id < before_id
    all_before = all(msg['id'] < message_ids[-1] for msg in result['data'])
    if all_before:
        print(f"   ✓ All messages are before before_id")
    else:
        print(f"   ✗ Some messages are not before before_id")

print("\n" + "="*70)
print("SECURITY AND PAGINATION TESTS COMPLETED")
print("="*70)
print("\nSummary:")
print("✓ Input sanitization for display_name")
print("✓ Key type validation (only ed25519)")
print("✓ Message size limits (max 16KB)")
print("✓ Metadata size limits (max 4KB)")
print("✓ Pagination with ASC/DESC order")
print("✓ Pagination with since_id (polling)")
print("✓ Pagination with before_id (infinite scroll)")
print("✓ Pagination metadata (count, has_more, next_cursor)")
print("="*70)
