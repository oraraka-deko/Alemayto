import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/crypto_service.dart';
import '../services/api_service.dart';
import '../utils/nickname_generator.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({Key? key}) : super(key: key);

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  final TextEditingController _serverUrlController = TextEditingController();
  final TextEditingController _nicknameController = TextEditingController();
  
  final CryptoService _cryptoService = CryptoService();
  final ApiService _apiService = ApiService();
  
  int _currentStep = 0;
  bool _isGeneratingKeys = false;
  bool _isConnecting = false;
  String? _errorMessage;
  String? _generatedLink;

  @override
  void initState() {
    super.initState();
    _serverUrlController.text = 'http://localhost:5000';
  }

  @override
  void dispose() {
    _pageController.dispose();
    _serverUrlController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  Future<void> _generateKeys() async {
    setState(() {
      _isGeneratingKeys = true;
      _errorMessage = null;
    });

    try {
      // Generate and store both keypairs
      await _cryptoService.generateAndStoreKeys();
      
      setState(() {
        _isGeneratingKeys = false;
      });
      
      // Move to next step
      _nextStep();
    } catch (e) {
      setState(() {
        _isGeneratingKeys = false;
        _errorMessage = 'Failed to generate keys: $e';
      });
    }
  }

  Future<void> _connectToServer() async {
    setState(() {
      _isConnecting = true;
      _errorMessage = null;
    });

    try {
      // Set server URL
      final serverUrl = _serverUrlController.text.trim();
      if (serverUrl.isEmpty) {
        throw Exception('Please enter a server URL');
      }
      
      _apiService.setBaseUrl(serverUrl);

      // Test connection
      final isHealthy = await _apiService.healthCheck();
      if (!isHealthy) {
        throw Exception('Server is not responding. Please check the URL.');
      }

      // Get public key for registration
      final signingPublicKey = await _cryptoService.getSigningPublicKey();
      if (signingPublicKey == null) {
        throw Exception('Public key not found');
      }

      final publicKeyBase64 = base64.encode(signingPublicKey);
      
      // Use nickname or generate random one
      String nickname = _nicknameController.text.trim();
      if (nickname.isEmpty) {
        nickname = NicknameGenerator.generate();
      }

      // Register with server
      final result = await _apiService.register(
        publicKeyBase64: publicKeyBase64,
        displayName: nickname,
      );

      if (result['success'] == true) {
        setState(() {
          _generatedLink = result['link'];
          _isConnecting = false;
        });

        // Save that we've completed onboarding
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('onboarding_complete', true);
        await prefs.setString('server_url', serverUrl);
        await prefs.setString('nickname', nickname);
        await prefs.setString('share_link', _generatedLink!);
        
        _nextStep();
      } else {
        throw Exception(result['error'] ?? 'Registration failed');
      }
    } catch (e) {
      setState(() {
        _isConnecting = false;
        _errorMessage = e.toString();
      });
    }
  }

  void _nextStep() {
    if (_currentStep < 2) {
      setState(() {
        _currentStep++;
      });
      _pageController.animateToPage(
        _currentStep,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      // Onboarding complete, navigate to main app
      Navigator.of(context).pushReplacementNamed('/home');
    }
  }

  Widget _buildStepIndicator() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (index) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          width: index == _currentStep ? 32 : 8,
          height: 8,
          decoration: BoxDecoration(
            color: index <= _currentStep
                ? Theme.of(context).primaryColor
                : Colors.grey.shade300,
            borderRadius: BorderRadius.circular(4),
          ),
        );
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ChiCrypt Setup'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: _buildStepIndicator(),
          ),
          Expanded(
            child: PageView(
              controller: _pageController,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _buildStep1(),
                _buildStep2(),
                _buildStep3(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // Step 1: Key Generation
  Widget _buildStep1() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.key,
            size: 80,
            color: Theme.of(context).primaryColor,
          ),
          const SizedBox(height: 32),
          const Text(
            'Secure Key Generation',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'We will generate encryption keys to secure your messages. Your private key stays only on this device and is encrypted.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 48),
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.red.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ],
              ),
            ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _isGeneratingKeys ? null : _generateKeys,
              icon: _isGeneratingKeys
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.vpn_key),
              label: Text(
                _isGeneratingKeys ? 'Generating...' : 'Generate Keys',
                style: const TextStyle(fontSize: 16),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Step 2: Server Configuration
  Widget _buildStep2() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.cloud,
            size: 80,
            color: Theme.of(context).primaryColor,
          ),
          const SizedBox(height: 32),
          const Text(
            'Server Configuration',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Enter your backend server URL and choose a nickname',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 32),
          TextField(
            controller: _serverUrlController,
            decoration: const InputDecoration(
              labelText: 'Server URL',
              hintText: 'http://localhost:5000',
              prefixIcon: Icon(Icons.link),
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nicknameController,
            decoration: InputDecoration(
              labelText: 'Nickname (optional)',
              hintText: 'Leave empty for random name',
              prefixIcon: const Icon(Icons.person),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: const Icon(Icons.shuffle),
                onPressed: () {
                  _nicknameController.text = NicknameGenerator.generate();
                },
                tooltip: 'Generate random nickname',
              ),
            ),
          ),
          const SizedBox(height: 24),
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.red.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ],
              ),
            ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _isConnecting ? null : _connectToServer,
              icon: _isConnecting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.cloud_upload),
              label: Text(
                _isConnecting ? 'Connecting...' : 'Connect & Register',
                style: const TextStyle(fontSize: 16),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Step 3: Success
  Widget _buildStep3() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.check_circle,
            size: 80,
            color: Colors.green,
          ),
          const SizedBox(height: 32),
          const Text(
            'Setup Complete!',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Your secure messaging link is ready. Share it with others to receive encrypted messages.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 32),
          if (_generatedLink != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Column(
                children: [
                  const Text(
                    'Your Link:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  SelectableText(
                    _generatedLink!,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 48),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _nextStep,
              icon: const Icon(Icons.arrow_forward),
              label: const Text(
                'Get Started',
                style: TextStyle(fontSize: 16),
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
