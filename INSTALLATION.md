# Installation Guide

## Quick Start

1. **Install via HACS** (recommended) or manually
2. **Restart Home Assistant**
3. **Add the integration** via Settings → Devices & Services
4. **Enter your Tovala credentials**
5. **Start automating!**

---

## Method 1: HACS Installation (Recommended)

### Step 1: Add Custom Repository

1. Open **HACS** in your Home Assistant sidebar
2. Click the **three dots** (⋮) in the top right
3. Select **Custom repositories**
4. Add the following details:
   - **Repository**: `https://github.com/InfoSecured/ha-tovala`
   - **Category**: `Integration`
5. Click **Add**

### Step 2: Install the Integration

1. In HACS, click **Explore & Download Repositories**
2. Search for **"Tovala Smart Oven"**
3. Click on the integration
4. Click **Download**
5. Select the latest version
6. Click **Download** again

### Step 3: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Click **Restart**
3. Wait for Home Assistant to come back online

### Step 4: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Tovala Smart Oven"**
4. Click on it
5. Enter your Tovala email and password
6. Click **Submit**

---

## Method 2: Manual Installation

### Step 1: Download the Integration

1. Download the latest release from [GitHub Releases](https://github.com/InfoSecured/ha-tovala/releases)
2. Extract the ZIP file

### Step 2: Copy Files

Copy the `custom_components/tovala` folder to your Home Assistant configuration directory:

```
config/
└── custom_components/
    └── tovala/
        ├── __init__.py
        ├── api.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── hacs.json
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        └── switch.py
```

### Step 3: Restart and Configure

Follow **Steps 3-4** from the HACS installation method above.

---

## What Gets Created?

After successful setup, you'll have:

### Sensors
- **`sensor.tovala_time_remaining`** - Shows remaining cooking time
- **`sensor.tovala_last_cook`** - Shows your most recent cook

### Binary Sensors
- **`binary_sensor.tovala_timer_running`** - ON when cooking is active

### Switches
- **`switch.tovala_[recipe_name]`** - One switch for each custom recipe

### Events
- **`tovala_timer_finished`** - Fires when cooking completes

---

## Troubleshooting Installation

### Integration Not Found After HACS Install

1. Make sure you **restarted Home Assistant** after installation
2. Clear your browser cache (Ctrl+F5 or Cmd+Shift+R)
3. Check HACS logs for any download errors

### Invalid Auth Error

- Double-check your Tovala email and password
- Make sure you can log in to the Tovala mobile app with the same credentials
- Check for any spaces before/after your email or password

### Cannot Connect Error

1. Check your internet connection
2. Verify Home Assistant can reach external URLs
3. Check firewall settings
4. Try manually testing the API:
   ```bash
   curl -i -X POST "https://api.beta.tovala.com/v0/getToken" \
     -H "Content-Type: application/json" \
     -H "X-Tovala-AppID: MAPP" \
     -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD","type":"user"}'
   ```

### Rate Limit Error

If you see a rate limit error:
- Wait 30-60 minutes before trying again
- Avoid multiple login attempts in quick succession
- Check if you have other integrations trying to access Tovala API

### No Entities Appear

1. Check **Settings** → **Devices & Services** → **Tovala Smart Oven**
2. Click on the integration
3. Verify your oven was discovered (check for an oven ID)
4. Check logs in **Settings** → **System** → **Logs** for errors

### Custom Recipes Not Showing

1. Make sure you have custom recipes saved in your Tovala mobile app
2. Reload the integration: **Settings** → **Devices & Services** → **Tovala** → **⋮** → **Reload**
3. Check logs for recipe fetch errors

---

## Enabling Debug Logging

If you need to troubleshoot issues, enable debug logging:

1. Edit your `configuration.yaml` file:
   ```yaml
   logger:
     default: warning
     logs:
       custom_components.tovala: debug
   ```

2. Restart Home Assistant

3. Check logs in **Settings** → **System** → **Logs**

4. Look for lines starting with `custom_components.tovala`

---

## Uninstalling

### Via HACS

1. Open **HACS** → **Integrations**
2. Find **Tovala Smart Oven**
3. Click the **three dots** (⋮)
4. Select **Remove**
5. Go to **Settings** → **Devices & Services**
6. Find **Tovala Smart Oven**
7. Click the **three dots** (⋮)
8. Select **Delete**
9. Restart Home Assistant

### Manual Uninstall

1. Delete the `custom_components/tovala/` folder
2. Remove the integration from **Settings** → **Devices & Services**
3. Restart Home Assistant

---

## Next Steps

Once installed, check out:
- [README.md](README.md) - Full documentation and features
- [Automation Examples](README.md#-automation-examples) - Ready-to-use automations
- [Dashboard Cards](README.md#-dashboard-card-example) - Beautiful UI examples

---

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting-installation) section above
2. Search [existing issues](https://github.com/InfoSecured/ha-tovala/issues)
3. Open a [new issue](https://github.com/InfoSecured/ha-tovala/issues/new) with:
   - Your Home Assistant version
   - Integration version
   - Debug logs (see above for how to enable)
   - Steps to reproduce the problem
