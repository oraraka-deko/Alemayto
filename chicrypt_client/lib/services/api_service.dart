import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'crypto_service.dart';

/// Service for communicating with the PyCrypt backend API
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final CryptoService _cryptoService = CryptoService();
  
  String _baseUrl = 'http://localhost:5000';

  /// Set the backend server URL
  void setBaseUrl(String url) {
    // Remove trailing slash if present
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }

  String get baseUrl => _baseUrl;

  /// Health check
  Future<bool> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/health'),
      ).timeout(const Duration(seconds: 10));
      
      return response.statusCode == 200;
    } catch (e) {
      print('Health check failed: $e');
      return false;
    }
  }

  /// Register client with the backend
  Future<Map<String, dynamic>> register({
    required String publicKeyBase64,
    String? displayName,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'public_key': publicKeyBase64,
          if (displayName != null) 'display_name': displayName,
        }),
      );

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        
        // Store tokens securely
        await _cryptoService.storeLinkToken(data['link_token']);
        await _cryptoService.storeFetchToken(data['fetch_token']);
        
        return {
          'success': true,
          'link': data['link'],
          'linkToken': data['link_token'],
        };
      } else {
        final error = jsonDecode(response.body);
        return {
          'success': false,
          'error': error['error'] ?? 'Registration failed',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Connection error: $e',
      };
    }
  }

  /// Send encrypted message (anonymous sender)
  Future<Map<String, dynamic>> sendMessage({
    required String linkToken,
    required String encryptedMessageBase64,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/send'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'link_token': linkToken,
          'encrypted_message': encryptedMessageBase64,
          if (metadata != null) 'metadata': metadata,
        }),
      );

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'messageId': data['id'],
        };
      } else {
        final error = jsonDecode(response.body);
        return {
          'success': false,
          'error': error['error'] ?? 'Send failed',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Connection error: $e',
      };
    }
  }

  /// Request authentication challenge
  Future<String?> requestChallenge(String linkToken) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/challenge_request'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'link_token': linkToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['challenge'];
      }
      return null;
    } catch (e) {
      print('Challenge request failed: $e');
      return null;
    }
  }

  /// Fetch messages using challenge-response authentication
  Future<Map<String, dynamic>> fetchMessagesWithChallenge({
    required String linkToken,
    bool includeSeen = false,
  }) async {
    try {
      // Request challenge
      final challenge = await requestChallenge(linkToken);
      if (challenge == null) {
        return {
          'success': false,
          'error': 'Failed to get challenge',
        };
      }

      // Sign challenge
      final challengeBytes = Uint8List.fromList(utf8.encode(challenge));
      final signature = await _cryptoService.signMessage(challengeBytes);
      final signatureBase64 = base64.encode(signature);

      // Fetch messages with signed challenge
      final response = await http.post(
        Uri.parse('$_baseUrl/fetch'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'link_token': linkToken,
          'challenge': challenge,
          'challenge_signature': signatureBase64,
          'include_seen': includeSeen,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'messages': data['data'],
        };
      } else {
        final error = jsonDecode(response.body);
        return {
          'success': false,
          'error': error['error'] ?? 'Fetch failed',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Connection error: $e',
      };
    }
  }

  /// Fetch messages using fetch token
  Future<Map<String, dynamic>> fetchMessagesWithToken({
    required String linkToken,
    bool includeSeen = false,
  }) async {
    try {
      final fetchToken = await _cryptoService.getFetchToken();
      if (fetchToken == null) {
        return {
          'success': false,
          'error': 'Fetch token not found',
        };
      }

      final response = await http.post(
        Uri.parse('$_baseUrl/fetch'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $fetchToken',
        },
        body: jsonEncode({
          'link_token': linkToken,
          'include_seen': includeSeen,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'messages': data['data'],
        };
      } else {
        final error = jsonDecode(response.body);
        return {
          'success': false,
          'error': error['error'] ?? 'Fetch failed',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Connection error: $e',
      };
    }
  }

  /// Acknowledge messages (mark as seen)
  Future<Map<String, dynamic>> acknowledgeMessages({
    required String linkToken,
    required List<int> messageIds,
  }) async {
    try {
      final fetchToken = await _cryptoService.getFetchToken();
      if (fetchToken == null) {
        return {
          'success': false,
          'error': 'Fetch token not found',
        };
      }

      final response = await http.post(
        Uri.parse('$_baseUrl/ack'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $fetchToken',
        },
        body: jsonEncode({
          'link_token': linkToken,
          'message_ids': messageIds,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'count': data['count'],
        };
      } else {
        final error = jsonDecode(response.body);
        return {
          'success': false,
          'error': error['error'] ?? 'Acknowledge failed',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Connection error: $e',
      };
    }
  }
}
