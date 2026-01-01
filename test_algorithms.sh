#!/bin/bash

# Test script to demonstrate all 4 rate limiting algorithms

API="http://localhost:8001/api"

echo "========================================="
echo "Rate Limiter System - Algorithm Testing"
echo "========================================="
echo ""

# Clean up previous test data
echo "1. Resetting system..."
curl -s -X DELETE "$API/reset-stats" > /dev/null
echo "✓ System reset complete"
echo ""

# Create API keys for each algorithm
echo "2. Creating API keys..."
TB_KEY=$(curl -s -X POST "$API/api-keys" -H "Content-Type: application/json" -d '{"name": "Token Bucket Test"}' | jq -r '.api_key')
LB_KEY=$(curl -s -X POST "$API/api-keys" -H "Content-Type: application/json" -d '{"name": "Leaky Bucket Test"}' | jq -r '.api_key')
FW_KEY=$(curl -s -X POST "$API/api-keys" -H "Content-Type: application/json" -d '{"name": "Fixed Window Test"}' | jq -r '.api_key')
SW_KEY=$(curl -s -X POST "$API/api-keys" -H "Content-Type: application/json" -d '{"name": "Sliding Window Test"}' | jq -r '.api_key')
echo "✓ Created 4 API keys"
echo ""

# Configure rate limits (5 requests per 10 seconds for easy testing)
echo "3. Configuring rate limits (5 requests per 10 seconds)..."
curl -s -X POST "$API/rate-limit-configs" -H "Content-Type: application/json" -d "{\"api_key\": \"$TB_KEY\", \"algorithm\": \"token_bucket\", \"max_requests\": 5, \"window_seconds\": 10}" > /dev/null
curl -s -X POST "$API/rate-limit-configs" -H "Content-Type: application/json" -d "{\"api_key\": \"$LB_KEY\", \"algorithm\": \"leaky_bucket\", \"max_requests\": 5, \"window_seconds\": 10}" > /dev/null
curl -s -X POST "$API/rate-limit-configs" -H "Content-Type: application/json" -d "{\"api_key\": \"$FW_KEY\", \"algorithm\": \"fixed_window\", \"max_requests\": 5, \"window_seconds\": 10}" > /dev/null
curl -s -X POST "$API/rate-limit-configs" -H "Content-Type: application/json" -d "{\"api_key\": \"$SW_KEY\", \"algorithm\": \"sliding_window\", \"max_requests\": 5, \"window_seconds\": 10}" > /dev/null
echo "✓ Configured all 4 algorithms"
echo ""

# Test Token Bucket
echo "4. Testing Token Bucket Algorithm..."
echo "   Sending 7 requests rapidly..."
for i in {1..7}; do
  RESULT=$(curl -s -X GET "$API/protected/test?api_key=$TB_KEY")
  if echo "$RESULT" | jq -e '.success' > /dev/null 2>&1; then
    REMAINING=$(echo "$RESULT" | jq -r '.remaining_quota')
    echo "   Request $i: ✓ Allowed (Remaining: $REMAINING)"
  else
    echo "   Request $i: ✗ Blocked (Rate limit exceeded)"
  fi
done
echo ""

# Test Leaky Bucket
echo "5. Testing Leaky Bucket Algorithm..."
echo "   Sending 7 requests rapidly..."
for i in {1..7}; do
  RESULT=$(curl -s -X GET "$API/protected/test?api_key=$LB_KEY")
  if echo "$RESULT" | jq -e '.success' > /dev/null 2>&1; then
    REMAINING=$(echo "$RESULT" | jq -r '.remaining_quota')
    echo "   Request $i: ✓ Allowed (Remaining: $REMAINING)"
  else
    echo "   Request $i: ✗ Blocked (Rate limit exceeded)"
  fi
done
echo ""

# Test Fixed Window
echo "6. Testing Fixed Window Algorithm..."
echo "   Sending 7 requests rapidly..."
for i in {1..7}; do
  RESULT=$(curl -s -X GET "$API/protected/test?api_key=$FW_KEY")
  if echo "$RESULT" | jq -e '.success' > /dev/null 2>&1; then
    REMAINING=$(echo "$RESULT" | jq -r '.remaining_quota')
    echo "   Request $i: ✓ Allowed (Remaining: $REMAINING)"
  else
    echo "   Request $i: ✗ Blocked (Rate limit exceeded)"
  fi
done
echo ""

# Test Sliding Window
echo "7. Testing Sliding Window Algorithm..."
echo "   Sending 7 requests rapidly..."
for i in {1..7}; do
  RESULT=$(curl -s -X GET "$API/protected/test?api_key=$SW_KEY")
  if echo "$RESULT" | jq -e '.success' > /dev/null 2>&1; then
    REMAINING=$(echo "$RESULT" | jq -r '.remaining_quota')
    echo "   Request $i: ✓ Allowed (Remaining: $REMAINING)"
  else
    echo "   Request $i: ✗ Blocked (Rate limit exceeded)"
  fi
done
echo ""

# Show final statistics
echo "8. Final Statistics:"
echo "========================================="
curl -s -X GET "$API/analytics/summary" | jq '{
  total_requests,
  allowed_requests,
  blocked_requests,
  success_rate,
  algorithm_stats: .algorithm_stats | to_entries | map({
    algorithm: .key,
    total: .value.total,
    allowed: .value.allowed,
    blocked: .value.blocked,
    success_rate: .value.success_rate
  })
}'
echo ""
echo "========================================="
echo "Test Complete! Visit the dashboard to see live data."
echo "========================================="
