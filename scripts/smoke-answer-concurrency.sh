#!/usr/bin/env bash
#
# Smoke test for W3-F2 scoring: concurrent answer submissions must never
# double-score a question. Proves the SELECT FOR UPDATE lock + the
# (session_id, question_index) unique constraint hold against real Postgres —
# the behaviour the hermetic SQLite suite cannot exercise.
#
# Requires the stack running (./start.sh). Override creds/host via env.
#
#   ./scripts/smoke-answer-concurrency.sh
#
set -uo pipefail

BASE="${BASE:-https://localhost/api/v1}"
EMAIL="${EMAIL:-rev-eval.test002@yopmail.com}"
PASSWORD="${PASSWORD:-password123}"
N="${N:-5}"  # number of concurrent submitters

jq_get() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }
pg() { docker compose exec -T postgres psql -U root -d eval_ai_dev -t -A -c "$1" | tr -d '[:space:]'; }

echo "1) Login as participant ($EMAIL)..."
TOKEN=$(curl -sk -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq_get 'd.get("access_token","")')
[ -z "$TOKEN" ] && { echo "   login failed"; exit 1; }
echo "   got token."

echo "2) Find a quiz test that can start a session (probing test_id 1..40)..."
SID=""; QID=""
for TID in $(seq 1 40); do
  RESP=$(curl -sk -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d "{\"test_id\":$TID}")
  SID=$(echo "$RESP" | jq_get 'd.get("session_id","")')
  if [ -n "$SID" ]; then
    QID=$(echo "$RESP" | jq_get '(d.get("question") or {}).get("id","")')
    IDX0=$(echo "$RESP" | jq_get 'd.get("current_index",0)')
    echo "   started session $SID on test_id=$TID; answering index=$IDX0 question=$QID"
    break
  fi
done
[ -z "$SID" ] || [ -z "$QID" ] && { echo "   no startable quiz test found"; exit 1; }

echo "3) Fire $N concurrent answers (distinct keys, same question)..."
codes=$(mktemp)
for i in $(seq 1 "$N"); do
  curl -sk -o /dev/null -w "%{http_code}\n" -X POST "$BASE/sessions/$SID/answer" \
    -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: race-$i" \
    -H "Content-Type: application/json" \
    -d "{\"question_id\":\"$QID\",\"submitted_answers\":[1]}" >>"$codes" &
done
wait
echo "   HTTP codes: $(sort "$codes" | uniq -c | tr '\n' ' ')"
WINS=$(grep -c '^200$' "$codes"); rm -f "$codes"

echo "4) DB invariants (robust to session reuse — assert against answered index $IDX0)..."
DUPES=$(pg "SELECT count(*) FROM (SELECT question_index FROM session_answers WHERE session_id='$SID' GROUP BY question_index HAVING count(*)>1) x;")
ATIDX=$(pg "SELECT count(*) FROM session_answers WHERE session_id='$SID' AND question_index=$IDX0;")
IDX=$(pg "SELECT current_index FROM quiz_sessions WHERE session_id='$SID';")
echo "   200 responses     : $WINS   (want 1)"
echo "   duplicate idx rows : $DUPES  (want 0)"
echo "   rows at index $IDX0   : $ATIDX  (want 1)"
echo "   current_index      : $IDX   (want $((IDX0 + 1)))"

if [ "$WINS" = "1" ] && [ "$DUPES" = "0" ] && [ "$ATIDX" = "1" ] && [ "$IDX" = "$((IDX0 + 1))" ]; then
  echo "✅ PASS: exactly one submit scored; no double-scoring under concurrency."
  exit 0
fi
echo "❌ FAIL: see values above."
exit 1
