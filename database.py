import pymysql
import os
from datetime import datetime
import hashlib
import hmac

class Database:
    def __init__(self):
        self.connection = None
        self.connected = False
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'pycrypt_db'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            self.connected = True
            print("Database connection established successfully")
        except Exception as e:
            print(f"Database connection error: {e}")
            print("Note: Database connection required for production. Set up MySQL and update .env file.")
            self.connected = False
            # Don't raise exception in development - allow app to start without DB
    
    def init_database(self):
        """Initialize database tables"""
        if not self.connected:
            print("Skipping database initialization - no database connection")
            return
            
        try:
            with self.connection.cursor() as cursor:
                # Create clients table for simplex link-based chat
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clients (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        link_token VARCHAR(128) UNIQUE NOT NULL,
                        public_key TEXT NOT NULL,
                        public_key_hash CHAR(64) NOT NULL,
                        key_type VARCHAR(16) NOT NULL DEFAULT 'ed25519',
                        display_name VARCHAR(255) DEFAULT NULL,
                        fetch_token_hash CHAR(128) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_link_token (link_token),
                        INDEX idx_public_key_hash (public_key_hash)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create messages table for encrypted messages
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        link_token VARCHAR(128) NOT NULL,
                        encrypted_message LONGTEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        seen BOOLEAN DEFAULT FALSE,
                        metadata JSON NULL,
                        INDEX idx_link_token (link_token),
                        INDEX idx_created_at (created_at),
                        INDEX idx_seen (seen)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create challenges table for challenge-response authentication
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS challenges (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        link_token VARCHAR(128) NOT NULL,
                        challenge_nonce VARCHAR(255) NOT NULL,
                        client_ip VARCHAR(45) NULL,
                        user_agent VARCHAR(255) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN DEFAULT FALSE,
                        INDEX idx_link_token (link_token),
                        INDEX idx_expires_at (expires_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # Create message_requests table for permission-based messaging
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS message_requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        from_link_token VARCHAR(128) NOT NULL,
                        to_link_token VARCHAR(128) NOT NULL,
                        from_nickname VARCHAR(255) NOT NULL,
                        status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_to_link_token (to_link_token),
                        INDEX idx_from_link_token (from_link_token),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
            print("Database tables initialized successfully")
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise e
    
    def register_client(self, public_key, link_token, fetch_token_hash, display_name=None, key_type='ed25519'):
        """Register a new client with their public key and generated tokens"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                public_key_hash = hashlib.sha256(public_key.encode()).hexdigest()
                sql = """
                    INSERT INTO clients (link_token, public_key, public_key_hash, key_type, display_name, fetch_token_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (link_token, public_key, public_key_hash, key_type, display_name, fetch_token_hash))
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error registering client: {e}")
            raise e

    # Removed context setter; acknowledgment now requires explicit link_token
    
    def get_client_by_link_token(self, link_token):
        """Get client by their link token"""
        if not self.connected:
            return None
            
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT * FROM clients WHERE link_token = %s"
                cursor.execute(sql, (link_token,))
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Error getting client by link token: {e}")
            return None
    
    def verify_fetch_token(self, link_token, fetch_token):
        """Timing-safe verify of fetch token for a client"""
        if not self.connected:
            return False
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT fetch_token_hash FROM clients WHERE link_token = %s"
                cursor.execute(sql, (link_token,))
                result = cursor.fetchone()
                if not result:
                    return False
                stored_hash = result['fetch_token_hash']
                provided_hash = hashlib.sha256(fetch_token.encode()).hexdigest()
                return hmac.compare_digest(stored_hash, provided_hash)
        except Exception as e:
            print(f"Error verifying fetch token: {e}")
            return False
    
    def store_message(self, link_token, encrypted_message, metadata=None):
        """Store an encrypted message for a client"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                import json
                metadata_json = json.dumps(metadata) if metadata else None
                
                sql = """
                    INSERT INTO messages (link_token, encrypted_message, metadata)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (link_token, encrypted_message, metadata_json))
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error storing message: {e}")
            raise e
    
    def get_messages(self, link_token, include_seen=False, limit=50, before_id=None):
        """Get messages for a client with pagination.
        limit: number of messages to return (capped at 200)
        before_id: return messages with id < before_id (cursor pagination)
        """
        if not self.connected:
            return []
            
        try:
            with self.connection.cursor() as cursor:
                # Sanitize limit
                if limit is None or not isinstance(limit, int):
                    limit = 50
                limit = max(1, min(limit, 200))
                base_condition = "link_token = %s"
                seen_condition = "" if include_seen else "AND seen = FALSE"
                cursor_condition = ""
                params = [link_token]
                if before_id is not None:
                    cursor_condition = "AND id < %s"
                    params.append(before_id)
                sql = f"""
                    SELECT id, encrypted_message, created_at, seen, metadata
                    FROM messages
                    WHERE {base_condition} {seen_condition} {cursor_condition}
                    ORDER BY id DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(sql, params)
                return cursor.fetchall()
                
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def mark_messages_seen(self, link_token, message_ids):
        """Mark messages as seen for given link token (scoped)"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                if not message_ids:
                    return
                placeholders = ','.join(['%s'] * len(message_ids))
                sql = f"UPDATE messages SET seen = TRUE WHERE id IN ({placeholders}) AND link_token = %s"
                cursor.execute(sql, (*message_ids, link_token))
                
        except Exception as e:
            print(f"Error marking messages seen: {e}")
            raise e
    
    def create_challenge(self, link_token, challenge_nonce, expires_in_seconds=300, client_ip=None, user_agent=None):
        """Create a challenge for authentication"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                # detect if client_ip/user_agent columns exist; fallback if not
                has_extra_cols = False
                try:
                    cursor.execute("SHOW COLUMNS FROM challenges LIKE 'client_ip'")
                    col = cursor.fetchone()
                    if col:
                        has_extra_cols = True
                except Exception:
                    has_extra_cols = False

                if has_extra_cols and (client_ip or user_agent):
                    sql = """
                        INSERT INTO challenges (link_token, challenge_nonce, client_ip, user_agent, expires_at)
                        VALUES (%s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s SECOND))
                    """
                    cursor.execute(sql, (link_token, challenge_nonce, client_ip, user_agent, expires_in_seconds))
                else:
                    sql = """
                        INSERT INTO challenges (link_token, challenge_nonce, expires_at)
                        VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s SECOND))
                    """
                    cursor.execute(sql, (link_token, challenge_nonce, expires_in_seconds))
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error creating challenge: {e}")
            raise e
    
    def get_challenge(self, link_token, challenge_nonce):
        """Get a challenge for verification"""
        if not self.connected:
            return None
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT * FROM challenges
                    WHERE link_token = %s AND challenge_nonce = %s 
                    AND expires_at > NOW() AND used = FALSE
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(sql, (link_token, challenge_nonce))
                return cursor.fetchone()
                
        except Exception as e:
            print(f"Error getting challenge: {e}")
            return None
    
    def mark_challenge_used(self, challenge_id):
        """Mark a challenge as used"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                sql = "UPDATE challenges SET used = TRUE WHERE id = %s"
                cursor.execute(sql, (challenge_id,))
                
        except Exception as e:
            print(f"Error marking challenge used: {e}")
            raise e
    
    def cleanup_old_challenges(self):
        """Remove expired challenges"""
        if not self.connected:
            return
            
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM challenges WHERE expires_at < NOW()"
                cursor.execute(sql)
                
        except Exception as e:
            print(f"Error cleaning up challenges: {e}")
    
    def get_client_info_by_link(self, link_token):
        """Get public client info by link token (for checking if contact exists)"""
        if not self.connected:
            return None
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT link_token, display_name, created_at 
                    FROM clients 
                    WHERE link_token = %s
                """
                cursor.execute(sql, (link_token,))
                return cursor.fetchone()
                
        except Exception as e:
            print("Error getting client info: {}".format(e))
            return None
    
    def create_message_request(self, from_link_token, to_link_token, from_nickname):
        """Create a message request from one client to another"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO message_requests 
                    (from_link_token, to_link_token, from_nickname, status)
                    VALUES (%s, %s, %s, 'pending')
                """
                cursor.execute(sql, (from_link_token, to_link_token, from_nickname))
                return cursor.lastrowid
                
        except Exception as e:
            print("Error creating message request: {}".format(e))
            raise e
    
    def get_pending_requests(self, to_link_token):
        """Get all pending message requests for a client"""
        if not self.connected:
            return []
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT id, from_link_token, from_nickname, created_at
                    FROM message_requests
                    WHERE to_link_token = %s AND status = 'pending'
                    ORDER BY created_at DESC
                """
                cursor.execute(sql, (to_link_token,))
                return cursor.fetchall()
                
        except Exception as e:
            print("Error getting pending requests: {}".format(e))
            return []
    
    def update_request_status(self, request_id, status):
        """Update message request status (accepted/rejected)"""
        if not self.connected:
            raise Exception("Database connection not available")
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    UPDATE message_requests 
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(sql, (status, request_id))
                
        except Exception as e:
            print("Error updating request status: {}".format(e))
            raise e
    
    def check_message_permission(self, from_link_token, to_link_token):
        """Check if from_client has permission to message to_client"""
        if not self.connected:
            return False
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT id FROM message_requests
                    WHERE from_link_token = %s 
                    AND to_link_token = %s 
                    AND status = 'accepted'
                    LIMIT 1
                """
                cursor.execute(sql, (from_link_token, to_link_token))
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            print("Error checking message permission: {}".format(e))
            return False
    
    def get_request_by_id(self, request_id):
        """Get a message request by ID"""
        if not self.connected:
            return None
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT * FROM message_requests
                    WHERE id = %s
                """
                cursor.execute(sql, (request_id,))
                return cursor.fetchone()
                
        except Exception as e:
            print("Error getting request: {}".format(e))
            return None
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close_connection()