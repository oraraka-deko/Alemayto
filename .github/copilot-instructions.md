<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements
	<!-- Python backend server with simplex link-based E2EE chat using libsodium sealed boxes -->

- [x] Scaffold the Project
	<!--
	Project scaffolded with Flask backend, MariaDB integration, 
	PyNaCl for sealed box encryption, challenge-response authentication,
	and cPanel hosting compatibility.
	Files created: app.py, database.py, utils.py, requirements.txt, .env, README.md, test_new_api.py
	-->

- [x] Customize the Project
	<!--
	Project customized for simplex link-based chat with:
	- End-to-end encryption using NaCl sealed boxes
	- Ed25519 for authentication signatures
	- X25519 for message encryption
	- Link token and fetch token system
	- Challenge-response authentication
	- Anonymous message sending
	- Secure message retrieval
	- MariaDB database with proper schema
	- Comprehensive API endpoints
	-->

- [x] Install Required Extensions
	<!-- No specific extensions required for this Python Flask project -->

- [x] Compile the Project
	<!--
	Dependencies installed successfully including PyNaCl.
	Application imports and runs without errors.
	Database connection working with MariaDB.
	All utility functions tested and working.
	-->

- [x] Create and Run Task
	<!--
	Created Flask server task for running the application.
	Task configured to run in background mode.
	 -->

- [x] Launch the Project
	<!--
	Project successfully launched with MariaDB database.
	All API endpoints implemented and tested:
	- /health - Health check
	- /register - Client registration with Ed25519 public key
	- /send - Anonymous encrypted message sending
	- /challenge_request - Challenge nonce generation
	- /fetch - Authenticated message retrieval
	- /ack - Message acknowledgment
	Database tables created: clients, messages, challenges
	Server running on http://localhost:5000
	 -->

- [x] Ensure Documentation is Complete
	<!--
	README.md complete with comprehensive API documentation.
	Includes cryptography details, setup instructions, and security best practices.
	test_new_api.py provides full end-to-end testing with real NaCl encryption.
	All tests passing successfully.
	End-to-end encryption verified - server never sees plaintext.
	All copilot-instructions.md steps completed successfully.
	 -->