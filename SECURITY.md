# Security notes

- Never commit `.env`, passwords, tokens, cookies, signed asset URLs, or authorization headers.
- Use `scripts/setup_credentials.py`; do not pass passwords on the command line.
- Review AOIs before publication. Some stakeholder boundaries may be sensitive.
- Generated `outputs/` are ignored because vendor metadata or asset links may require review before sharing.
- If a secret is committed, revoke or rotate it immediately; deleting the file from the latest commit is not sufficient.

