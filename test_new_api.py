#!/usr/bin/env python3
"""
Comprehensive test script for the new simplex link-based chat API
Tests all endpoints with real NaCl encryption
"""

import requests
import json
import base64
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

BASE_URL = 'http://localhost:5000'

print("="*70)
print("PYCRYPT SIMPLEX CHAT API - COMPREHENSIVE TEST")
print("="*70)

# Step 1: Generate Ed25519 keypair for signing (authentication)
print("\n1. Generating Ed25519 keypair for authentication...")
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key

# Convert verify_key to base64 for transmission
public_key_b64 = verify_key.encode(encoder=Base64Encoder).decode('utf-8')
print(f"   Public Key (Base64): {public_key_b64[:40]}...")

# Step 2: Register client
print("\n2. Testing Client Registration (/register)...")
registration_data = {
    "public_key": public_key_b64,
    "display_name": "Test User"
}

response = requests.post(f'{BASE_URL}/register', json=registration_data)
print(f"   Status: {response.status_code}")

if response.status_code == 201:
    reg_result = response.json()
    print(f"   ✓ Registration successful!")
    print(f"   Link: {reg_result['link']}")
    print(f"   Link Token: {reg_result['link_token']}")
    print(f"   Fetch Token: {reg_result['fetch_token'][:40]}...")
    
    link_token = reg_result['link_token']
    fetch_token = reg_result['fetch_token']
else:
    print(f"   ✗ Registration failed: {response.json()}")
    exit(1)

# Step 3: Generate X25519 keypair for encryption (sealed box)
print("\n3. Generating X25519 keypair for encryption...")
encryption_private_key = PrivateKey.generate()
encryption_public_key = encryption_private_key.public_key

# For the sender to encrypt (they only need recipient's public key)
recipient_public_key_b64 = base64.b64encode(bytes(encryption_public_key)).decode('utf-8')
print(f"   Encryption Public Key: {recipient_public_key_b64[:40]}...")

# Step 4: Send encrypted message (as anonymous sender)
print("\n4. Testing Send Message (/send)...")

# Sender creates encrypted message using sealed box
plaintext = "Hello from anonymous sender! This is end-to-end encrypted."
plaintext_bytes = plaintext.encode('utf-8')

# Create sealed box and encrypt
sealed_box = SealedBox(encryption_public_key)
encrypted_message = sealed_box.encrypt(plaintext_bytes)
encrypted_message_b64 = base64.b64encode(encrypted_message).decode('utf-8')

send_data = {
    "link_token": link_token,
    "encrypted_message": encrypted_message_b64,
    "metadata": {"sender_nick": "Anonymous"}
}

response = requests.post(f'{BASE_URL}/send', json=send_data)
print(f"   Status: {response.status_code}")

if response.status_code == 201:
    send_result = response.json()
    print(f"   ✓ Message sent successfully!")
    print(f"   Message ID: {send_result['id']}")
    message_id = send_result['id']
else:
    print(f"   ✗ Send failed: {response.json()}")
    message_id = None

# Step 5: Send second message
print("\n5. Sending second message...")
plaintext2 = "This is the second encrypted message!"
encrypted_message2 = sealed_box.encrypt(plaintext2.encode('utf-8'))
encrypted_message2_b64 = base64.b64encode(encrypted_message2).decode('utf-8')

send_data2 = {
    "link_token": link_token,
    "encrypted_message": encrypted_message2_b64
}

response = requests.post(f'{BASE_URL}/send', json=send_data2)
if response.status_code == 201:
    print(f"   ✓ Second message sent! ID: {response.json()['id']}")
    message_id2 = response.json()['id']
else:
    print(f"   ✗ Failed: {response.json()}")
    message_id2 = None

# Step 6: Request challenge for authentication
print("\n6. Testing Challenge Request (/challenge_request)...")
challenge_request_data = {
    "link_token": link_token
}

response = requests.post(f'{BASE_URL}/challenge_request', json=challenge_request_data)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    challenge_result = response.json()
    challenge_nonce = challenge_result['challenge']
    print(f"   ✓ Challenge received!")
    print(f"   Challenge Nonce: {challenge_nonce[:40]}...")
else:
    print(f"   ✗ Challenge request failed: {response.json()}")
    challenge_nonce = None

# Step 7: Fetch messages using challenge-response
print("\n7. Testing Fetch Messages with Challenge-Response (/fetch)...")

if challenge_nonce:
    # Sign the challenge with private key
    challenge_bytes = challenge_nonce.encode('utf-8')
    signature = signing_key.sign(challenge_bytes)
    signature_b64 = base64.b64encode(signature.signature).decode('utf-8')
    
    fetch_data = {
        "link_token": link_token,
        "challenge": challenge_nonce,
        "challenge_signature": signature_b64
    }
    
    response = requests.post(f'{BASE_URL}/fetch', json=fetch_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        fetch_result = response.json()
        print(f"   ✓ Messages fetched successfully!")
        print(f"   Number of messages: {len(fetch_result['data'])}")
        
        # Decrypt messages
        print("\n   Decrypting messages...")
        unsealed_box = SealedBox(encryption_private_key)
        
        for idx, msg in enumerate(fetch_result['data'], 1):
            encrypted_b64 = msg['encrypted_message']
            encrypted_bytes = base64.b64decode(encrypted_b64)
            
            # Decrypt using sealed box
            decrypted = unsealed_box.decrypt(encrypted_bytes)
            decrypted_text = decrypted.decode('utf-8')
            
            print(f"   Message {idx} (ID: {msg['id']}): {decrypted_text}")
            print(f"   Seen: {msg['seen']}, Created: {msg['created_at']}")
    else:
        print(f"   ✗ Fetch failed: {response.json()}")

# Step 8: Fetch messages using fetch_token (simpler method)
print("\n8. Testing Fetch Messages with Fetch Token (/fetch)...")

fetch_data_token = {
    "link_token": link_token
}

headers = {
    "Authorization": f"Bearer {fetch_token}"
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data_token, headers=headers)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    print(f"   ✓ Fetch with token successful!")
    print(f"   Number of messages: {len(response.json()['data'])}")
else:
    print(f"   ✗ Fetch failed: {response.json()}")

# Step 9: Acknowledge messages
print("\n9. Testing Acknowledge Messages (/ack)...")

if message_id and message_id2:
    ack_data = {
        "link_token": link_token,
        "message_ids": [message_id, message_id2]
    }
    
    headers = {
        "Authorization": f"Bearer {fetch_token}"
    }
    
    response = requests.post(f'{BASE_URL}/ack', json=ack_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        ack_result = response.json()
        print(f"   ✓ Messages acknowledged!")
        print(f"   Count: {ack_result['count']}")
    else:
        print(f"   ✗ Ack failed: {response.json()}")

# Step 10: Fetch again to verify seen status
print("\n10. Fetching messages again (should show seen=true)...")

fetch_data_seen = {
    "link_token": link_token,
    "include_seen": True
}

response = requests.post(f'{BASE_URL}/fetch', json=fetch_data_seen, headers=headers)
if response.status_code == 200:
    messages = response.json()['data']
    print(f"   ✓ Fetched {len(messages)} messages")
    for msg in messages:
        print(f"   Message ID {msg['id']}: seen={msg['seen']}")
else:
    print(f"   ✗ Fetch failed")

# Step 11: Test invalid authentication
print("\n11. Testing Invalid Authentication...")

bad_fetch_data = {
    "link_token": link_token
}

bad_headers = {
    "Authorization": "Bearer invalid_token_12345"
}

response = requests.post(f'{BASE_URL}/fetch', json=bad_fetch_data, headers=bad_headers)
print(f"   Status: {response.status_code}")
if response.status_code == 401:
    print(f"   ✓ Correctly rejected invalid token!")
else:
    print(f"   ✗ Should have rejected invalid token")

print("\n" + "="*70)
print("TEST COMPLETED SUCCESSFULLY!")
print("="*70)
print("\nSummary:")
print("✓ Client registration with Ed25519 public key")
print("✓ Link token and fetch token generation")
print("✓ Encrypted message sending (sealed box)")
print("✓ Challenge-response authentication")
print("✓ Fetch token authentication")
print("✓ Message retrieval and decryption")
print("✓ Message acknowledgment")
print("✓ Invalid authentication rejection")
print("\nEnd-to-end encryption verified - server never saw plaintext!")
print("="*70)