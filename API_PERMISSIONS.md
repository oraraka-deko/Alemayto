# New API Endpoints Documentation

## Contact & Permission-Based Messaging

### 1. Check Contact (`/check_contact`)

**Method:** `POST`

**Purpose:** Verify if a contact exists by their link token and get their public information.

**Request:**
```json
{
  "link_token": "link_xxxxx"
}
```

**Response (Success - Contact Exists):**
```json
{
  "exists": true,
  "link_token": "link_xxxxx",
  "nickname": "Alice",
  "created_at": "2025-11-08T12:00:00"
}
```

**Response (Contact Not Found):**
```json
{
  "exists": false
}
```

**Status Codes:**
- `200 OK` - Request successful (check `exists` field)
- `400 Bad Request` - Missing link_token
- `500 Internal Server Error` - Server error

---

### 2. Request Message Permission (`/request_message_permission`)

**Method:** `POST`

**Purpose:** Request permission from another client before being able to send them messages.

**Request:**
```json
{
  "from_link_token": "link_sender",
  "to_link_token": "link_recipient",
  "from_nickname": "Bob"
}
```

**Response (New Request):**
```json
{
  "message": "Message request sent successfully",
  "request_id": 1,
  "status": "pending"
}
```

**Response (Already Granted):**
```json
{
  "message": "Permission already granted",
  "status": "accepted"
}
```

**Status Codes:**
- `200 OK` - Permission already granted
- `201 Created` - New request created
- `400 Bad Request` - Missing required fields
- `404 Not Found` - Invalid link_token
- `500 Internal Server Error` - Server error

---

### 3. Get Message Requests (`/get_message_requests`)

**Method:** `POST`

**Authentication:** Required (Bearer token or challenge-response)

**Purpose:** Retrieve all pending message requests for a client.

**Request:**
```json
{
  "link_token": "link_xxxxx"
}
```

**Headers:**
```
Authorization: Bearer <fetch_token>
```

**Response:**
```json
{
  "message": "Requests retrieved successfully",
  "data": [
    {
      "id": 1,
      "from_link_token": "link_sender",
      "from_nickname": "Bob",
      "created_at": "2025-11-08T12:00:00"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Requests retrieved
- `400 Bad Request` - Missing link_token
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Invalid link_token
- `500 Internal Server Error` - Server error

---

### 4. Respond to Message Request (`/respond_message_request`)

**Method:** `POST`

**Authentication:** Required (Bearer token or challenge-response)

**Purpose:** Accept or reject a message request.

**Request:**
```json
{
  "link_token": "link_xxxxx",
  "request_id": 1,
  "action": "accept"
}
```

**Headers:**
```
Authorization: Bearer <fetch_token>
```

**Actions:**
- `"accept"` - Grant permission to send messages
- `"reject"` - Deny permission to send messages

**Response:**
```json
{
  "message": "Request accepted successfully",
  "request_id": 1,
  "status": "accepted"
}
```

**Status Codes:**
- `200 OK` - Request processed
- `400 Bad Request` - Missing fields or invalid action
- `401 Unauthorized` - Authentication failed
- `403 Forbidden` - Not authorized to respond to this request
- `404 Not Found` - Request not found
- `500 Internal Server Error` - Server error

---

### 5. Send Message (Updated - `/send`)

**Method:** `POST`

**Purpose:** Send an encrypted message. Now supports permission-based messaging.

**Request (With Permission Check):**
```json
{
  "link_token": "link_recipient",
  "from_link_token": "link_sender",
  "encrypted_message": "base64_encrypted_data",
  "metadata": {
    "timestamp": "2025-11-08T12:00:00"
  }
}
```

**Request (Anonymous - No Permission Check):**
```json
{
  "link_token": "link_recipient",
  "encrypted_message": "base64_encrypted_data"
}
```

**Response (Success):**
```json
{
  "message": "Message sent successfully",
  "id": 123
}
```

**Response (Permission Denied):**
```json
{
  "error": "Permission denied. Please request permission first.",
  "action_required": "request_permission"
}
```

**Status Codes:**
- `201 Created` - Message sent
- `400 Bad Request` - Missing required fields
- `403 Forbidden` - Permission denied (when from_link_token provided)
- `404 Not Found` - Invalid link_token
- `500 Internal Server Error` - Server error

---

## Database Schema Addition

### message_requests Table

```sql
CREATE TABLE message_requests (
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
);
```

---

## Workflow Example

### Client2 wants to message Client1 for the first time:

1. **Client2 checks if Client1 exists:**
   ```
   POST /check_contact
   { "link_token": "client1_link" }
   ```

2. **Client2 requests permission:**
   ```
   POST /request_message_permission
   {
     "from_link_token": "client2_link",
     "to_link_token": "client1_link",
     "from_nickname": "Client2"
   }
   ```

3. **Client1 gets online and fetches requests:**
   ```
   POST /get_message_requests
   { "link_token": "client1_link" }
   Headers: Authorization: Bearer <client1_fetch_token>
   ```

4. **Client1 accepts the request:**
   ```
   POST /respond_message_request
   {
     "link_token": "client1_link",
     "request_id": 1,
     "action": "accept"
   }
   Headers: Authorization: Bearer <client1_fetch_token>
   ```

5. **Client2 can now send messages:**
   ```
   POST /send
   {
     "link_token": "client1_link",
     "from_link_token": "client2_link",
     "encrypted_message": "..."
   }
   ```

---

## Migration

The database migration file has been updated (`migrations/versions/001_initial_schema.py`) to include the `message_requests` table. When the server starts, it will automatically create this table if it doesn't exist.

---

## Backward Compatibility

- Anonymous sending (without `from_link_token`) still works for backward compatibility
- Existing `/send` requests without `from_link_token` will not perform permission checks
- All other endpoints remain unchanged
