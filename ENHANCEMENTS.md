# Security and API Enhancements

This document describes the security improvements and API enhancements implemented based on the security audit findings.

## Security Improvements

### 1. Input Sanitization ✅
- **Display Name**: All `display_name` fields are now sanitized using `sanitize_input()` to prevent XSS and injection attacks
- **From Nickname**: All `from_nickname` fields in message requests are sanitized
- Characters removed: `< > " ' ; ( ) & +`

### 2. Message Size Validation ✅
- **Encrypted Message**: Maximum 16KB (decoded from base64)
- **Metadata**: Maximum 4KB (JSON serialized)
- Returns HTTP 413 (Payload Too Large) when limits exceeded

### 3. Key Type Validation ✅
- Only `ed25519` key type is supported
- Key type is validated during registration
- Invalid key types return HTTP 400 with error message
- Response includes `key_type` field to confirm accepted type

### 4. Secure Token Comparison ✅
- Fetch token verification uses `hmac.compare_digest()` for timing-safe comparison
- Prevents timing attacks on authentication tokens

### 5. Message Ownership Protection ✅
- `mark_messages_seen()` is scoped by `link_token`
- Prevents users from acknowledging messages that don't belong to them

## Pagination and Message Ordering

### 1. Message Ordering ✅
- **Default**: `DESC` (newest first) - maintains backward compatibility
- **Ascending**: `order=ASC` returns messages chronologically (oldest → newest)
- Configurable via `order` parameter in `/fetch` endpoint

### 2. Pagination Strategies ✅

#### Infinite Scroll (DESC order)
```json
{
  "link_token": "link_xxx",
  "limit": 50,
  "before_id": 12345,
  "order": "DESC"
}
```

#### Polling for New Messages (ASC order)
```json
{
  "link_token": "link_xxx",
  "since_id": 12340,
  "order": "ASC"
}
```

### 3. Pagination Metadata ✅
Response now includes:
- `count`: Number of messages returned
- `has_more`: Boolean indicating if more messages exist
- `next_cursor`: ID to use for next page

Example response:
```json
{
  "message": "Messages retrieved successfully",
  "data": [...],
  "count": 50,
  "has_more": true,
  "next_cursor": 12395
}
```

## Database Improvements

### 1. Size Tracking ✅
- New `size_bytes` column in `messages` table
- Automatically calculated and stored when messages are saved
- Enables monitoring and analytics

### 2. Composite Index ✅
- Index: `(link_token, seen, created_at)`
- Optimizes queries for unseen messages
- Improves performance for typical fetch operations

### 3. Migration Support ✅
- Migration 003: Adds `size_bytes` and composite index
- Backward compatible with existing databases
- Automatic detection of column existence

## API Enhancements

### Updated Endpoints

#### POST /register
**New Fields:**
- `key_type` (optional, default: 'ed25519') - only ed25519 supported
- Response includes `key_type` to confirm

**Sanitization:**
- `display_name` is sanitized before storage

#### POST /send
**New Validations:**
- Encrypted message size limit: 16KB (decoded)
- Metadata size limit: 4KB (JSON)
- Base64 validation for encrypted_message

#### POST /fetch
**New Parameters:**
- `since_id` - Get messages after this ID (for polling)
- `before_id` - Get messages before this ID (for infinite scroll)
- `order` - 'ASC' or 'DESC' (default: DESC)
- `limit` - Max messages to return (capped at 200)

**New Response Fields:**
- `count` - Number of messages returned
- `has_more` - Boolean indicating more messages exist
- `next_cursor` - ID for next pagination request

#### POST /request_message_permission
**Sanitization:**
- `from_nickname` is sanitized before storage

## Testing

### Test Suites

#### test_enhancements.py
Tests for new security and pagination features:
- Input sanitization
- Key type validation
- Message size limits
- Metadata size limits
- Pagination with ASC/DESC order
- Pagination with since_id
- Pagination with before_id
- Pagination metadata

#### test_edge_cases.py
Tests for edge cases from security audit:
- Challenge reuse prevention
- Challenge rate limiting
- Extremely large message rejection
- Invalid metadata handling
- Invalid base64 rejection
- Non-existent message IDs in ack
- Empty message_ids handling
- Invalid order parameter
- Limit capping
- Duplicate public key registration

### Running Tests

Start the server:
```bash
python app.py
```

In another terminal, run tests:
```bash
# New feature tests
python test_enhancements.py

# Edge case tests
python test_edge_cases.py

# Existing API tests
python test_new_api.py
```

## Security Best Practices

### What's Protected ✅
1. ✅ XSS prevention via input sanitization
2. ✅ DoS prevention via size limits
3. ✅ Timing attacks prevented with constant-time comparison
4. ✅ Message leakage prevented via ownership scoping
5. ✅ Key type enforcement
6. ✅ Challenge replay prevention

### Future Improvements (Recommended)
1. ⏳ Token rotation endpoint (`/rotate_fetch_token`)
2. ⏳ Soft-deletion or retention policy
3. ⏳ Structured logging with correlation IDs
4. ⏳ Metrics collection (messages_sent, messages_fetched, etc.)
5. ⏳ Security headers (X-Content-Type-Options, CSP)
6. ⏳ DB connection pooling
7. ⏳ Migration version tracking
8. ⏳ Scheduled challenge cleanup job

## Backward Compatibility

All changes are backward compatible:
- New parameters are optional
- Default behavior is preserved (DESC order)
- Existing clients continue to work without changes
- Database schema changes are additive only

## Migration Guide

### For Existing Databases

Run the migration:
```bash
alembic upgrade head
```

Or the database will auto-migrate on app startup if tables don't exist.

### For Existing Clients

No changes required. To use new features:
1. Add `order=ASC` for chronological messages
2. Add `since_id` for polling
3. Use `next_cursor` from response for pagination
4. Check `has_more` to know if more messages exist

## Performance Considerations

- Composite index improves query performance for unseen messages
- Limit capping (max 200) prevents excessive data transfer
- Size tracking enables future optimization decisions
- Pagination reduces payload size and improves response time
