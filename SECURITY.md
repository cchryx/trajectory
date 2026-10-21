# Security

## Report a problem

Do not open a public issue for a security problem. Use the "Report a vulnerability" button on the [Security tab](https://github.com/cchryx/trajectory/security/advisories/new). Only the maintainer can see it.

Please include what you found and the steps to see it. You will get a reply within a week.

## Secrets

- Never commit passwords, API keys or `.env` files. `.gitignore` already skips `.env`.
- The live database password and API keys are GitHub secrets and Render settings. They are not in the code.
- If a secret is committed by mistake, change it right away. Deleting the commit is not enough, because the old value stays in Git history and forks.

## Resumes

Uploaded resumes are read in memory and never saved or logged. Pull requests that store or log resume text will not be merged.
