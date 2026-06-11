#!/usr/bin/env bash
#
# W3-F6 e2e pre-flight: make sure the Mongo question bank can satisfy session
# minting. Compose does not auto-seed questions (seed_rag_context_questions.py
# needs httpx, absent in the QMS image) and an empty bank makes POST /sessions
# return 422, so the Playwright run would die on the first Start click.
#
# Idempotent: if the `questions` collection already holds >= MIN_QUESTIONS
# documents it does nothing. Inserted docs mirror the W3-F5 integration
# fixture shape and are tagged `e2e-seed`.
#
# Usage: ./scripts/e2e-seed.sh   (stack already up: docker compose up -d --wait)

set -euo pipefail

MIN_QUESTIONS="${MIN_QUESTIONS:-30}"
MONGO_USER="${MONGO_USER:-admin}"
MONGODB_PASSWORD="${MONGODB_PASSWORD:-admin}"
MONGO_DB="${MONGO_DB:-evalai}"

docker compose exec -T mongo mongosh --quiet \
  -u "$MONGO_USER" -p "$MONGODB_PASSWORD" --authenticationDatabase admin \
  "$MONGO_DB" --eval "
const min = ${MIN_QUESTIONS};
const existing = db.questions.countDocuments();
if (existing >= min) {
  print('question bank already has ' + existing + ' docs (>= ' + min + '), skipping seed');
} else {
  const now = new Date();
  const docs = [];
  for (let i = existing; i < min; i++) {
    docs.push({
      type: 'mcq',
      question_text: 'E2E seed question ' + i + ' — pick option two.',
      options: [1, 2, 3, 4].map(j => ({ option_id: j, text: 'Option ' + j + ' of question ' + i })),
      correct_answers: [2],
      answer_explanation: 'Seeded by scripts/e2e-seed.sh for the W3-F6 happy path.',
      difficulty: 'easy',
      skills: [],
      tags: ['e2e-seed'],
      created_at: now,
      updated_at: now,
    });
  }
  db.questions.insertMany(docs);
  print('seeded ' + docs.length + ' questions (collection now ' + db.questions.countDocuments() + ')');
}
"
