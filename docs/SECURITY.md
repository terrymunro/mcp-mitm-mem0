# Security & Reliability Features

This document describes the security and reliability features implemented in the MCP MITM Mem0 project.

## 🔐 Authentication

### Bearer Token Authentication

The FastAPI application supports bearer token authentication using the `AUTH_TOKEN` environment variable.

#### Configuration

```bash
# Required for authentication
export AUTH_TOKEN="your-secure-token-here"
```

#### Usage

```bash
# Make authenticated requests
curl -H "Authorization: Bearer your-secure-token-here" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test", "query": "test"}' \
     http://localhost:8000/search
```

#### Behavior

- **If `AUTH_TOKEN` is not set**: API is accessible without authentication (development mode)
- **If `AUTH_TOKEN` is set**: All endpoints require valid bearer token
- **Invalid/missing token**: Returns HTTP 401 Unauthorized

### Security Best Practices

1. **Use strong tokens**: Generate cryptographically secure tokens
2. **Rotate tokens**: Change tokens regularly
3. **Environment variables**: Store tokens securely in environment variables
4. **Never log tokens**: Tokens are automatically hidden in logs

## ⚡ Rate Limiting

Rate limiting is implemented using `slowapi` to prevent abuse and ensure fair usage.

### Rate Limits by Endpoint

| Endpoint | Rate Limit | Purpose |
|----------|------------|---------|
| `/health` | 10/minute | Health checks |
| `/search` | 30/minute | Memory search |
| `/list` | 20/minute | List memories |
| `/remember` | 20/minute | Add memories |
| `/forget` | 10/minute | Delete memories |

### Rate Limit Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1234567890
```

### Rate Limit Exceeded

When rate limit is exceeded, the API returns:

```json
{
  "error": "Rate limit exceeded",
  "detail": "30 per minute"
}
```

## 🛡️ Graceful Degradation

The application handles Mem0 service unavailability gracefully without crashing.

### Memory Service States

1. **Available**: Normal operation, all endpoints work
2. **Temporarily Unavailable**: Returns HTTP 503 with error details
3. **Not Initialized**: Returns HTTP 503 indicating service unavailable

### Error Handling

#### Connection Errors
```json
{
  "error": "Service unavailable",
  "details": "Memory service is temporarily unavailable",
  "status_code": 503
}
```

#### Service Not Initialized
```json
{
  "error": "Service unavailable", 
  "details": "Memory service is unavailable",
  "status_code": 503
}
```

### Health Check

The `/health` endpoint shows service status:

```json
{
  "status": "healthy",
  "memory_service_available": true,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔒 Secure Configuration

Sensitive environment variables are handled securely and never exposed in logs.

### Environment Variables

#### Required
- `OPENAI_API_KEY`: OpenAI API key for Mem0
- `MEM0_PROVIDER`: Mem0 provider (e.g., "openai")
- `MODEL_NAME`: Model name to use (e.g., "gpt-4")

#### Optional
- `AUTH_TOKEN`: Bearer token for API authentication
- `SERVER_HOST`: Server host (default: localhost)
- `SERVER_PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: false)

### Security Features

1. **Masked Logging**: Sensitive values are replaced with `***` in logs
2. **Safe Dump**: `settings.safe_dump()` provides logging-safe configuration
3. **Warnings**: Warns when sensitive data might be exposed
4. **Secure Repr**: `repr()` and `str()` hide sensitive values

### Example Configuration

```bash
# .env file
OPENAI_API_KEY=sk-your-openai-key
MEM0_PROVIDER=openai
MODEL_NAME=gpt-4
AUTH_TOKEN=your-secure-bearer-token
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false
```

## 🚀 Running Securely

### Production Setup

1. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="sk-your-key"
   export AUTH_TOKEN="$(openssl rand -hex 32)"
   export MEM0_PROVIDER="openai"
   export MODEL_NAME="gpt-4"
   ```

2. **Run the API server**:
   ```bash
   python run_api.py
   ```

3. **Use HTTPS**: Deploy behind reverse proxy with TLS
4. **Monitor logs**: Check for authentication failures
5. **Rotate tokens**: Change AUTH_TOKEN regularly

### Development Setup

For development without authentication:

```bash
# Don't set AUTH_TOKEN for development
export OPENAI_API_KEY="sk-your-dev-key"
export MEM0_PROVIDER="openai"  
export MODEL_NAME="gpt-3.5-turbo"
export DEBUG=true

python run_api.py
```

## 🧪 Testing Security Features

Run the security test suite:

```bash
# Install test dependencies
uv add pytest pytest-asyncio

# Run security tests
python -m pytest test_security_features.py -v
```

### Test Coverage

- ✅ Bearer token authentication
- ✅ Rate limiting middleware
- ✅ Graceful degradation
- ✅ Secure configuration
- ✅ Error handling
- ✅ Endpoint security

## 📊 Monitoring & Alerts

### Key Metrics to Monitor

1. **Authentication failures**: Track 401 responses
2. **Rate limit hits**: Track 429 responses  
3. **Service unavailable**: Track 503 responses
4. **Response times**: Monitor for degradation
5. **Memory service health**: Track availability

### Log Analysis

Look for these patterns in logs:

```
# Authentication issues
WARNING: Invalid authorization token provided
WARNING: No authorization header provided

# Rate limiting
INFO: Rate limit exceeded for IP x.x.x.x

# Service degradation  
ERROR: Memory service unavailable
ERROR: Failed to initialize memory service
```

## 🔧 Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check AUTH_TOKEN is set correctly
   - Verify bearer token format
   - Ensure token matches exactly

2. **429 Rate Limited**
   - Reduce request frequency
   - Implement client-side rate limiting
   - Consider increasing limits if needed

3. **503 Service Unavailable**
   - Check Mem0 service status
   - Verify OPENAI_API_KEY is valid
   - Check network connectivity

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python run_api.py
```

This provides additional logging for troubleshooting security and reliability issues.
