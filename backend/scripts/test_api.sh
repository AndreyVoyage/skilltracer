#!/bin/bash
# Test API endpoints with user_id fallback

set -e

BASE_URL="https://skilltracer.art-artel.su"
USER_ID="6072711152"

echo "=== Testing Health ==="
curl -s "$BASE_URL/health" | python3 -m json.tool

echo ""
echo "=== Testing Week Entries (fallback auth) ==="
curl -s "$BASE_URL/api/v1/entries/week?start_date=2026-04-13&user_id=$USER_ID" | python3 -m json.tool

echo ""
echo "=== Testing User Trackers ==="
curl -s "$BASE_URL/api/user/$USER_ID/trackers" | python3 -m json.tool

echo ""
echo "=== Testing Week Debug ==="
curl -s "$BASE_URL/api/v1/entries/week/debug?start_date=2026-04-13&user_id=$USER_ID" | python3 -m json.tool

echo ""
echo "All tests passed!"
