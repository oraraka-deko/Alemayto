import hashlib
import base64
import secrets
from nacl.public import PublicKey as NaClPublicKey
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import re

def generate_link_token():
    """
    Generate a unique link token
    Returns a URL-safe random string
    """
    # Generate 24 random bytes -> 32 character base64 string
    random_bytes = secrets.token_bytes(24)
    link_token = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    return f"link_{link_token}"

def generate_fetch_token():
    """
    Generate a secure fetch token for authentication
    Returns a long random token
    """
    # Generate 48 random bytes -> 64 character base64 string
    random_bytes = secrets.token_bytes(48)
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

def hash_token(token):
    """
    Hash a token for secure storage
    """
    return hashlib.sha256(token.encode()).hexdigest()

def generate_challenge_nonce():
    """
    Generate a random challenge nonce for authentication
    """
    random_bytes = secrets.token_bytes(32)
    return base64.b64encode(random_bytes).decode('utf-8')

def validate_public_key(public_key_b64: str) -> bool:
    """
    Validate Ed25519 public key: base64-encoded 32 bytes.
    We enforce Ed25519 only (no RSA), to match signature verification logic.
    """
    try:
        if not isinstance(public_key_b64, str):
            return False
        # Base64 decode and length check
        key_bytes = base64.b64decode(public_key_b64)
        if len(key_bytes) != 32:
            return False
        # Validate it's a valid NaCl public key (curve25519/ed25519 size)
        NaClPublicKey(key_bytes)
        # Additionally verify it's usable as Ed25519 verify key
        VerifyKey(key_bytes)
        return True
    except Exception as e:
        print(f"Public key validation error: {e}")
        return False

def verify_signature(public_key_b64, message, signature_b64):
    """
    Verify an Ed25519 signature
    public_key_b64: base64 encoded public key (32 bytes)
    message: bytes to verify
    signature_b64: base64 encoded signature
    """
    try:
        public_key_bytes = base64.b64decode(public_key_b64)
        signature_bytes = base64.b64decode(signature_b64)
        
        # Create VerifyKey from the public key
        verify_key = VerifyKey(public_key_bytes)
        
        # Verify the signature
        verify_key.verify(message, signature_bytes)
        return True
        
    except BadSignatureError:
        return False
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False

def sanitize_input(data):
    """
    Sanitize input data to prevent injection attacks
    """
    if isinstance(data, str):
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';()&+]', '', data)
        return sanitized.strip()
    return data

def validate_secure_link(link):
    """
    Validate secure link format
    """
    if not isinstance(link, str):
        return False
        
    # Check length and character set
    if len(link) != 32:
        return False
        
    # Check if it contains only hexadecimal characters
    if not re.match(r'^[a-f0-9]{32}$', link):
        return False
        
    return True

def create_response(success=True, message="", data=None, error_code=None):
    """
    Create standardized API response
    """
    response = {
        'success': success,
        'message': message,
        'timestamp': None
    }
    
    if data is not None:
        response['data'] = data
        
    if error_code is not None:
        response['error_code'] = error_code
        
    return response

def log_security_event(event_type, details, client_ip=None):
    """
    Log security-related events for monitoring
    """
    import datetime
    timestamp = datetime.datetime.utcnow().isoformat()
    
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'details': details,
        'client_ip': client_ip
    }
    
    # In production, you might want to send this to a logging service
    print(f"Security Event: {log_entry}")
    
    return log_entry