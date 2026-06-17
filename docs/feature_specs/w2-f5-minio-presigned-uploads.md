# W2-F5 — Direct-to-MinIO Diagram Uploads via Pre-Signed URLs

*Allow question creators to upload and attach architectural diagrams or screenshots directly to MinIO when authoring questions.*

* **Curriculum Fit**: Day 8 (MinIO Pre-signed URLs, MongoDB document modeling) & Day 9 (Direct-to-MinIO uploads).
* **Prerequisites**: Day 8 and 9 topics.
* **Required for**: W3-F1 (Quiz Session Creation Backend — question-management-service must have seeded question documents for the `$sample` aggregation to return results when a session is created)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–3 hours

## Implementation Details

1. Add an endpoint `GET /questions/presigned-upload-url` in question-management-service that uses boto3 to generate a pre-signed PUT URL for MinIO.
2. In the Next.js frontend, implement a file-input field inside the question creator form.
3. Use Zod client-side validation to restrict file types (e.g., `.png`, `.jpg` only) and cap file size at 5MB.
4. Upon selecting a file, the frontend fetches the pre-signed URL, performs a direct PUT upload from the browser to MinIO, and saves the object key/path inside the question's MongoDB document.
