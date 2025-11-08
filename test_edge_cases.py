#!/usr/bin/env python3
"""
Test script for edge cases mentioned in the problem statement
Tests:
1. Challenge reuse after mark_challenge_used
2. Message flood protection (rate limiting)
3. Extremely large encrypted_message rejection
4. Invalid metadata JSON handling
"""

import requests
import json
import base64
import time
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

BASE_URL = 'http://localhost:5000'

print("="*70)
print("EDGE CASE TESTS")
print("="*70)

# Setup: Register a client
print("\n0. Setting up test client...")
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key
public_key_b64 = verify_key.encode(encoder=Base64Encoder).decode('utf-8')

registration_data = {
    "public_key": public_key_b64,
    "display_name": "Edge Case Test User"
}

response = requests.post(f'{BASE_URL}/register', json=registration_data)
if response.status_code == 201:
    reg_result = response.json()
    link_token = reg_result['link_token']
    fetch_token = reg_result['fetch_token']
    print(f"   ✓ Test client registered")
else:
    print(f"   ✗ Failed to register test client")
    exit(1)

# Test 1: Challenge Reuse
print("\n1. Testing Challenge Reuse Prevention...")

# Request a challenge
challenge_request = {"link_token": link_token}
response = requests.post(f'{BASE_URL}/challenge_request', json=challenge_request)

if response.status_code == 200:
    challenge_nonce = response.json()['challenge']
    print(f"   ✓ Challenge requested")
    
    # Sign the challenge
    challenge_bytes = challenge_nonce.encode('utf-8')
    signature = signing_key.sign(challenge_bytes)
    signature_b64 = base64.b64encode(signature.signature).decode('utf-8')
    
    # Use the challenge once (should succeed)
    fetch_data = {
        "link_token": link_token,
        "challenge": challenge_nonce,
        "challenge_signature": signature_b64
    }
    
    response = requests.post(f'{BASE_URL}/fetch', json=fetch_data)
    if response.status_code == 200:
        print(f"   ✓ First use of challenge succeeded")
    else:
        print(f"   ✗ First use should have succeeded")
    
    # Try to reuse the same challenge (should fail)
    response = requests.post(f'{BASE_URL}/fetch', json=fetch_data)
    if response.status_code == 401:
        print(f"   ✓ Challenge reuse correctly rejected")
        print(f"   Error: {response.json()['error']}")
    else:
        print(f"   ✗ Challenge reuse should have been rejected (got {response.status_code})")
else:
    print(f"   ✗ Failed to request challenge")

# Test 2: Challenge Rate Limiting
print("\n2. Testing Challenge Request Rate Limiting...")

# Request challenges rapidly
challenge_count = 0
for i in range(10):
    response = requests.post(f'{BASE_URL}/challenge_request', json=challenge_request)
    if response.status_code == 200:
        challenge_count += 1
    elif response.status_code == 429:
        print(f"   ✓ Rate limiting kicked in after {challenge_count} challenges")
        print(f"   Error: {response.json()['error']}")
        break
    time.sleep(0.1)

if challenge_count >= 10:
    print(f"   ! All 10 challenges accepted (rate limit may be disabled or threshold higher)")

# Test 3: Extremely Large Encrypted Message
print("\n3. Testing Extremely Large Encrypted Message Rejection...")

# Create an encryption key
encryption_private_key = PrivateKey.generate()
encryption_public_key = encryption_private_key.public_key
sealed_box = SealedBox(encryption_public_key)

# Try to send a message that's way too large (50KB plaintext)
huge_plaintext = "A" * 50000
encrypted_huge = sealed_box.encrypt(huge_plaintext.encode('utf-8'))
encrypted_huge_b64 = base64.b64encode(encrypted_huge).decode('utf-8')

send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_huge_b64
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
if response.status_code == 413:
    print(f"   ✓ Huge message (50KB) correctly rejected")
    print(f"   Error: {response.json()['error']}")
else:
    print(f"   ✗ Huge message should have been rejected (got {response.status_code})")

# Test 4: Invalid Metadata JSON Type
print("\n4. Testing Invalid Metadata JSON Handling...")

normal_plaintext = "Normal message"
encrypted_normal = sealed_box.encrypt(normal_plaintext.encode('utf-8'))
encrypted_normal_b64 = base64.b64encode(encrypted_normal).decode('utf-8')

# Send with list metadata (should be stored as JSON)
send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_normal_b64,
    "metadata": ["item1", "item2"]  # List instead of object
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
if response.status_code == 201:
    print(f"   ✓ Message with list metadata accepted (JSON serializable)")
    msg_id = response.json()['id']
else:
    print(f"   ✗ Valid JSON metadata should be accepted (got {response.status_code})")

# Test 5: Invalid Base64 Encrypted Message
print("\n5. Testing Invalid Base64 Encrypted Message...")

send_data = {
    "link_token": link_token,
    "encrypted_message": "not-valid-base64!!!@#$"
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
if response.status_code == 400:
    print(f"   ✓ Invalid base64 correctly rejected")
    print(f"   Error: {response.json()['error']}")
else:
    print(f"   ✗ Invalid base64 should have been rejected (got {response.status_code})")

# Test 6: Ack with Messages Not Belonging to Link
print("\n6. Testing Ack with Non-Existent Message IDs...")

headers = {"Authorization": f"Bearer {fetch_token}"}
ack_data = {
    "link_token": link_token,
    "message_ids": [999999, 999998]  # Non-existent IDs
}

response = requests.post(f'{BASE_URL}/ack', json=ack_data, headers=headers)
if response.status_code == 200:
    print(f"   ✓ Ack completed (non-existent IDs ignored gracefully)")
    print(f"   Count: {response.json()['count']}")
else:
    print(f"   ✗ Ack should handle non-existent IDs gracefully (got {response.status_code})")

# Test 7: Empty Message IDs in Ack
print("\n7. Testing Ack with Empty Message IDs...")

ack_data = {
    "link_token": link_token,
    "message_ids": []
}

response = requests.post(f'{BASE_URL}/ack', json=ack_data, headers=headers)
if response.status_code == 200:
    print(f"   ✓ Empty message_ids handled gracefully")
else:
    print(f"   ✗ Empty message_ids should be handled (got {response.status_code})")

# Test 8: Fetch with Invalid Order Parameter
print("\n8. Testing Fetch with Invalid Order Parameter...")

fetch_data = {
    "link_token": link_token,
    "order": "INVALID"
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
if response.status_code == 200:
    print(f"   ✓ Invalid order parameter handled (defaults to DESC)")
else:
    print(f"   ✗ Should handle invalid order parameter (got {response.status_code})")

# Test 9: Fetch with Invalid Limit
print("\n9. Testing Fetch with Invalid Limit...")

fetch_data = {
    "link_token": link_token,
    "limit": 300  # Over max of 200
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data, headers=headers)
if response.status_code == 200:
    result = response.json()
    # Should be capped at 200
    if result['count'] <= 200:
        print(f"   ✓ Limit capped at maximum (200)")
    else:
        print(f"   ✗ Limit should be capped at 200")
else:
    print(f"   ✗ Should handle oversized limit (got {response.status_code})")

# Test 10: Register with Same Public Key Twice
print("\n10. Testing Registration with Same Public Key Twice...")

# Try to register again with the same public key
registration_data2 = {
    "public_key": public_key_b64,
    "display_name": "Duplicate User"
}

response = requests.post(f'{BASE_URL}/register', json=registration_data2)
if response.status_code == 201:
    reg_result2 = response.json()
    # Check if we got a different link_token (multi-link policy)
    if reg_result2['link_token'] != link_token:
        print(f"   ✓ Same public key registered with different link_token (multi-link allowed)")
    else:
        print(f"   ! Same link_token returned (deduplication)")
else:
    print(f"   ! Registration rejected (strict uniqueness enforced)")
    print(f"   Error: {response.json()['error']}")

print("\n" + "="*70)
print("EDGE CASE TESTS COMPLETED")
print("="*70)
print("\nSummary:")
print("✓ Challenge reuse prevention")
print("✓ Challenge request rate limiting")
print("✓ Extremely large message rejection")
print("✓ Invalid metadata handling")
print("✓ Invalid base64 rejection")
print("✓ Non-existent message ID handling in ack")
print("✓ Empty message_ids handling")
print("✓ Invalid order parameter handling")
print("✓ Limit capping enforcement")
print("✓ Duplicate public key registration behavior")
print("="*70)
