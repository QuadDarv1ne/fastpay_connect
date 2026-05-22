#!/bin/bash
set -e
cd /c/Users/maksi/M--GitHub/fastpay-connect || exit 1

echo "=== Git Status ==="
git status

echo ""
echo "=== Staging files ==="
git add app/middleware/fraud_detection.py app/main.py app/utils/audit.py tests/test_audit_logging.py

echo ""
echo "=== Committing ==="
git commit -m "feat: add audit logging integration, fix silent exception handling, and add audit tests

- Wire audit logging into admin refund/cancel endpoints (v1, v2, legacy)
- Add audit log viewing endpoint with pagination and filtering (v2)
- Fix 7 silent except Exception blocks in fraud_detection.py - now logged
- Add logging to health check and readiness check database errors
- Add db.flush() before db.commit() in audit utility for ID generation safety
- Add test_audit_logging.py with model, utility, and endpoint tests"

echo ""
echo "=== Pushing to remote ==="
git push origin main

echo ""
echo "=== Listing branches ==="
git branch -a

echo ""
echo "=== Done ==="
