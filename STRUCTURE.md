# Project Structure

This document shows the complete file structure for the Tovala Smart Oven Home Assistant integration.

```
ha-tovala/
├── .github/
│   └── workflows/
│       └── validate.yml          # GitHub Actions validation workflow
│
├── custom_components/
│   └── tovala/
│       ├── __init__.py            # Integration entry point and setup
│       ├── api.py                 # Tovala API client
│       ├── binary_sensor.py       # Timer running binary sensor
│       ├── config_flow.py         # Configuration UI flow
│       ├── const.py               # Constants and configuration
│       ├── coordinator.py         # Data update coordinator
│       ├── hacs.json              # HACS metadata
│       ├── manifest.json          # Integration manifest
│       ├── sensor.py              # Time remaining & last cook sensors
│       ├── strings.json           # UI strings
│       ├── switch.py              # Custom recipe switches
│       └── translations/
│           └── en.json            # English translations
│
├── .gitignore                     # Git ignore rules
├── CHANGELOG.md                   # Version history
├── INSTALLATION.md                # Installation guide
├── LICENSE                        # MIT License
└── README.md                      # Main documentation
```

---

## File Descriptions

### Core Integration Files

**`custom_components/tovala/__init__.py`**
- Integration entry point
- Sets up platforms (sensor, binary_sensor, switch)
- Handles authentication
- Discovers oven automatically
- Fetches custom recipes
- Creates coordinator

**`custom_components/tovala/api.py`**
- Complete API client for Tovala cloud
- JWT token handling and auto-refresh
- Multi-base URL support (beta/prod fallback)
- All API endpoints (auth, ovens, status, recipes, cooking)
- Error handling and rate limit detection

**`custom_components/tovala/coordinator.py`**
- DataUpdateCoordinator for efficient polling
- Polls oven status every 10 seconds
- Calculates remaining cooking time
- Fetches meal details automatically
- Fires timer_finished events
- Caches meal information

**`custom_components/tovala/config_flow.py`**
- User-friendly configuration UI
- Credential validation
- Error handling with user-friendly messages
- Prevents duplicate accounts

### Platform Files

**`custom_components/tovala/sensor.py`**
- **Time Remaining Sensor**: Shows seconds remaining
  - Attributes: cooking_state, barcode, meal details, images
- **Last Cook Sensor**: Shows most recent cooking session
  - Attributes: Full cooking history (last 10 sessions)

**`custom_components/tovala/binary_sensor.py`**
- **Timer Running**: ON when actively cooking
- Used for automations and status monitoring

**`custom_components/tovala/switch.py`**
- One switch per custom recipe
- Momentary behavior (auto-resets after 1 second)
- Starts cooking when turned on
- Updates coordinator after starting

### Configuration Files

**`custom_components/tovala/const.py`**
- Domain name
- Configuration keys
- Default scan interval
- Event names
- API constants

**`custom_components/tovala/manifest.json`**
- Integration metadata
- Version number
- Requirements
- Documentation links

**`custom_components/tovala/strings.json`**
- UI text for config flow
- Error messages
- Step descriptions

**`custom_components/tovala/hacs.json`**
- HACS-specific metadata
- Render readme flag
- Country availability

**`custom_components/tovala/translations/en.json`**
- English translations
- Entity names
- Config flow text

### Documentation Files

**`README.md`**
- Main documentation
- Feature list
- Installation instructions
- Automation examples
- Dashboard card examples
- Troubleshooting guide

**`INSTALLATION.md`**
- Detailed installation guide
- HACS vs manual installation
- Troubleshooting steps
- Debug logging instructions

**`CHANGELOG.md`**
- Version history
- Breaking changes
- Upgrade guide
- Roadmap

**`LICENSE`**
- MIT License
- Copyright information

### GitHub Files

**`.github/workflows/validate.yml`**
- HACS validation
- Hassfest validation
- Automated testing

**`.gitignore`**
- Excludes Python cache
- Excludes IDE files
- Excludes test artifacts

---

## Key Design Decisions

### Why Coordinator Pattern?
- Efficient API polling (single request for all entities)
- Automatic state updates across all entities
- Built-in error handling and retry logic
- Home Assistant best practice

### Why Config Flow?
- User-friendly setup wizard
- No manual YAML editing
- Built-in validation
- Easy to reconfigure

### Why Separate Platform Files?
- Clear separation of concerns
- Easy to maintain and extend
- Standard Home Assistant structure
- Can disable platforms individually

### Why Multiple Sensors?
- Time Remaining: For automations and timers
- Last Cook: For history tracking
- Timer Running: For state-based automations
- Each serves a specific purpose

---

## Development Workflow

1. **Make changes** to Python files
2. **Run validation**: `hass --script check_config -c config`
3. **Test locally** in Home Assistant
4. **Enable debug logging** to verify behavior
5. **Submit PR** with tests and documentation

---

## Adding New Features

### Adding a New Sensor
1. Create entity class in `sensor.py`
2. Extract data from `coordinator.data`
3. Add to `async_setup_entry()`
4. Update documentation

### Adding a New API Endpoint
1. Add method to `TovalaClient` in `api.py`
2. Use `_get_json()` or `_post_json()` helpers
3. Add error handling
4. Update coordinator if needed

### Adding Configuration Options
1. Add constant to `const.py`
2. Update config flow in `config_flow.py`
3. Use in coordinator or platform setup
4. Update `strings.json`

---

## Testing Checklist

- [ ] Authentication with valid credentials
- [ ] Authentication with invalid credentials
- [ ] Oven discovery
- [ ] Recipe fetching
- [ ] Sensor state updates
- [ ] Switch triggering
- [ ] Event firing
- [ ] Rate limit handling
- [ ] Network error handling
- [ ] Reload integration
- [ ] Remove integration

---

## Release Checklist

- [ ] Update version in `manifest.json`
- [ ] Update `CHANGELOG.md`
- [ ] Test installation via HACS
- [ ] Test manual installation
- [ ] Verify all entities appear
- [ ] Test automations
- [ ] Update documentation
- [ ] Create GitHub release
- [ ] Tag version
