# W2-F6 — Structured Question Authoring Interface

*Create a robust interactive form in the Next.js frontend to allow trainers to add new questions into the MongoDB database.*

* **Curriculum Fit**: Day 9 (Next.js 16 App Router, Form State Management with React Hook Form, Client-Side Validation with Zod, Component composition with Tailwind and Shadcn).
* **Prerequisites**: Day 9 topics.
* **Required for**: W3-F3 (Test-Taking Frontend Skeleton — question documents must exist in MongoDB for a session to sample and render a first question on page load)
* **Time Estimate**: Without AI tools: 5–8 hours | With AI tools (Gemini/Claude Code): 3–5 hours

## Implementation Details

1. Build an `/admin/questions/create` page in Next.js.
2. Create a form structure using react-hook-form that dynamically alters its fields based on the selected question type (e.g., rendering options arrays for MCQ/MULTI vs. a simple checkbox for TRUE_FALSE).
3. Formulate a Zod validation schema ensuring that MCQ questions have exactly one correct answer selected, MULTI questions have at least one correct answer selected, and all options have non-empty text.
4. Submit the validated form payload via an API call through the API gateway.
