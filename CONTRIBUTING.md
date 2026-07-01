# Contributing to Vokul

Thank you for your interest in contributing to Vokul! As a local-first, open-source password manager, security and data integrity are our top priorities. We welcome contributions from the community to help improve the CLI tool, the browser extension, and the overall ecosystem.

This guide provides an overview of the development process, coding standards, and guidelines for submitting changes.

## Table of Contents

- [Getting Started](#getting-started)

- [Development Environment](#development-environment)

- [Coding Standards](#coding-standards)

- [Testing](#testing)

- [Submitting a Pull Request](#submitting-a-pull-request)

- [Security Guidelines](#security-guidelines)

## Getting Started

Before you begin, ensure you have the following prerequisites installed:

- Python 3.8 or higher

- Git

1. **Fork the repository** on GitHub.

1. **Clone your fork** to your local machine:

   ```bash
   git clone https://github.com/your-username/vokul-cli.git
   cd vokul-cli
   ```

1. **Create a new branch** for your feature or bug fix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

To set up your development environment, we recommend using a virtual environment.

1. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

1. **Install the project in editable mode** along with its dependencies:

   ```bash
   pip install -e .
   ```

1. **Run the CLI locally** to ensure everything is working:

   ```bash
   vokul version
   ```

## Coding Standards

We strive to maintain clean, readable, and secure code throughout the project.

### Python (CLI & Bridge )

- **Style Guide:** Follow PEP 8 standards. We recommend using tools like `black` for formatting and `flake8` or `pylint` for linting.

- **Type Hinting:** Use Python type hints (`typing` module) wherever possible to improve code clarity and static analysis.

- **Documentation:** Use docstrings to document functions, classes, and modules. Follow the Google or NumPy docstring format.

- **Error Handling:** Use the custom exception hierarchy defined in `vokul/core/exceptions.py` for all internal errors. Avoid catching generic `Exception` unless absolutely necessary.

### JavaScript (Browser Extension)

- **Style Guide:** Follow standard JavaScript best practices. If using ES6+ features, ensure compatibility with the target Chrome versions.

- **Manifest V3:** Adhere to Chrome's Manifest V3 guidelines for extensions, particularly regarding service workers and native messaging.

## Testing

While the project currently lacks an automated test suite, manual testing is crucial before submitting any changes.

### Manual Testing Checklist

- [ ] Initialize a new vault (`vokul init`)

- [ ] Add, edit, and delete services (`vokul add`, `vokul edit`, `vokul delete`)

- [ ] Retrieve passwords and verify clipboard integration (`vokul get`)

- [ ] Test TOTP generation (`vokul totp`)

- [ ] Verify password generation (`vokul generate`)

- [ ] Test brute-force throttling by intentionally entering the wrong master password multiple times

- [ ] Test vault recovery by manually corrupting the `vault.vk` file and verifying restoration from backup

If you add new features, please consider writing unit tests using `pytest` and placing them in a `tests/` directory.

## Submitting a Pull Request

When your changes are ready, please follow these steps:

1. **Commit your changes** with clear, descriptive commit messages:

   ```bash
   git add .
   git commit -m "feat: add support for vault export functionality"
   ```

1. **Push your branch** to your forked repository:

   ```bash
   git push origin feature/your-feature-name
   ```

1. **Open a Pull Request** against the `main` branch of the original repository.

1. **Provide context** in your PR description, explaining what changes were made and why. Link any related issues.

1. **Be responsive** to feedback from maintainers and be willing to make requested changes.

## Security Guidelines

Given the nature of this project (a password manager), security is paramount.

- **Do Not Commit Secrets:** Never commit real passwords, master keys, or private test data to the repository.

- **Audit Dependencies:** If you add new dependencies, ensure they are reputable and actively maintained.

- **Cryptography:** Do not modify the core cryptographic primitives (`Argon2id`, `AES-GCM`) without a thorough security audit and clear justification.

- **Data Privacy:** Ensure that all data remains local to the user's machine unless explicitly intended to be sent via the native messaging bridge.

Thank you for helping make Vokul a secure and reliable tool for everyone!
