import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sodium_libs/sodium_libs.dart';

/// Service for handling cryptographic operations and secure key storage
/// Uses libsodium (NaCl) for Ed25519 signing and X25519 encryption
class CryptoService {
  static final CryptoService _instance = CryptoService._internal();
  factory CryptoService() => _instance;
  CryptoService._internal();

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  // Storage keys
  static const String _signingSecretKeyKey = 'signing_secret_key';
  static const String _signingPublicKeyKey = 'signing_public_key';
  static const String _encryptionSecretKeyKey = 'encryption_secret_key';
  static const String _encryptionPublicKeyKey = 'encryption_public_key';
  static const String _linkTokenKey = 'link_token';
  static const String _fetchTokenKey = 'fetch_token';

  Sodium? _sodium;
  bool _initialized = false;

  /// Initialize sodium library
  Future<void> initialize() async {
    if (_initialized) return;
    _sodium = await SodiumInit.init();
    _initialized = true;
  }

  /// Generate Ed25519 keypair for signing/authentication
  Future<KeyPair> generateSigningKeyPair() async {
    await initialize();
    return _sodium!.crypto.sign.keyPair();
  }

  /// Generate X25519 keypair for encryption
  Future<KeyPair> generateEncryptionKeyPair() async {
    await initialize();
    return _sodium!.crypto.box.keyPair();
  }

  /// Store signing keypair securely
  Future<void> storeSigningKeyPair(KeyPair keyPair) async {
    await _secureStorage.write(
      key: _signingSecretKeyKey,
      value: base64.encode(keyPair.secretKey.extractBytes()),
    );
    await _secureStorage.write(
      key: _signingPublicKeyKey,
      value: base64.encode(keyPair.publicKey),
    );
  }

  /// Store encryption keypair securely
  Future<void> storeEncryptionKeyPair(KeyPair keyPair) async {
    await _secureStorage.write(
      key: _encryptionSecretKeyKey,
      value: base64.encode(keyPair.secretKey.extractBytes()),
    );
    await _secureStorage.write(
      key: _encryptionPublicKeyKey,
      value: base64.encode(keyPair.publicKey),
    );
  }

  /// Get signing public key (for registration)
  Future<Uint8List?> getSigningPublicKey() async {
    final key = await _secureStorage.read(key: _signingPublicKeyKey);
    if (key == null) return null;
    return base64.decode(key);
  }

  /// Get signing secret key (for authentication)
  Future<Uint8List?> getSigningSecretKey() async {
    final key = await _secureStorage.read(key: _signingSecretKeyKey);
    if (key == null) return null;
    return base64.decode(key);
  }

  /// Get encryption public key (for sharing with senders)
  Future<Uint8List?> getEncryptionPublicKey() async {
    final key = await _secureStorage.read(key: _encryptionPublicKeyKey);
    if (key == null) return null;
    return base64.decode(key);
  }

  /// Get encryption secret key (for decryption)
  Future<Uint8List?> getEncryptionSecretKey() async {
    final key = await _secureStorage.read(key: _encryptionSecretKeyKey);
    if (key == null) return null;
    return base64.decode(key);
  }

  /// Store link token
  Future<void> storeLinkToken(String linkToken) async {
    await _secureStorage.write(key: _linkTokenKey, value: linkToken);
  }

  /// Get link token
  Future<String?> getLinkToken() async {
    return await _secureStorage.read(key: _linkTokenKey);
  }

  /// Store fetch token (very sensitive!)
  Future<void> storeFetchToken(String fetchToken) async {
    await _secureStorage.write(key: _fetchTokenKey, value: fetchToken);
  }

  /// Get fetch token
  Future<String?> getFetchToken() async {
    return await _secureStorage.read(key: _fetchTokenKey);
  }

  /// Sign a message using Ed25519
  Future<Uint8List> signMessage(Uint8List message) async {
    await initialize();
    final secretKey = await getSigningSecretKey();
    if (secretKey == null) {
      throw Exception('Signing key not found. Please complete registration.');
    }

    final signature = _sodium!.crypto.sign.detached(
      message: message,
      secretKey: SecureKey.fromList(_sodium!, secretKey),
    );

    return signature;
  }

  /// Encrypt a message using sealed box (X25519)
  Future<Uint8List> encryptMessage(String message, Uint8List recipientPublicKey) async {
    await initialize();
    
    final messageBytes = Uint8List.fromList(utf8.encode(message));
    
    final encrypted = _sodium!.crypto.box.seal(
      message: messageBytes,
      publicKey: recipientPublicKey,
    );

    return encrypted;
  }

  /// Decrypt a message using sealed box (X25519)
  Future<String> decryptMessage(Uint8List encryptedMessage) async {
    await initialize();
    
    final secretKey = await getEncryptionSecretKey();
    final publicKey = await getEncryptionPublicKey();
    
    if (secretKey == null || publicKey == null) {
      throw Exception('Encryption keys not found. Please complete registration.');
    }

    final decrypted = _sodium!.crypto.box.sealOpen(
      cipherText: encryptedMessage,
      publicKey: publicKey,
      secretKey: SecureKey.fromList(_sodium!, secretKey),
    );

    return utf8.decode(decrypted);
  }

  /// Check if keys are already generated
  Future<bool> hasKeys() async {
    final signingPub = await _secureStorage.read(key: _signingPublicKeyKey);
    final encryptionPub = await _secureStorage.read(key: _encryptionPublicKeyKey);
    return signingPub != null && encryptionPub != null;
  }

  /// Check if registered with server (has link and fetch tokens)
  Future<bool> isRegistered() async {
    final linkToken = await getLinkToken();
    final fetchToken = await getFetchToken();
    return linkToken != null && fetchToken != null;
  }

  /// Clear all stored keys (for testing or reset)
  Future<void> clearAll() async {
    await _secureStorage.deleteAll();
  }

  /// Generate both keypairs and store them
  Future<Map<String, Uint8List>> generateAndStoreKeys() async {
    await initialize();

    // Generate Ed25519 keypair for signing/authentication
    final signingKeyPair = await generateSigningKeyPair();
    await storeSigningKeyPair(signingKeyPair);

    // Generate X25519 keypair for encryption
    final encryptionKeyPair = await generateEncryptionKeyPair();
    await storeEncryptionKeyPair(encryptionKeyPair);

    return {
      'signing_public': signingKeyPair.publicKey,
      'encryption_public': encryptionKeyPair.publicKey,
    };
  }
}
