CSAS LMS - Hosting preparation

This archive is prepared for Python hosting platforms that accept a source repository. It does not itself publish the site online. You still need a hosting account and must upload/push this folder using a supported method.

Start command (if the platform asks): gunicorn app:app --bind 0.0.0.0:$PORT
Build/install command (if requested): pip install -r requirements.txt

Important limitations:
- This app uses SQLite stored in lms.db in the app folder. On many free hosting services, local files can be erased on redeploy/restart or may not be persistent. Do not use for real student records without a persistent database/storage and backups.
- Set environment variable LMS_SECRET_KEY to a long random secret before public deployment.
- Demo account credentials are documented in README.md; change/remove them before public use.
- This is an academic demo and is not security-hardened for production.
