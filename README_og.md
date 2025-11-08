# PyCrypt - Simplex Link-Based E2EE Chat Backend

A Python Flask backend server for secure simplex (one-way) link-based messaging with **end-to-end encryption** using libsodium (NaCl). Designed for Flutter applications where senders can anonymously send encrypted messages to a recipient using only a shareable link.

## 🔒 Security Architecture

- **End-to-End Encryption**: Server never sees plaintext or private keys
- **Sealed Box Encryption**: Uses NaCl `crypto_box_seal` with ephemeral keys for forward secrecy
- **Challenge-Response Auth**: Signature-based authentication to prove private key ownership
- **Anonymous Sending**: Anyone with a link can send encrypted messages
- **Protected Reading**: Only the link owner (with private key) can decrypt messages

## 🎯 Key Features

- **Simplex Communication**: One-way messaging from senders to recipient
- **Link-Based Sharing**: Share a single link for anyone to send you encrypted messages
- **Dual Authentication**: Supports both challenge-response signatures and fetch tokens
- **Message Acknowledgment**: Mark messages as seen/unseen
- **MariaDB/MySQL Storage**: Encrypted messages stored securely in database
- **cPanel Compatible**: Designed for shared hosting deployment

## 📋 How It Works

1. **Recipient Setup**: Client generates Ed25519 keypair, registers with server
2. **Link Generation**: Server returns unique `link_token` and `fetch_token`
3. **Sharing**: Recipient shares link with senders
4. **Sending**: Senders encrypt messages with recipient's public key (sealed box)
5. **Fetching**: Recipient authenticates and retrieves encrypted messages
6. **Decryption**: Client-side decryption using private key

## 🗂️ Project Structure

```
pycrypt/
├── app.py                 # Main Flask application with API endpoints
├── database.py            # Database operations (clients, messages, challenges)
├── utils.py              # Crypto utilities (tokens, signatures, validation)
├── requirements.txt      # Python dependencies
├── test_new_api.py       # Comprehensive API test suite
├── .env                  # Environment configuration
└── README.md             # This file
```

## 🔌 API Endpoints

### 1. Health Check
**GET** `/health`

Returns server status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T01:00:00.000000"
}
```

---

### 2. Register Client
**POST** `/register`

Register a new client with their Ed25519 public key.

**Request:**
```json
{
  "public_key": "<base64-encoded-ed25519-public-key>",
  "display_name": "Alice" 
}
```

**Response (201):**
```json
{
  "message": "Client registered successfully",
  "client_id": 1,
  "link": "http://domain.com/l/link_abc123",
  "link_token": "link_abc123",
  "fetch_token": "<secret-token-store-securely>"
}
```

**Security**: Store `fetch_token` securely on client device (use secure storage).

---

### 3. Send Message
**POST** `/send`

Send an encrypted message (anonymous sender).

**Request:**
```json
{
  "link_token": "link_abc123",
  "encrypted_message": "<base64-sealed-box-ciphertext>",
  "metadata": {"sender_nick": "Bob"}  // optional, better to encrypt this
}
```

**Response (201):**
```json
{
  "message": "Message sent successfully",
  "id": 42
}
```

**Encryption**: Use NaCl `crypto_box_seal` with recipient's X25519 public key.

---

### 4. Request Challenge
**POST** `/challenge_request`

Request a challenge nonce for signature-based authentication.

**Request:**
```json
{
  "link_token": "link_abc123"
}
```

**Response (200):**
```json
{
  "challenge": "<base64-nonce>"
}
```

**Expires**: Challenge valid for 5 minutes.

---

### 5. Fetch Messages
**POST** `/fetch`

Retrieve encrypted messages. Requires authentication via challenge-response OR fetch token.

**Method A - Challenge-Response (Recommended):**
```json
{
  "link_token": "link_abc123",
  "challenge": "<nonce-from-challenge-request>",
  "challenge_signature": "<base64-ed25519-signature>"
}
```

**Method B - Fetch Token:**
```json
{
  "link_token": "link_abc123"
}
```
**Headers:**
```
Authorization: Bearer <fetch_token>
```

**Response (200):**
```json
{
  "message": "Messages retrieved successfully",
  "data": [
    {
      "id": 42,
      "encrypted_message": "<base64-ciphertext>",
      "created_at": "2025-11-08T01:00:00",
      "seen": false,
      "metadata": null
    }
  ]
}
```

**Parameters:**
- `include_seen`: (optional, default false) Include already-seen messages

---

### 6. Acknowledge Messages
**POST** `/ack`

Mark messages as seen. Requires authentication.

**Request:**
```json
{
  "link_token": "link_abc123",
  "message_ids": [42, 43, 44]
}
```

**Headers:**
```
Authorization: Bearer <fetch_token>
```

**Response (200):**
```json
{
  "message": "Messages marked as seen",
  "count": 3
}
```

---

## 🔐 Cryptography Details

### Key Types

1. **Ed25519 (Signing)**: For authentication via challenge-response
   - Client registers with Ed25519 public key
   - Signs challenges to prove identity

2. **X25519 (Encryption)**: For message encryption via sealed boxes
   - Derived from or generated separately
   - Used for `crypto_box_seal` operations

### Encryption Flow

**Sender (Anonymous):**
```python
from nacl.public import PublicKey, SealedBox
import base64

# Get recipient's X25519 public key
recipient_pubkey = PublicKey(base64.b64decode(recipient_public_key_b64))

# Encrypt message
sealed_box = SealedBox(recipient_pubkey)
encrypted = sealed_box.encrypt(plaintext.encode('utf-8'))
encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')

# Send to server
```

**Recipient (Decrypt):**
```python
from nacl.public import PrivateKey, SealedBox

# Use stored private key
private_key = PrivateKey(base64.b64decode(private_key_b64))

# Decrypt message
unsealed_box = SealedBox(private_key)
decrypted = unsealed_box.decrypt(base64.b64decode(encrypted_b64))
plaintext = decrypted.decode('utf-8')
```

### Authentication Flow

**Challenge-Response:**
```python
from nacl.signing import SigningKey
import base64

# Client signs challenge
signing_key = SigningKey(private_key_bytes)
signature = signing_key.sign(challenge_nonce.encode('utf-8'))
signature_b64 = base64.b64encode(signature.signature).decode('utf-8')

# Send signature to server for verification
```

---

## 🛠️ Setup Instructions

### 1. Requirements

- Python 3.8+
- MariaDB/MySQL
- Git

### 2. Installation

```bash
# Clone repository
cd /path/to/project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create database
mysql -u root -p -e "CREATE DATABASE pycrypt_db;"

# Create user
mysql -u root -p -e "CREATE USER 'pycrypt_user'@'localhost' IDENTIFIED BY 'your_password';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON pycrypt_db.* TO 'pycrypt_user'@'localhost'; FLUSH PRIVILEGES;"
```

### 4. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DEBUG=True
PORT=5000

DB_HOST=localhost
DB_USER=pycrypt_user
DB_PASSWORD=your_password
DB_NAME=pycrypt_db

BASE_URL=http://localhost:5000
```

### 5. Initialize Database

```bash
python -c "from app import db; db.init_database()"
```

### 6. Run Server

```bash
python app.py
```

Server will be available at `http://localhost:5000`

### 7. Run Tests

```bash
python test_new_api.py
```

---

## 📊 Database Schema

### Clients Table
```sql
CREATE TABLE clients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  link_token VARCHAR(128) UNIQUE NOT NULL,
  public_key TEXT NOT NULL,
  public_key_hash CHAR(64) NOT NULL,
  display_name VARCHAR(255),
  fetch_token_hash CHAR(128) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Messages Table
```sql
CREATE TABLE messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  link_token VARCHAR(128) NOT NULL,
  encrypted_message LONGTEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  seen BOOLEAN DEFAULT FALSE,
  metadata JSON NULL
);
```

### Challenges Table
```sql
CREATE TABLE challenges (
  id INT AUTO_INCREMENT PRIMARY KEY,
  link_token VARCHAR(128) NOT NULL,
  challenge_nonce VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE
);
```

---

## 🚀 cPanel Deployment

1. **Upload Files**: Upload all files to cPanel hosting directory
2. **Python Environment**: Use cPanel Python app manager to create environment
3. **Install Dependencies**: `pip install -r requirements.txt` in cPanel terminal
4. **Database Setup**: Create database and user via cPanel MySQL manager
5. **Configure .env**: Update with production credentials
6. **Set Entry Point**: Point cPanel Python app to `app.py`
7. **Start Application**: Launch via cPanel interface

---

## 🔒 Security Best Practices

### Server-Side
- ✅ Server never decrypts messages (no private keys on server)
- ✅ Store only hashed tokens (fetch_token_hash)
- ✅ Use parameterized SQL queries (injection prevention)
- ✅ Validate all inputs
- ✅ Expire challenges after 5 minutes
- ✅ Use HTTPS in production

### Client-Side (Flutter)
- ✅ Generate keypairs on device
- ✅ Store private keys in secure storage (Keychain/Keystore)
- ✅ Never transmit private keys
- ✅ Validate server certificates
- ✅ Implement proper error handling
- ✅ Provide key backup/recovery option (encrypted with passphrase)

---

## 📦 Dependencies

- **Flask** (3.1+): Web framework
- **Flask-CORS** (6.0+): Cross-origin resource sharing
- **PyNaCl** (1.5+): libsodium bindings for encryption
- **PyMySQL** (1.1+): MySQL database connector
- **python-dotenv** (1.0+): Environment variable management
- **cryptography** (41.0+): Additional crypto utilities
- **requests** (2.31+): HTTP client for testing

---

## 🧪 Testing

The `test_new_api.py` script provides comprehensive testing:

- ✅ Client registration with Ed25519 keypair
- ✅ Link and fetch token generation
- ✅ Message encryption with sealed boxes
- ✅ Anonymous message sending
- ✅ Challenge-response authentication
- ✅ Fetch token authentication
- ✅ Message retrieval and client-side decryption
- ✅ Message acknowledgment
- ✅ Invalid authentication rejection

Run tests:
```bash
python test_new_api.py
```

---

## 🆘 Troubleshooting

### Database Connection Failed
- Check MariaDB is running: `systemctl status mariadb`
- Verify credentials in `.env`
- Check user permissions

### Import Errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Authentication Fails
- Verify challenge hasn't expired (5 min limit)
- Check signature generation matches server verification
- Ensure correct public/private key pairing

### Messages Can't Decrypt
- Verify X25519 keys (not Ed25519) used for encryption
- Check base64 encoding/decoding
- Ensure sealed box implementation matches server

---

**Built with security and privacy as top priorities** 🔐