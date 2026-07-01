# Security Policy — Vokul

## Supported Versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| 0.1.x | No |

Only the latest major version of Vokul receives security patches and updates. Users running older versions are strongly encouraged to upgrade immediately.

---

## Reporting a Vulnerability

Vokul takes security vulnerabilities seriously. If you discover a vulnerability in the CLI, the browser extension, the native messaging bridge, or any other component of the ecosystem, please report it responsibly.

### How to Report

1. **Open a private issue** on the GitHub repository using the [security advisory template](https://github.com/DevX-Dragon/vokul-cli/security/advisories/new), or

1. **Email the maintainer** directly at a private address (see the repository's contact section for details).

### What to Include

When reporting a vulnerability, please provide as much detail as possible:

- **Description:** A clear explanation of the vulnerability and its potential impact.

- **Steps to Reproduce:** A step-by-step guide to trigger the issue.

- **Affected Version:** The version of Vokul where the vulnerability was observed.

- **Proof of Concept:** A minimal code snippet, script, or screenshot demonstrating the vulnerability (if applicable).

- **Suggested Fix:** If you have a proposed mitigation or fix, please include it.

### Response Timeline

| Phase | Target Timeline |
| --- | --- |
| Acknowledgement | Within 48 hours |
| Initial Assessment | Within 5 business days |
| Patch Development | Within 14 business days |
| Public Disclosure | After patch release |

### Coordinated Disclosure

We follow a **coordinated disclosure** model. This means that vulnerabilities will not be publicly disclosed until a patch has been developed, tested, and released. Reporters are expected to maintain confidentiality until the official disclosure.

---

## Security Architecture

This section documents the security measures currently implemented in Vokul to give users and auditors a clear picture of the threat model and defenses.

### Encryption Model

Vokul uses a two-layer cryptographic model for vault data protection.

| Layer | Algorithm | Purpose |
| --- | --- | --- |
| Key Derivation | Argon2id (64 MiB memory, 3 iterations, 4 threads) | Derives a 256-bit encryption key from the master password |
| Data Encryption | AES-256-GCM | Encrypts all vault records with authenticated encryption |

The **salt** is randomly generated during vault initialization and stored alongside the ciphertext. The **nonce** is unique for every encryption operation, preventing replay attacks and ensuring that identical plaintexts produce distinct ciphertexts.

### Brute-Force Protection

Vokul implements a **persistent, cross-session throttling mechanism** to defend against brute-force attacks on the master password. The system works as follows:

1. A hidden lock file (`.vault.vk.lock`) is maintained alongside the vault file.

1. Every failed password attempt is timestamped and persisted to disk.

1. Only attempts within the last **5 minutes** are counted toward the penalty.

1. After **3 failed attempts** within the window, a progressive lockout is enforced:
  - Base penalty: **15 seconds**
  - Additional penalty: **+10 seconds** per extra failed attempt

1. The lock file is cleared upon successful authentication or vault destruction.

This ensures that even across separate terminal sessions, an attacker cannot rapidly brute-force the master password.

### Data Locality and Privacy

Vokul is **local-first by design**. No credentials are ever transmitted to external servers. All data remains encrypted on the user's local filesystem. The only exception is the **native messaging bridge**, which forwards decrypted data to the Chrome extension via the operating system's native messaging API — a mechanism that requires explicit user consent and is sandboxed by the browser.

### Clipboard Security

When retrieving a password via `vokul get`, the password is copied to the system clipboard and **automatically cleared after 15 seconds**. This minimizes the window during which the plaintext password is exposed in memory or accessible to clipboard-monitoring malware.

### Backup and Recovery Integrity

Every vault save operation triggers an **automatic backup** to a timestamped file in the `backups/` directory. These backups are encrypted with the same key as the main vault, ensuring that recovered data maintains the same level of confidentiality and integrity as the original.

---

## Known Security Considerations

While Vokul implements strong security measures, users should be aware of the following considerations:

### Memory Exposure

During normal operation, decrypted passwords exist briefly in process memory before being copied to the clipboard. On systems with swap or hibernation enabled, this data could theoretically persist to disk. Users with extreme threat models should consider disabling swap or using full-disk encryption.

### Environment Variable Support

Vokul supports the `VOKUL_MASTER_PASSWORD` environment variable for non-interactive use. While convenient for scripting, users should be aware that environment variables can be visible to other processes on the same system (e.g., via `/proc` on Linux). This option should only be used in trusted environments.

### Extension Trust Boundary

The Chrome extension communicates with the CLI through the native messaging bridge. While the bridge enforces a strict message format, users should ensure they only install the extension from the official repository and that their browser is not compromised.

### File System Permissions

Vokul relies on the operating system's file system permissions to protect the vault file. Users should ensure that the directory containing `vault.vk` is not world-readable. On Unix-like systems, Vokul does not explicitly set restrictive file permissions — this is a responsibility of the user.

---

## Security Best Practices for Users

The following recommendations help maximize the security of your Vokul installation:

| Practice | Description |
| --- | --- |
| **Use a strong master password** | Aim for 16+ characters with a mix of upper/lower case, numbers, and symbols. Consider using `vokul generate --length 24` to create one. |
| **Enable full-disk encryption** | Use LUKS (Linux), FileVault (macOS), or BitLocker (Windows) to encrypt the entire drive where your vault is stored. |
| **Store vault in a secure location** | Place `vault.vk` in a directory with restricted permissions (e.g., `chmod 600`). |
| **Keep Vokul updated** | Regularly run `pip install --upgrade vokul` to receive the latest security patches. |
| **Review backup files** | Periodically verify that backup files in the `backups/` directory are present and intact. |
| **Use ****`--show`**** cautiously** | The `vokul get --show` flag prints passwords directly to the terminal, which may be captured in terminal history or logs. Prefer the default clipboard behavior. |
| **Rotate passwords regularly** | Use `vokul edit` to update passwords periodically and leverage the built-in password history for reference. |
| **Audit the vault** | Run `vokul list` periodically to review stored entries and `vokul history` to audit password changes. |

---

## For Security Researchers

If you are conducting a security audit of Vokul, the following resources may be helpful:

- **Source Code:** The entire codebase is open source and available on GitHub.

- **Documentation:** Comprehensive documentation is available in `docs/DOCUMENTATION.md`.

- **Cryptographic Parameters:** All Argon2id and AES-GCM parameters are defined in `src/vokul/core/params.py` and `src/vokul/core/crypto.py`.

- **CLI Entry Point:** All command logic is in `src/vokul/__main__.py`.

- **Vault Manager:** All vault lifecycle and CRUD operations are in `src/vokul/core/vault.py`.

---

## Changelog of Security Fixes

| Date | Version | Description |
| --- | --- | --- |
| 2026-06-28 | 1.0.0 | Initial release with Argon2id + AES-GCM encryption, persistent brute-force throttling, and automatic backup recovery. |

---

> **Disclaimer:** Vokul is provided "as is" without warranty of any kind. While every effort has been made to implement industry-standard security practices, no software is immune to vulnerabilities. Users should exercise reasonable caution and follow best practices when managing sensitive credentials.