# Testing SQS Integration

## Prerequisites

1. **AWS SQS Queue Setup**
   - Create an SQS queue (Standard or FIFO)
   - **Standard Queue**: Best for high throughput, at-least-once delivery
   - **FIFO Queue**: Ordered messages, exactly-once processing (queue name must end with `.fifo`)
   - Note the Queue URL
   - Set up IAM credentials with `sqs:SendMessage` and `sqs:GetQueueAttributes` permissions

   **Queue Type Detection**: The code automatically detects queue type from URL:
   - FIFO: URL ends with `.fifo` (e.g., `https://sqs.us-west-1.amazonaws.com/123456789/my-queue.fifo`)
   - Standard: URL doesn't end with `.fifo` (e.g., `https://sqs.us-west-1.amazonaws.com/123456789/my-queue`)

2. **Configure Environment Variables**

   Edit `.env` file:
   ```bash
   AWS_REGION=us-west-1
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   SQS_QUEUE_URL=https://sqs.us-west-1.amazonaws.com/123456789/your-queue-name
   SQS_ENABLED=True
   ```

## Step 1: Check SQS Configuration

### Test SQS Health Endpoint
```bash
curl http://localhost:8001/health/sqs
```

**Expected Response:**
```json
{
  "sqs_enabled": true,
  "sqs_configured": true,
  "sqs_connected": true,
  "queue_url": "https://sqs.us-west-1.amazonaws.com/...",
  "aws_region": "us-west-1"
}
```

## Step 2: Check Service Logs

When the service starts, you should see:
```
============================================================
🔍 Verifying SQS Configuration on Startup
============================================================
🔧 Initializing SQS Client...
   AWS_REGION: us-west-1
   SQS_ENABLED: True
   SQS_QUEUE_URL: https://sqs.us-west-1.amazonaws.com/...
   AWS_ACCESS_KEY_ID: SET
   AWS_SECRET_ACCESS_KEY: SET
✅ SQS Client initialized with explicit credentials for region: us-west-1
🔍 Verifying SQS connection...
✅ SQS connection verified successfully!
   Queue ARN: arn:aws:sqs:us-west-1:123456789:queue-name
   Messages in queue: 0
============================================================
```

## Step 3: Test Bulk Assignment

### Sample Bulk Assign Request
```bash
curl -X POST http://localhost:8001/v1/api/submissions/bulk-assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "test_id": 1,
    "participant_emails": [
      "krishnagopika1701@gmail.com",
      "krishnagopikaurlaganti4@gmail.com"
    ],
    "due_date": "2024-11-15T23:59:59"
  }'
```

### Watch Logs for SQS Publishing

When bulk assignment runs, you should see **individual logs for EACH participant**:

**For each participant:**
```
📤 Publishing TEST_ASSIGNED event for krishnagopika1701@gmail.com (submission_id: 123)
📤 Attempting to publish event: TEST_ASSIGNED
📝 Message body prepared (size: 512 bytes)
   Standard queue - skipping FIFO parameters
📨 Sending message to SQS queue: https://sqs.us-west-1.amazonaws.com/...
✅ Event published to SQS successfully!
   Event Type: TEST_ASSIGNED
   Message ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
   MD5 Hash: 5d41402abc4b2a76b9719d911017c592
   Queue URL: https://sqs.us-west-1.amazonaws.com/...
✅ TEST_ASSIGNED event published successfully for krishnagopika1701@gmail.com

📤 Publishing TEST_ASSIGNED event for krishnagopikaurlaganti4@gmail.com (submission_id: 124)
📤 Attempting to publish event: TEST_ASSIGNED
📝 Message body prepared (size: 514 bytes)
   Standard queue - skipping FIFO parameters
📨 Sending message to SQS queue: https://sqs.us-west-1.amazonaws.com/...
✅ Event published to SQS successfully!
   Event Type: TEST_ASSIGNED
   Message ID: b2c3d4e5-f6a7-8901-bcde-f12345678901
   MD5 Hash: 6d42502bce5c3b87c7820e922018d593
   Queue URL: https://sqs.us-west-1.amazonaws.com/...
✅ TEST_ASSIGNED event published successfully for krishnagopikaurlaganti4@gmail.com

✅ Bulk assignment completed: 2 successful, 0 failed
```

**Each participant gets their own complete event** with test name, assigned date, duration, and skills.

## Step 4: Verify Messages in SQS

### Check AWS Console
1. Go to AWS SQS Console
2. Select your queue
3. Click "Send and receive messages"
4. Click "Poll for messages"
5. You should see the messages in the queue

### Check via AWS CLI
```bash
aws sqs receive-message \
  --queue-url https://sqs.us-west-1.amazonaws.com/YOUR_ACCOUNT/YOUR_QUEUE \
  --region us-west-1 \
  --max-number-of-messages 10
```

## Troubleshooting

### Issue: "SQS client not initialized"
- Check that AWS credentials are set in `.env`
- Restart the service
- Check logs for initialization errors

### Issue: "SQS_QUEUE_URL not configured"
- Verify `SQS_QUEUE_URL` is set in `.env`
- Make sure it's the full URL (not just queue name)

### Issue: "AWS ClientError: AccessDenied"
- Verify IAM credentials have correct permissions
- Required permissions: `sqs:SendMessage`, `sqs:GetQueueAttributes`

### Issue: "InvalidMessageContents"
- Check that message size is under 256KB
- Verify JSON serialization is working

### Issue: Messages not appearing in queue
- Check `SQS_ENABLED=True` in `.env`
- Verify queue URL is correct
- Check AWS region matches
- Look for error logs during publishing
- Use `/health/sqs` endpoint to verify connectivity

### Issue: "InvalidParameterValue: MessageDeduplicationId is invalid"
**Cause**: Using a Standard queue but code is sending FIFO parameters.

**Solution**:
- The code now auto-detects queue type from URL
- Restart the service after updating `.env`
- Verify queue type with `/health/sqs` endpoint
- If using Standard queue, ensure URL doesn't end with `.fifo`
- If using FIFO queue, ensure URL ends with `.fifo`

### Issue: FIFO Queue Errors
- Ensure `MessageGroupId` is provided (code auto-adds "default" if missing)
- Ensure queue name ends with `.fifo`
- Check deduplication settings in AWS console

## Event Schemas

### TEST_ASSIGNED Event

**One event is sent for EACH participant** with complete test details:

```json
{
  "event_type": "TEST_ASSIGNED",
  "timestamp": "2024-10-30T12:00:00.000Z",
  "data": {
    "test_id": 1,
    "test_name": "Python Backend Assessment",
    "user_id": 123,
    "user_email": "krishnagopika1701@gmail.com",
    "assigned_by_id": 456,
    "submission_id": 789,
    "assigned_at": "2024-10-30T12:00:00.000Z",
    "due_date": "2024-11-15T23:59:59",
    "duration_minutes": 60,
    "skills": ["Python", "REST APIs", "SQL"],
    "role": "Backend Developer",
    "curriculum": "Python Full Stack",
    "active": true
  }
}
```

**Key Fields:**
- `test_name`: Name of the test
- `assigned_at`: When the test was assigned (start date)
- `due_date`: When the test is due
- `duration_minutes`: How long the test takes
- `skills`: Array of skills being tested
- `user_email`: Participant's email

**Note:** No bulk summary event is sent. Each participant gets their own individual event with complete information.

## Quick Commands

```bash
# Check service health
curl http://localhost:8001/health

# Check SQS health
curl http://localhost:8001/health/sqs

# View service logs (look for SQS messages)
# Terminal where service is running

# Test with LocalStack (for local development without AWS)
docker run -d -p 4566:4566 localstack/localstack
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name test-events
# Update SQS_QUEUE_URL to: http://localhost:4566/000000000000/test-events
```
