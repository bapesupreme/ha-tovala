# Changelog

All notable changes to the Tovala Smart Oven Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-11-28

### Added
- Oven Power switch to turn off/cancel cooking sessions
- Automatic oven state detection (on when cooking/preheating/warming/ready)

### Changed
- Switch platform now always creates a power switch
- API client includes new `cancel_cook()` method

## [2.0.0] - 2025-01-XX

### Added
- **Custom Recipe Switches**: One-tap switches for all your custom Tovala recipes
- **Enhanced Meal Details**: Full meal information including images, ingredients, and descriptions
- **Cooking History Sensor**: Track your last 10 cooking sessions
- **Event System**: `tovala_timer_finished` event fires when cooking completes
- **Auto-discovery**: Automatically finds your oven ID on first setup
- **JWT Token Support**: Proper token handling with auto-refresh
- **Multi-base URL Support**: Tries both beta and production API endpoints
- **Better Error Handling**: Graceful handling of rate limits and connection issues

### Changed
- **Complete Rewrite**: Merged best features from Homebridge plugin and original HA integration
- **Improved Coordinator**: More efficient data updates with better caching
- **Config Flow**: Enhanced setup wizard with better error messages
- **API Client**: Robust authentication and retry logic

### Fixed
- Rate limit detection and proper error messages
- Token expiration handling
- Meal image URL construction
- Oven ID extraction from multiple response formats

## [1.0.1] - 2025-XX-XX (Original Release)

### Added
- Initial release
- Basic cooking status monitoring
- Time remaining sensor
- Binary sensor for timer running
- Manual oven ID configuration

### Known Issues
- No custom recipe support
- Limited meal details
- Manual oven ID entry required

---

## Upgrade Guide

### From 1.x to 2.0

1. **Backup your configuration** (optional but recommended)
2. **Update via HACS** or manually replace files
3. **Restart Home Assistant**
4. **Reconfigure the integration**:
   - Go to Settings → Devices & Services
   - Remove the old Tovala integration
   - Add it again with your credentials
5. **Update automations**: Check if entity IDs have changed

### Breaking Changes in 2.0

- Entity naming may have changed (check your entity IDs)
- Some attributes may be in different formats
- Config flow is now required (no YAML configuration)

---

## Roadmap

### Planned for 2.1
- [ ] WebSocket support for real-time updates
- [ ] Configurable polling interval
- [ ] Device triggers for automations

### Planned for 2.2
- [ ] Multi-oven support
- [ ] Remote cooking controls (stop, pause)
- [ ] Temperature adjustment

### Planned for Future Releases
- [ ] Meal subscription integration
- [ ] Cooking presets
- [ ] Energy monitoring
- [ ] Integration with meal planning services

---

## Support

For issues, questions, or feature requests:
- [GitHub Issues](https://github.com/InfoSecured/ha-tovala/issues)
- [Home Assistant Community](https://community.home-assistant.io/)

## Credits

- Original integration by [@InfoSecured](https://github.com/InfoSecured)
- Homebridge plugin inspiration by [@kylewhirl](https://github.com/kylewhirl)
- Community contributors and testers
