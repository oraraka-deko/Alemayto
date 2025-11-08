#!/usr/bin/env python3

import requests
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate test RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

print("Generated Public Key:")
print(public_pem)
print("\n" + "="*50 + "\n")

# Test 1: Health Check
print("1. Testing Health Check...")
try:
    response = requests.get('http://localhost:5000/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50 + "\n")

# Test 2: Register Client
print("2. Testing Client Registration...")
try:
    payload = {"public_key": public_pem}
    response = requests.post('http://localhost:5000/register_client', json=payload)
    print(f"Status: {response.status_code}")
    registration_data = response.json()
    print(f"Response: {registration_data}")
    
    if response.status_code == 201:
        secure_link = registration_data.get('secure_link')
        print(f"Generated Secure Link: {secure_link}")
        
        # Test 3: Store Encrypted Data
        print("\n" + "="*50 + "\n")
        print("3. Testing Store Encrypted Data...")
        
        encrypted_test_data = "This is encrypted test data (base64 encoded)"
        payload = {
            "sender_link": secure_link,
            "encrypted_data": encrypted_test_data
        }
        
        response = requests.post('http://localhost:5000/store_data', json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test 4: Get Data by Public Key
        print("\n" + "="*50 + "\n")
        print("4. Testing Get Data by Public Key...")
        
        payload = {"public_key": public_pem}
        response = requests.post('http://localhost:5000/get_data', json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test 5: Get Data by Link
        print("\n" + "="*50 + "\n")
        print("5. Testing Get Data by Secure Link...")
        
        payload = {"secure_link": secure_link}
        response = requests.post('http://localhost:5000/get_data_by_link', json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50 + "\n")
print("Testing completed!")