# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security
vulnerability in OmniScript, please report it responsibly:

### Preferred: Private Disclosure

**Email**: security@omniscript.dev

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (if you have them)

We will acknowledge receipt within 48 hours and provide a preliminary
assessment within 7 days.

### Alternative: GitHub Security Advisories

You can also use GitHub's private vulnerability reporting:
1. Go to the repository's **Security** tab
2. Click **Report a vulnerability**
3. Fill in the details

## Response Process

1. **Acknowledgment** (48 hours): We confirm receipt and begin triage
2. **Triage** (7 days): We assess severity, impact, and affected versions
3. **Fix Development**: We develop and test a fix
4. **Disclosure Coordination**: We coordinate public disclosure timeline
5. **Release**: We publish a patch release with the fix
6. **Public Advisory**: We publish a GitHub Security Advisory

## Severity Classification

We use CVSS 3.1 for severity assessment:

| Severity | CVSS Range | Response Time |
|----------|------------|---------------|
| Critical | 9.0-10.0   | 24 hours      |
| High     | 7.0-8.9    | 72 hours      |
| Medium   | 4.0-6.9    | 7 days        |
| Low      | 0.1-3.9    | 30 days       |

## Security Best Practices for Contributors

- Never commit secrets, API keys, or credentials
- Use environment variables for configuration
- Run `bandit` and `ruff` before committing
- Keep dependencies updated (Dependabot alerts are monitored)
- Follow the principle of least privilege in code

## Security Features in OmniScript

- **Checked Effects**: Static effect system prevents unauthorized I/O
- **Capability-Based Security**: Fine-grained permissions (filesystem, network, etc.)
- **Input Validation**: String escaping in JS emitter prevents XSS
- **Secure Defaults**: AES-GCM encryption, PBKDF2 password hashing
- **Supply Chain**: Pinned dependencies, trusted publishing (OIDC)

## Contact

Security team: security@omniscript.dev