from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import subprocess
import sys

# Load environment variables FIRST
load_dotenv()

from database import Database
from utils import (
    generate_link_token, 
    generate_fetch_token, 
    hash_token,
    generate_challenge_nonce,
    validate_public_key,
    verify_signature,
    sanitize_input,
    create_response
)

def run_migrations():
    """Check if database needs setup and run migrations if needed"""
    try:
        # Check if database connection works
        db_test = Database()
        if not db_test.connected:
            print("WARNING: Database not connected. Skipping migrations.")
            print("   Set up your database and configure .env file for production.")
            return False
        
        # Check if tables exist
        try:
            with db_test.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_count = len(tables)
                
                if table_count == 0:
                    print("INFO: No tables found. Running initial migration...")
                    # Run alembic upgrade
                    result = subprocess.run(
                        ['alembic', 'upgrade', 'head'],
                        cwd=os.path.dirname(os.path.abspath(__file__)),
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        print("SUCCESS: Database tables created successfully!")
                        return True
                    else:
                        print("ERROR: Migration failed: {}".format(result.stderr))
                        # Fallback to init_database
                        print("INFO: Trying fallback initialization...")
                        db_test.init_database()
                        print("SUCCESS: Database initialized using fallback method")
                        return True
                else:
                    print("INFO: Database already set up ({} tables found)".format(table_count))
                    return True
                    
        except Exception as e:
            print("Error checking database: {}".format(e))
            print("INFO: Attempting to initialize database...")
            db_test.init_database()
            return True
            
    except Exception as e:
        print("WARNING: Database setup check failed: {}".format(e))
        return False

app = Flask(__name__)
CORS(app)

# Run migrations on startup
print("\nStarting ChiCrypt Server...")
run_migrations()

# Initialize database
db = Database()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/register', methods=['POST'])
def register():
    """
    Register a new client with their public key
    Returns a link_token (for sharing) and fetch_token (for authentication)
    """
    try:
        data = request.get_json()
        
        if not data or 'public_key' not in data:
            return jsonify({'error': 'Public key is required'}), 400
            
        public_key = data['public_key']
        display_name = sanitize_input(data.get('display_name'))
        key_type = data.get('key_type', 'ed25519')
        
        # Validate key_type (only Ed25519 supported)
        if key_type not in ['ed25519']:
            return jsonify({'error': 'Unsupported key_type. Only ed25519 is supported.'}), 400
        
        # Validate the public key format
        if not validate_public_key(public_key):
            return jsonify({'error': 'Invalid public key format'}), 400
            
        # Generate tokens
        link_token = generate_link_token()
        fetch_token = generate_fetch_token()
        fetch_token_hash = hash_token(fetch_token)
        
        # Save to database
        client_id = db.register_client(
            public_key=public_key,
            link_token=link_token,
            fetch_token_hash=fetch_token_hash,
            display_name=display_name,
            key_type=key_type
        )
        
        # Construct shareable link
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        shareable_link = f"{base_url}/l/{link_token}"
        
        return jsonify({
            'message': 'Client registered successfully',
            'client_id': client_id,
            'link': shareable_link,
            'link_token': link_token,
            'fetch_token': fetch_token,  # Client must store this securely!
            'key_type': key_type
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/send', methods=['POST'])
def send_message():
    """
    Send an encrypted message to a recipient
    Requires permission if from_link_token is provided (permission-based messaging)
    Otherwise allows anonymous sending with just link_token (backward compatible)
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data or 'encrypted_message' not in data:
            return jsonify({'error': 'link_token and encrypted_message are required'}), 400
            
        to_link_token = data['link_token']
        from_link_token = data.get('from_link_token')  # Optional sender identification
        encrypted_message = data['encrypted_message']
        metadata = data.get('metadata')  # Optional metadata
        # Validate payload sizes
        try:
            import base64 as _b64
            decoded = _b64.b64decode(encrypted_message)
            if len(decoded) > 16 * 1024:
                return jsonify({'error': 'Encrypted message too large (max 16KB)'}), 413
        except Exception:
            return jsonify({'error': 'Invalid base64 for encrypted_message'}), 400
        if metadata is not None:
            try:
                meta_str = json.dumps(metadata)
                if len(meta_str) > 4 * 1024:
                    return jsonify({'error': 'Metadata too large (max 4KB)'}), 413
            except Exception:
                return jsonify({'error': 'Invalid metadata JSON'}), 400
        
        # Verify that the recipient link_token exists
        client = db.get_client_by_link_token(to_link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # If sender is identified, check permission
        if from_link_token:
            # Verify sender exists
            from_client = db.get_client_by_link_token(from_link_token)
            if not from_client:
                return jsonify({'error': 'Invalid from_link_token'}), 404
                
            # Check if sender has permission to message recipient
            has_permission = db.check_message_permission(from_link_token, to_link_token)
            if not has_permission:
                return jsonify({
                    'error': 'Permission denied. Please request permission first.',
                    'action_required': 'request_permission'
                }), 403
        
        # Store the encrypted message (server never decrypts it)
        message_id = db.store_message(
            link_token=to_link_token,
            encrypted_message=encrypted_message,
            metadata=metadata
        )
        
        return jsonify({
            'message': 'Message sent successfully',
            'id': message_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/challenge_request', methods=['POST'])
def challenge_request():
    """
    Request a challenge nonce for authentication
    Client must sign this challenge to prove they own the private key
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data:
            return jsonify({'error': 'link_token is required'}), 400
            
        link_token = data['link_token']
        
        # Verify that the link_token exists
        client = db.get_client_by_link_token(link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # Rate limiting: max 5 outstanding, cooldown 3s
        try:
            with db.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) AS cnt FROM challenges 
                    WHERE link_token=%s AND used=FALSE AND expires_at>NOW()
                """, (link_token,))
                row = cursor.fetchone()
                if row and row['cnt'] >= 5:
                    return jsonify({'error': 'Too many outstanding challenges'}), 429
                cursor.execute("""
                    SELECT TIMESTAMPDIFF(SECOND, created_at, NOW()) AS age
                    FROM challenges WHERE link_token=%s ORDER BY created_at DESC LIMIT 1
                """, (link_token,))
                age = cursor.fetchone()
                if age and age['age'] is not None and age['age'] < 3:
                    return jsonify({'error': 'Challenge requested too frequently'}), 429
        except Exception:
            pass

        # Generate a challenge nonce
        challenge_nonce = generate_challenge_nonce()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        db.create_challenge(link_token, challenge_nonce, expires_in_seconds=300, client_ip=client_ip, user_agent=user_agent)
        db.cleanup_old_challenges()
        return jsonify({'challenge': challenge_nonce}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fetch', methods=['POST'])
def fetch_messages():
    """
    Fetch encrypted messages for a client
    Requires either:
    - challenge_signature (proving ownership of private key), OR
    - fetch_token in Authorization header
    
    Pagination parameters:
    - limit: number of messages to return (default 50, max 200)
    - before_id: for infinite scroll (DESC order)
    - since_id: for polling new messages (ASC order)
    - order: 'ASC' or 'DESC' (default 'DESC')
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data:
            return jsonify({'error': 'link_token is required'}), 400
            
        link_token = data['link_token']
        
        # Get client
        client = db.get_client_by_link_token(link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # Check authentication method
        auth_header = request.headers.get('Authorization')
        challenge_signature = data.get('challenge_signature')
        challenge_nonce = data.get('challenge')
        
        authenticated = False
        
        # Method 1: Challenge-response (stronger)
        if challenge_signature and challenge_nonce:
            # Verify challenge exists and is valid
            challenge = db.get_challenge(link_token, challenge_nonce)
            if not challenge:
                return jsonify({'error': 'Invalid or expired challenge'}), 401
                
            # Verify signature
            message_to_verify = challenge_nonce.encode('utf-8')
            if verify_signature(client['public_key'], message_to_verify, challenge_signature):
                authenticated = True
                # Mark challenge as used
                db.mark_challenge_used(challenge['id'])
            else:
                return jsonify({'error': 'Invalid signature'}), 401
                
        # Method 2: Fetch token (simpler but less secure)
        elif auth_header and auth_header.startswith('Bearer '):
            fetch_token = auth_header.split(' ')[1]
            if db.verify_fetch_token(link_token, fetch_token):
                authenticated = True
            else:
                return jsonify({'error': 'Invalid fetch_token'}), 401
        else:
            return jsonify({'error': 'Authentication required (challenge_signature or Authorization header)'}), 401
            
        if not authenticated:
            return jsonify({'error': 'Authentication failed'}), 401
            
        # Get messages with pagination
        include_seen = data.get('include_seen', False)
        limit = data.get('limit', 50)
        before_id = data.get('before_id')
        since_id = data.get('since_id')
        order = data.get('order', 'DESC')
        
        try:
            limit = int(limit)
        except Exception:
            limit = 50
            
        messages = db.get_messages(
            link_token, 
            include_seen=include_seen, 
            limit=limit, 
            before_id=before_id,
            since_id=since_id,
            order=order
        )
        
        # Format response
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg['id'],
                'encrypted_message': msg['encrypted_message'],
                'created_at': msg['created_at'].isoformat() if msg['created_at'] else None,
                'seen': msg['seen'],
                'metadata': json.loads(msg['metadata']) if msg['metadata'] else None
            })
        
        # Add pagination metadata
        response_data = {
            'message': 'Messages retrieved successfully',
            'data': message_list,
            'count': len(message_list),
            'has_more': len(message_list) == limit
        }
        
        # Add next_cursor for pagination
        if message_list:
            if order == 'ASC':
                response_data['next_cursor'] = message_list[-1]['id']
            else:
                response_data['next_cursor'] = message_list[-1]['id']
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ack', methods=['POST'])
def acknowledge_messages():
    """
    Mark messages as seen
    Requires authentication (fetch_token or challenge_signature)
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data or 'message_ids' not in data:
            return jsonify({'error': 'link_token and message_ids are required'}), 400
            
        link_token = data['link_token']
        message_ids = data['message_ids']
        
        # Get client
        client = db.get_client_by_link_token(link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # Check authentication (same as fetch)
        auth_header = request.headers.get('Authorization')
        challenge_signature = data.get('challenge_signature')
        challenge_nonce = data.get('challenge')
        
        authenticated = False
        
        if challenge_signature and challenge_nonce:
            challenge = db.get_challenge(link_token, challenge_nonce)
            if challenge:
                message_to_verify = challenge_nonce.encode('utf-8')
                if verify_signature(client['public_key'], message_to_verify, challenge_signature):
                    authenticated = True
                    db.mark_challenge_used(challenge['id'])
                    
        elif auth_header and auth_header.startswith('Bearer '):
            fetch_token = auth_header.split(' ')[1]
            if db.verify_fetch_token(link_token, fetch_token):
                authenticated = True
                
        if not authenticated:
            return jsonify({'error': 'Authentication failed'}), 401
            
        # Mark messages as seen (scoped by link_token)
        db.mark_messages_seen(link_token, message_ids)
        
        return jsonify({
            'message': 'Messages marked as seen',
            'count': len(message_ids)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_contact', methods=['POST'])
def check_contact():
    """
    Check if a contact exists by link token
    Returns existence status and nickname if exists
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data:
            return jsonify({'error': 'link_token is required'}), 400
            
        link_token = data['link_token']
        
        # Get client info
        client = db.get_client_info_by_link(link_token)
        
        if client:
            return jsonify({
                'exists': True,
                'link_token': client['link_token'],
                'nickname': client['display_name'],
                'created_at': client['created_at'].isoformat() if client['created_at'] else None
            }), 200
        else:
            return jsonify({
                'exists': False
            }), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/request_message_permission', methods=['POST'])
def request_message_permission():
    """
    Request permission to send messages to another client
    Client2 sends request to Client1 before being able to message them
    """
    try:
        data = request.get_json()
        
        if not data or 'from_link_token' not in data or 'to_link_token' not in data:
            return jsonify({'error': 'from_link_token and to_link_token are required'}), 400
            
        from_link_token = data['from_link_token']
        to_link_token = data['to_link_token']
        from_nickname = sanitize_input(data.get('from_nickname', 'Anonymous'))
        
        # Verify both clients exist
        from_client = db.get_client_by_link_token(from_link_token)
        to_client = db.get_client_by_link_token(to_link_token)
        
        if not from_client:
            return jsonify({'error': 'Invalid from_link_token'}), 404
            
        if not to_client:
            return jsonify({'error': 'Invalid to_link_token'}), 404
            
        # Check if request already exists
        existing_permission = db.check_message_permission(from_link_token, to_link_token)
        if existing_permission:
            return jsonify({
                'message': 'Permission already granted',
                'status': 'accepted'
            }), 200
            
        # Create new request
        request_id = db.create_message_request(from_link_token, to_link_token, from_nickname)
        
        return jsonify({
            'message': 'Message request sent successfully',
            'request_id': request_id,
            'status': 'pending'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_message_requests', methods=['POST'])
def get_message_requests():
    """
    Get pending message requests for a client
    Requires authentication
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data:
            return jsonify({'error': 'link_token is required'}), 400
            
        link_token = data['link_token']
        
        # Get client
        client = db.get_client_by_link_token(link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # Check authentication
        auth_header = request.headers.get('Authorization')
        challenge_signature = data.get('challenge_signature')
        challenge_nonce = data.get('challenge')
        
        authenticated = False
        
        if challenge_signature and challenge_nonce:
            challenge = db.get_challenge(link_token, challenge_nonce)
            if challenge:
                message_to_verify = challenge_nonce.encode('utf-8')
                if verify_signature(client['public_key'], message_to_verify, challenge_signature):
                    authenticated = True
                    db.mark_challenge_used(challenge['id'])
                    
        elif auth_header and auth_header.startswith('Bearer '):
            fetch_token = auth_header.split(' ')[1]
            if db.verify_fetch_token(link_token, fetch_token):
                authenticated = True
                
        if not authenticated:
            return jsonify({'error': 'Authentication failed'}), 401
            
        # Get pending requests
        requests = db.get_pending_requests(link_token)
        
        request_list = []
        for req in requests:
            request_list.append({
                'id': req['id'],
                'from_link_token': req['from_link_token'],
                'from_nickname': req['from_nickname'],
                'created_at': req['created_at'].isoformat() if req['created_at'] else None
            })
        
        return jsonify({
            'message': 'Requests retrieved successfully',
            'data': request_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/respond_message_request', methods=['POST'])
def respond_message_request():
    """
    Accept or reject a message request
    Requires authentication from the recipient (to_link_token)
    """
    try:
        data = request.get_json()
        
        if not data or 'link_token' not in data or 'request_id' not in data or 'action' not in data:
            return jsonify({'error': 'link_token, request_id, and action are required'}), 400
            
        link_token = data['link_token']
        request_id = data['request_id']
        action = data['action']  # 'accept' or 'reject'
        
        if action not in ['accept', 'reject']:
            return jsonify({'error': 'action must be "accept" or "reject"'}), 400
            
        # Get client
        client = db.get_client_by_link_token(link_token)
        if not client:
            return jsonify({'error': 'Invalid link_token'}), 404
            
        # Check authentication
        auth_header = request.headers.get('Authorization')
        challenge_signature = data.get('challenge_signature')
        challenge_nonce = data.get('challenge')
        
        authenticated = False
        
        if challenge_signature and challenge_nonce:
            challenge = db.get_challenge(link_token, challenge_nonce)
            if challenge:
                message_to_verify = challenge_nonce.encode('utf-8')
                if verify_signature(client['public_key'], message_to_verify, challenge_signature):
                    authenticated = True
                    db.mark_challenge_used(challenge['id'])
                    
        elif auth_header and auth_header.startswith('Bearer '):
            fetch_token = auth_header.split(' ')[1]
            if db.verify_fetch_token(link_token, fetch_token):
                authenticated = True
                
        if not authenticated:
            return jsonify({'error': 'Authentication failed'}), 401
            
        # Get the request and verify it belongs to this client
        request_info = db.get_request_by_id(request_id)
        if not request_info:
            return jsonify({'error': 'Request not found'}), 404
            
        if request_info['to_link_token'] != link_token:
            return jsonify({'error': 'Unauthorized - this request is not for you'}), 403
            
        if request_info['status'] != 'pending':
            return jsonify({'error': 'Request already processed'}), 400
            
        # Update request status
        new_status = 'accepted' if action == 'accept' else 'rejected'
        db.update_request_status(request_id, new_status)
        
        return jsonify({
            'message': 'Request {} successfully'.format(new_status),
            'request_id': request_id,
            'status': new_status
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database tables
    db.init_database()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)