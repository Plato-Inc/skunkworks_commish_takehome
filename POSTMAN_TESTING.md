# Postman Collection for Commission Advance API Testing

This guide covers setting up and running end-to-end tests for the commission advance API using Postman.

## Quick Setup

### 1. Import the Collection and Environment

1. Open Postman
2. Import Collection: 
   - Click "Import" and select `postman_collection.json`
   - Collection name: "Commission Advance API"
3. Import Environment: 
   - Click "Import" and select `postman_environment.json`
   - Environment name: "Commission Advance Environment"

### 2. Start the API Server

```bash
# Make sure the API is running locally
make dev
# OR: uvicorn app.main:app --reload
```

Verify it's running by visiting: http://localhost:8000/docs

### 3. Set Up File Paths

For file upload requests, you need to configure the file paths in Postman:

1. Go to the "Advance Quote - Happy Path" request
2. In the Body tab, select form-data
3. Set the file paths:
   - `carrier_remittance`: Browse to `sample_data/carrier_remittance.csv`
   - `crm_policies`: Browse to `sample_data/crm_policies.csv`

## Test Scenarios Included

### Happy Path Tests
- Health Check: Verifies API is running and healthy
- Advance Quote - Happy Path: Full flow with sample data
- API Documentation: Tests Swagger UI availability
- OpenAPI Schema: Validates API specification

### Error Handling Tests
- Missing Carrier File: Tests validation when carrier remittance file is missing
- Missing CRM File: Tests validation when CRM policies file is missing

### Automated Test Assertions

Each request includes test scripts that verify:

**Health Check Tests:**
- Status code 200
- Response contains "healthy" status
- Timestamp field exists
- Version field exists

**Advance Quote Tests:**
- Status code 200
- Response structure (quotes array, metadata)
- Agent A001 hits $2,000 cap (business rule validation)
- All quotes contain required fields
- Data types are correct

**Error Handling Tests:**
- Proper HTTP status codes (422 for validation errors)
- Error messages are descriptive

## Running the Tests

### Option 1: Manual Testing
1. Select the "Commission Advance Environment"
2. Run requests individually to see detailed responses
3. Check the Test Results tab for assertion outcomes

### Option 2: Collection Runner (Automated)
1. Click on the collection name and select "Run collection"
2. Select all requests or specific ones
3. Choose the environment: "Commission Advance Environment"
4. Click "Run Commission Advance API"
5. View the test report with pass/fail results

### Option 3: Command Line (Newman)
```bash
# Install Newman (Postman CLI)
npm install -g newman

# Run the collection
newman run postman_collection.json -e postman_environment.json

# Generate HTML report
newman run postman_collection.json -e postman_environment.json -r html
```

## Environment Configuration

The environment includes variables for different deployment stages:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `base_url` | `http://localhost:8000` | Local development URL |
| `prod_url` | `https://your-production-domain.azurewebsites.net` | Production URL (update after deployment) |
| `staging_url` | `https://your-staging-domain.azurewebsites.net` | Staging URL (update after deployment) |

### Switching Environments
1. Local Development: Use `base_url` (default)
2. Production Testing: 
   - Edit environment
   - Enable `prod_url` and disable `base_url`
   - Update the `prod_url` value with your actual deployment URL

## Expected Test Results

### Happy Path Response Example
```json
{
  "generated_at": "2025-07-06T12:00:00.000Z",
  "quotes": [
    {
      "agent_id": "A001",
      "earned_to_date": 1500.0,
      "total_eligible_remaining": 3000.0,
      "safe_to_advance": 2000.0,
      "eligible_policies_count": 5
    }
  ],
  "total_agents": 3,
  "total_policies_analyzed": 15
}
```

### Key Business Rules Validated
- $2,000 Cap: Agent A001 should hit the maximum advance limit
- 80% Rule: Safe-to-advance = min(0.80 × remaining_expected, $2,000)
- 7-Day Eligibility: Only policies submitted ≥7 days ago are eligible
- Active Status: Only active policies count toward advances

## Troubleshooting

### Common Issues

**"Cannot read file" Error:**
- Ensure file paths are correct in the form-data section
- Use absolute paths if relative paths don't work
- Make sure CSV files exist in `sample_data/` directory

**Connection Refused:**
- Verify the API server is running: `curl http://localhost:8000/health`
- Check if port 8000 is available
- Ensure virtual environment is activated

**Test Failures:**
- Check the **Test Results** tab for specific assertion failures
- Verify response structure matches expected format
- Ensure sample data hasn't been modified

**File Upload Issues:**
- Postman requires manual file selection for security
- You cannot set file paths programmatically in collections
- Each team member needs to configure file paths locally

### Performance Monitoring

The collection automatically logs response times for each request. Look for:
- Health check: < 50ms
- Advance quote: < 500ms (depends on data size)
- Documentation: < 200ms

## Advanced Testing Scenarios

### Custom Test Data
To test with your own data:
1. Create CSV files following the required schema
2. Update file paths in the request body
3. Modify test assertions if needed

### Load Testing
```bash
# Run multiple iterations
newman run postman_collection.json -e postman_environment.json -n 10

# With delay between requests
newman run postman_collection.json -e postman_environment.json -n 10 --delay-request 1000
```

### CI/CD Integration
Add to your GitHub Actions or CI pipeline:
```yaml
- name: Run API Tests
  run: |
    newman run postman_collection.json -e postman_environment.json --reporters cli,junit
```

## Adding More Tests

To extend the collection:
1. Duplicate existing requests and modify them
2. Add test scripts in the Tests tab using Postman's test library
3. Create new test data files for edge cases
4. Update environment variables as needed

### Example: Adding a Claw-back Test
```javascript
pm.test("Handles negative payments correctly", function () {
    var jsonData = pm.response.json();
    var agentWithClawback = jsonData.quotes.find(q => q.earned_to_date < 0);
    pm.expect(agentWithClawback).to.exist;
    pm.expect(agentWithClawback.total_eligible_remaining).to.be.at.least(0);
});
```

This collection provides comprehensive testing coverage for the commission advance API. 