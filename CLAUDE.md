# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Assistant Custom Integration** (HACS-installable) that connects to Tovala Smart Ovens via their undocumented cloud API. It polls oven status, exposes sensors for remaining cook time, provides switches for custom recipes, and allows turning off the oven remotely.

**Key constraints:**
- Tovala has no public API; this integration reverse-engineers their mobile app's HTTPS endpoints
- The integration tries both `api.beta.tovala.com` and `api.tovala.com` automatically
- Authentication requires specific headers including `X-Tovala-AppID: MAPP`
- All API paths include the user_id extracted from the JWT token: `/v0/users/{user_id}/...`

## Architecture

### Component Structure

```
custom_components/tovala/
├── __init__.py        # Entry point: setup, login, coordinator initialization
├── api.py             # TovalaClient: authentication, API discovery, cooking control
├── coordinator.py     # DataUpdateCoordinator: polling, event firing
├── config_flow.py     # ConfigFlow: UI-based setup with email/password
├── sensor.py          # Time remaining & last cook sensors
├── binary_sensor.py   # Timer running binary sensor
├── switch.py          # Custom recipe switches & oven power switch
├── const.py           # Constants (domain, platforms, scan interval)
└── manifest.json      # Integration metadata
```

### Key Components

**api.py (`TovalaClient`):**
- Handles token-based authentication with automatic base URL discovery (beta → prod fallback)
- Extracts `userId` from JWT token payload for building API paths
- Rate limit detection (HTTP 429) stops login attempts immediately
- Token expiry tracking with automatic re-authentication
- **Critical:** All requests must include `X-Tovala-AppID: MAPP` header
- Known endpoints:
  - Login: `POST /v0/getToken` → returns `{"token": "jwt..."}`
  - List ovens: `GET /v0/users/{user_id}/ovens` → returns array of oven objects
  - Oven status: `GET /v0/users/{user_id}/ovens/{oven_id}/cook/status` → returns cooking state
  - Custom recipes: `GET /v0/users/{user_id}/customMealDataJSON` → returns user's custom recipes
  - Start cooking: `POST /v0/users/{user_id}/ovens/{oven_id}/cook/start` with `{"barcode": "..."}`
  - Cancel cooking: `POST /v0/users/{user_id}/ovens/{oven_id}/cook/cancel` with `{}`
  - Cooking history: `GET /v0/users/{user_id}/ovens/{oven_id}/cook/history` → returns last 10 cooks
  - Meal details: `GET /v1/users/{user_id}/meals/{meal_id}` → returns meal info and images

**coordinator.py (`TovalaCoordinator`):**
- Extends Home Assistant's `DataUpdateCoordinator`
- Polls oven status every 10 seconds (configurable via `DEFAULT_SCAN_INTERVAL`)
- Calculates remaining cook time from `estimated_end_time` field (not a direct API field)
- Detects timer completion (remaining time crossing from >0 to 0)
- Fires `tovala_timer_finished` event with `{oven_id, data}` payload
- Fetches meal details automatically when cooking starts
- Handles missing oven_id gracefully (returns empty dict)
- Adds calculated `remaining` field to coordinator data for sensors

**switch.py:**
- **Custom Recipe Switches**: One momentary switch per custom recipe from Tovala app
  - Auto-resets after 1 second
  - Starts cooking with the recipe's barcode
  - Updates coordinator after starting
- **Oven Power Switch**: Controls oven power state
  - Shows ON when oven is cooking/preheating/warming/ready
  - Turn OFF to cancel current cooking session
  - Turn ON is not supported (oven turns on automatically with recipes)
  - Displays current state, temperature, and time remaining in attributes

**__init__.py:**
- Entry setup flow: authenticate → discover ovens → fetch custom recipes → create coordinator
- Automatically discovers and stores first oven_id if not configured
- Fetches custom recipes during setup and stores in data dict
- Forwards setup to sensor, binary_sensor, and switch platforms
- Implements unload for clean removal

**config_flow.py:**
- Simple user step with email/password fields
- Error handling: `auth` (401/403), `cannot_connect` (network/other), rate limiting
- Creates config entry with credentials (oven_id added during async_setup_entry)

### Data Flow

1. User configures integration via UI → `config_flow.py` validates credentials
2. `__init__.py` creates `TovalaClient`, authenticates, discovers oven_id, fetches custom recipes
3. `TovalaCoordinator` polls `client.oven_status(oven_id)` every 10s
4. Sensors read from coordinator's cached data
5. Switches trigger `client.start_cooking()` or `client.cancel_cook()`
6. When `remaining` crosses to 0, coordinator fires `tovala_timer_finished` event

### API Structure

The Tovala API follows this pattern (discovered via Charles Proxy):
- **Base URL**: `https://api.beta.tovala.com` (primary) or `https://api.tovala.com` (fallback)
- **Authentication**: JWT token from `/v0/getToken` endpoint
- **User ID extraction**: Parse JWT payload to extract `userId` field
- **Path pattern**: All data endpoints use `/v0/users/{user_id}/...` structure (v1 for meal details)
- **Oven ID format**: UUID like `b3d64c11-96db-4ed2-9589-b52fbd0a15b1`
- **Barcode format**: Custom format like `133A254|463|5E34BF80`

## Development Commands

**Testing locally:**
```bash
# Copy integration to Home Assistant config directory
cp -r custom_components/tovala /path/to/homeassistant/config/custom_components/

# Restart Home Assistant (method varies by installation type)
# Then configure via UI: Settings → Devices & Services → Add Integration → Tovala
```

**Enable debug logging:**
Add to Home Assistant `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.tovala: debug
```

**Test authentication manually:**
```bash
curl -i -X POST "https://api.beta.tovala.com/v0/getToken" \
  -H "Content-Type: application/json" \
  -H "X-Tovala-AppID: MAPP" \
  -d '{"email":"EMAIL","password":"PASSWORD","type":"user"}'
```

**No automated tests exist** - testing requires a live Tovala account and oven.

## Code Patterns

### Error Handling
- `TovalaAuthError`: Authentication failures (401/403) - stop immediately, don't retry other bases
- `TovalaApiError`: Network errors, rate limits (429), or API failures - may retry other base URLs
- Rate limit errors (HTTP 429) are logged and raised immediately to avoid account lockout

### Logging Strategy
- `_LOGGER.debug()`: All HTTP requests/responses, login attempts, endpoint discovery
- `_LOGGER.info()`: Successful login, oven discovery, cooking actions
- `_LOGGER.warning()`: Failed endpoint attempts (expected during discovery), missing data
- `_LOGGER.error()`: Connection failures, rate limits, unexpected errors

### Home Assistant Patterns
- Use `async_get_clientsession(hass)` for HTTP - never create your own session
- Entities must define `unique_id` for persistence across restarts
- Coordinator-based entities should check `coordinator.last_update_success` for availability
- Config entries store credentials; coordinator stores runtime state
- Switches that trigger actions should call `coordinator.async_request_refresh()` after

## Common Tasks

**Adding a new sensor:**
1. Create entity class in `sensor.py` or new file
2. Extract value from `self.coordinator.data`
3. Add platform to `PLATFORMS` in `const.py` if new file
4. Add to `async_setup_entry()` entities list

**Adding a new API endpoint:**
1. Add method to `TovalaClient` in `api.py`
2. Use `_get_json()` or `_post_json()` helpers
3. Include proper error handling
4. Update coordinator if data should be cached

**Modifying API behavior:**
- Authentication: edit `TovalaClient.login()` in api.py
- JWT parsing: edit `TovalaClient._decode_jwt_user_id()` in api.py
- API endpoints: edit methods in `TovalaClient` class in api.py
- Poll interval: change `DEFAULT_SCAN_INTERVAL` in const.py
- Remaining time calculation: edit `TovalaCoordinator._async_update_data()` in coordinator.py

**Updating version:**
1. Edit `manifest.json` version field
2. Update `CHANGELOG.md` with changes
3. Commit changes
4. Tag with `git tag vX.Y.Z && git push --tags`
5. Create GitHub release
6. HACS detects new releases automatically

## API Response Expectations

**Token response** (`POST /v0/getToken`):
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600
}
```
JWT payload contains: `{"user": true, "userId": 1731601, "exp": ..., "iat": ..., "iss": "..."}`

**Ovens list response** (`GET /v0/users/{user_id}/ovens`):
```json
[{
  "id": "b3d64c11-96db-4ed2-9589-b52fbd0a15b1",
  "userid": 1731601,
  "type": "tovala",
  "model": "gen2",
  "name": "My Tovala",
  "tovala": {
    "serial": "TOVMN21130001"
  }
}]
```

**Oven status response** (`GET /v0/users/{user_id}/ovens/{oven_id}/cook/status`):

When idle:
```json
{
  "remote_control_enabled": true,
  "state": "idle"
}
```

When cooking:
```json
{
  "remote_control_enabled": true,
  "state": "cooking",
  "estimated_start_time": "2025-11-07T01:45:47Z",
  "estimated_end_time": "2025-11-07T01:53:02Z",
  "barcode": "133A254|463|5E34BF80",
  "routine": {...}
}
```

**Custom recipes response** (`GET /v0/users/{user_id}/customMealDataJSON`):
```json
{
  "userRecipes": [
    {
      "title": "Preheat 350F",
      "barcode": "CUSTOM123456"
    }
  ]
}
```

**Note**: Remaining cook time is NOT a direct field. Calculate it as:
```python
remaining_seconds = (estimated_end_time - current_time).total_seconds()
```

## Known Issues & Limitations

- No oven selection UI yet (uses first oven found)
- No configuration options for poll interval (hardcoded 10s)
- Credentials stored in plain text in config entry (Home Assistant standard)
- Oven power switch cannot turn oven on (only off) - use custom recipe switches to preheat
- Timer events rely on polling (every 10s), not real-time WebSocket updates
- Custom recipes must be created in Tovala mobile app first

## Real-time Updates (Future Enhancement)

The Tovala app uses Pusher WebSockets for real-time state changes:
- WebSocket: `wss://ws-mt1.pusher.com/app/e0ce4b79beeee326e8d8`
- Channel format: `impPub-{agentid}` (e.g., `impPub-ypaelOLxNwq9`)
- Events: `stateChanged` with payloads like `{"currentState": "ovenConnected", ...}`

This could be implemented to eliminate polling delay and provide instant updates.

## Usage Examples

**Creating preheat recipes:**
1. Open Tovala mobile app
2. Go to Custom Recipes
3. Create recipe named "Preheat 350F"
4. Set temperature to 350°F
5. Set time (e.g., 10 minutes)
6. Save - integration will fetch it automatically

**Automations:**
```yaml
# Turn off oven when timer finishes
automation:
  - alias: "Tovala Timer Finished"
    trigger:
      - platform: event
        event_type: tovala_timer_finished
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.tovala_oven_power

# Start preheat when arriving home
automation:
  - alias: "Preheat Oven on Arrival"
    trigger:
      - platform: state
        entity_id: person.me
        to: "home"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.preheat_350f
```
