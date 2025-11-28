# Tovala Smart Oven for Home Assistant

[![hacs][hacsbadge]](https://hacs.xyz)
[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[releases-shield]: https://img.shields.io/github/release/bapesupreme/ha-tovala.svg
[releases]: https://github.com/bapesupreme/ha-tovala/releases
[license-shield]: https://img.shields.io/github/license/bapesupreme/ha-tovala.svg

A **Home Assistant custom integration** that connects to Tovala Smart Ovens via their cloud API. Monitor cooking status, control custom recipes, get meal details with images, track cooking history, and receive notifications when your food is ready!

> **Note:** Tovala does not publish a public API. This integration reverse-engineers the mobile app's HTTPS endpoints.

---

## ✨ Features

- 🔥 **Real-time cooking status** - Monitor your oven's current state
- ⏱️ **Timer tracking** - See remaining cook time updated every 10 seconds
- 🍽️ **Meal details** - Get meal name, image, and ingredients for Tovala meals
- 🔘 **Custom recipe switches** - Start your custom recipes with a single tap
- 📸 **Meal images** - Display meal photos in notifications and dashboards
- 📜 **Cooking history** - View your last 10 cooking sessions
- 🔔 **Automation ready** - Fire events and use attributes in automations
- 🔍 **Automatic oven discovery** - No manual oven ID configuration needed

---

## 📦 Installation

### HACS (Recommended)

1. Open **HACS → Integrations → ⋮ → Custom repositories**
2. Add repository URL: `https://github.com/bapesupreme/ha-tovala`
3. Category: **Integration**
4. Click **Install**
5. **Restart Home Assistant**
6. Go to **Settings → Devices & Services → Add Integration**
7. Search for **Tovala Smart Oven** and sign in with your Tovala credentials

### Manual Installation

1. Copy the `custom_components/tovala/` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration from **Settings → Devices & Services**

---

## 📊 Entities

### Sensors

**`sensor.tovala_time_remaining`**
Remaining cook time in seconds.

**Attributes:**
- `cooking_state` - "idle" or "cooking"
- `barcode` - The scanned barcode
- `meal_id` - Tovala meal ID (e.g., 463)
- `meal_title` - Meal name (e.g., "2 Eggs Over Medium on Avocado Toast")
- `meal_subtitle` - Additional meal description
- `meal_image` - Full URL to meal photo
- `meal_ingredients` - List of ingredients
- `estimated_end_time` - ISO timestamp when cooking will finish

**`sensor.tovala_last_cook`**
Shows your most recent cooking session.

**Attributes:**
- `last_cook_barcode` - Barcode of last cook
- `last_cook_meal_id` - Meal ID if it was a Tovala meal
- `last_cook_start_time` - When cooking started
- `last_cook_end_time` - When cooking ended
- `last_cook_status` - "complete" or "canceled"
- `recent_history` - Array of last 10 cooking sessions

### Binary Sensors

**`binary_sensor.tovala_timer_running`**
On when the oven is actively cooking (remaining time > 0).

### Switches

**`switch.tovala_[recipe_name]`**
One switch for each custom recipe. Tap to start cooking that recipe.

- **Recipe Switches**: One switch per custom recipe (momentary)
- **Oven Power**: Turn off/cancel cooking (shows ON when oven is active) ⭐ NEW
  
### Events

**`tovala_timer_finished`**
Fired when the cooking timer reaches zero.

Payload:
```json
{
  "oven_id": "b3d64c11-96db-4ed2-9589-b52fbd0a15b1",
  "data": { "state": "idle", "meal": {...}, ... }
}
```

---

## 🤖 Automation Examples

### Send notification with meal name and image when cooking finishes

**Mobile App (iOS/Android):**
```yaml
automation:
  - alias: "Tovala Cooking Done - Mobile"
    trigger:
      - platform: state
        entity_id: binary_sensor.tovala_timer_running
        from: "on"
        to: "off"
    action:
      - service: notify.mobile_app_YOUR_DEVICE
        data:
          title: "Tovala Oven"
          message: "{{ state_attr('sensor.tovala_time_remaining', 'meal_title') or 'Your food' }} is ready!"
          data:
            image: "{{ state_attr('sensor.tovala_time_remaining', 'meal_image') }}"
```

**Telegram:**
```yaml
automation:
  - alias: "Tovala Cooking Done - Telegram"
    trigger:
      - platform: numeric_state
        entity_id: sensor.tovala_time_remaining
        below: 1
    action:
      - service: telegram_bot.send_photo
        data:
          url: "{{ state_attr('sensor.tovala_time_remaining', 'meal_image') }}"
          caption: >-
            {% set meal = state_attr('sensor.tovala_time_remaining', 'meal_title') %}
            {{ meal if meal else 'Your oven' }} is done cooking!
```

### Alert when 1 minute remaining

```yaml
automation:
  - alias: "Tovala Almost Done"
    trigger:
      - platform: numeric_state
        entity_id: sensor.tovala_time_remaining
        below: 60
    condition:
      - condition: state
        entity_id: binary_sensor.tovala_timer_running
        state: "on"
    action:
      - service: notify.notify
        data:
          message: "Your {{ state_attr('sensor.tovala_time_remaining', 'meal_title') }} has 1 minute left!"
```

### Start a recipe at a specific time

```yaml
automation:
  - alias: "Start Dinner Recipe at 6 PM"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: state
        entity_id: person.your_name
        state: "home"
    action:
      - service: switch.turn_on
        entity_id: switch.tovala_grilled_chicken
```

---

## 🎨 Dashboard Card Example

Using [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom):

```yaml
type: custom:mushroom-template-card
primary: Tovala Oven
secondary: >-
  {% if state_attr('sensor.tovala_time_remaining', 'meal_title') %}
    {{ state_attr('sensor.tovala_time_remaining', 'meal_title') }}
  {% elif states('sensor.tovala_time_remaining') | int > 0 %}
    {{ states('sensor.tovala_time_remaining') | int // 60 }}m {{ states('sensor.tovala_time_remaining') | int % 60 }}s remaining
  {% else %}
    Idle
  {% endif %}
entity: sensor.tovala_time_remaining
icon: mdi:toaster-oven
icon_color: >-
  {% if is_state('binary_sensor.tovala_timer_running', 'on') %}
    orange
  {% else %}
    grey
  {% endif %}
tap_action:
  action: more-info
```

### Recipe Control Card

```yaml
type: entities
title: Tovala Recipes
entities:
  - entity: switch.tovala_grilled_chicken
  - entity: switch.tovala_salmon_teriyaki
  - entity: switch.tovala_veggie_pizza
  - entity: switch.tovala_bacon_strips
```

---

## 🔧 Troubleshooting

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.tovala: debug
```

Then **restart Home Assistant** and check logs in **Developer Tools → Logs**.

### "cannot_connect" error

This means Home Assistant cannot reach Tovala's API:

1. **Check your internet connection**
2. **Verify credentials** - Make sure your email/password are correct
3. **Test API access**:
   ```bash
   curl -i -X POST "https://api.beta.tovala.com/v0/getToken" \
     -H "Content-Type: application/json" \
     -H "X-Tovala-AppID: MAPP" \
     -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD","type":"user"}'
   ```
   - If you get HTTP 200, credentials are valid
   - If you get HTTP 401/403, check your email/password
   - If connection fails, check firewall/DNS

### "auth" error

Your credentials are incorrect. Double-check your Tovala email and password.

### No meal details showing

Meal details only appear when:
1. You scan a **Tovala meal barcode** (not manual cooking modes)
2. The meal is in Tovala's database
3. You've reloaded the integration after updating

Manual cooking modes (like "Bake at 400°") won't have meal details.

### Recipe switches not appearing

Make sure you have custom recipes saved in your Tovala account. Create them using the Tovala mobile app first.

---

## 🛣️ Roadmap

- [ ] WebSocket support for real-time updates (currently polls every 10s)
- [ ] Multi-oven support with oven selection in UI
- [ ] Control capabilities (stop cooking remotely, adjust settings)
- [ ] Configurable poll interval
- [ ] Device triggers for "Timer Started" and "Timer Finished"
- [ ] Support for Tovala meal subscriptions and scheduling

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📜 License

MIT © 2025 Jason Lazerus

---

## ⚠️ Disclaimer

This integration is not affiliated with, endorsed by, or supported by Tovala. Use at your own risk. The integration may break if Tovala changes their API.

---

## 🙏 Credits

- Original Home Assistant integration by [@InfoSecured](https://github.com/InfoSecured)
- Homebridge plugin inspiration by [@kylewhirl](https://github.com/kylewhirl)
- Integration maintained by [@bapesupreme](https://github.com/bapesupreme)
- Thanks to the Home Assistant community for their support

---

## 📞 Support

If you encounter issues or have questions:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Search [existing issues](https://github.com/InfoSecured/ha-tovala/issues)
3. Open a [new issue](https://github.com/InfoSecured/ha-tovala/issues/new) with debug logs

**Please include debug logs when reporting issues!**
