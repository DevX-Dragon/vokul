<p align="center">
  <img src="https://cdn.hackclub.com/019ee55a-4ff3-795e-8a97-2a290171b177/app_rounded.png" alt="App Logo" width="100">
</p>

<h1 align="center"> Vokul</h1>

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/DevX-Dragon/vokul)](https://github.com/DevX-Dragon/vokul/main/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/vokul)](https://pypi.org/project/vokul/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vokul)](https://pypi.org/project/vokul/)
![Hours Spent](https://hackatime-badge.hackclub.com/U0A0M7YSS84/VOKUL-CLI/)

</div>

**Vokul** is a local-first command-line interface (CLI) password manager designed for security and ease of use. It allows you to securely store, retrieve, and manage your sensitive credentials directly on your machine, encrypted with a master password.

## Features

- **Local-First Storage**: Your data stays on your machine, never touching external servers.
- **Strong Encryption**: Utilizes `cryptography` with AES-GCM and Argon2id for key derivation.
- **CLI Interface**: Manage your vault efficiently from the terminal.
- **TOTP Support**: Generate Time-based One-Time Passwords for 2FA-enabled services.
- **Password History**: Keeps a short history of previous passwords for each service.
- **Clipboard Integration**: Automatically copies passwords to clipboard and clears them after a short delay.
- **Security Throttling**: Protects against brute-force attacks with persistent lockout mechanisms.
- **Vault Backup & Recovery**: Automatic backups and self-healing from corrupted vaults.
- **JSON Output**: Supports machine-readable output for integration with other tools.

## Installation

### Prerequisites

- Python 3.8 or higher

### Using pip (Recommended)

```bash
pip install vokul
```

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/vokul-cli.git
   cd vokul-cli
   ```
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Quick Start

### 1. Initialize Your Vault

Before you can use VOKUL, you need to initialize a new vault and set your master password. This will create a `vault.vk` file in your current directory.

```bash
vokul init
```

### 2. Add a New Service

Store credentials for a new service. You will be prompted for the password if not provided directly.

```bash
vokul add --service github
vokul add --service mybank --password "StrongP@ssw0rd!" --totp "JBSWY3DPEHPK3PXP"
```

### 3. Retrieve a Password

Get a password for a service. By default, it copies to your clipboard and clears after 15 seconds.

```bash
vokul get --service github
```

To display the password directly in the terminal (use with caution):

```bash
vokul get --service github --show
```

### 4. Generate a TOTP Code

If you've stored a TOTP secret, you can generate the current 2FA code.

```bash
vokul totp --service mybank
```

### 5. List All Services

See all services stored in your vault.

```bash
vokul list
```

### 6. Generate a Strong Password

Create a new strong password. You can specify length, exclude symbols, or generate a memorable passphrase.

```bash
vokul generate --length 20
vokul generate --memorable
vokul generate --no-symbols
```

### 7. Delete a Service

Remove a service from your vault. This requires confirmation.

```bash
vokul delete --service oldservice
```

### 8. Destruct Your Vault

Permanently delete your entire vault file. **This action is irreversible.**

```bash
vokul destruct --force
```

## Usage

For a full list of commands and options, use the `--help` flag:

```bash
vokul --help
vokul [command] --help
```

## Contributing

Contributions are welcome! Please see the `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Contact

For questions or feedback, please open an issue on the GitHub repository.
