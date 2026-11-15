# HVAC Schedule for Home Assistant

This custom integration applies an independent daily temperature schedule to a selected `climate` entity.
Choose the entity and number of periods in the Home Assistant UI when adding the integration.

Each integration instance controls one `climate` entity. Add the integration twice to control heating and hot water.

## Features

- Select a `climate` entity during setup.
- Separate config entry and virtual device for each climate entity.
- Between 1 and 12 daily periods, with 6 by default.
- Configure the period count, enabled state, start time, and temperature through **Configure**.
- The `climate` entity selected during setup is fixed and cannot be changed in the options.
- One compact, read-only row per period on the device page.
- Temperature limits and step size are taken automatically from the selected climate entity.
- Schedules work across midnight.
- The schedule is applied at the start of each minute and immediately after changes.
- Button to force the scheduled temperature to be applied.
- Avoids repeatedly writing the same temperature.
- Settings are stored in the Home Assistant config entry.

## Installation

1. Copy the following directory:

   ```text
   custom_components/heat_pump_schedule
   ```

   into Home Assistant's `/config/custom_components/` directory. The resulting manifest path should be:

   ```text
   /config/custom_components/heat_pump_schedule/manifest.json
   ```

2. Restart Home Assistant. If the integration does not appear in search immediately, hard-refresh the browser page.

3. Open **Settings → Devices & services → Add integration** and search for **HVAC Schedule**.

4. Select the climate entity and number of periods. For your configuration, the first instance typically controls
   `climate.heating`, and the second controls `climate.hot_water`.

5. Add the integration again for the second entity.

To edit an existing schedule, open it on the integration page and select **Configure**. Each period appears as a separate
row showing its start time, temperature, and state. Select a period to open its editor and change its enabled state,
start time, and temperature. The temperature slider uses the target `climate` entity's limits and step size.
The period count has its own menu item, and all changes take effect after selecting **Save changes**.
Reducing the count removes the last periods. The target `climate` entity is intentionally absent from the options;
to control another entity, add another integration instance.

## Controls

Each instance creates a virtual device named **HVAC Schedule · …** with the following entities:

- **Schedule control** — the main switch.
- **Period N · 21:00 — 31 °C** — a read-only summary showing the period's state.
- **Scheduled temperature**.
- **Active period**.
- **Schedule status**.
- **Last temperature sent via Modbus**.
- **Last temperature synchronization check**.
- **Apply now**.

You can add these entities to a dashboard using a standard **Entities** card.
For two circuits, create two cards and place them in a `horizontal-stack`.

Period start times, temperatures, and enabled states can only be edited through **Configure**
on the installed integration.
When upgrading from an older version, the separate editable period entities are automatically removed from the registry.
Then turn on **Schedule control**.

### Standard temperature mode

The **Standard temperature** sensor always displays the configured standard temperature, even when
both control switches are off. Its value updates after saving a new standard temperature in Configure.

During installation, choose a standard temperature using the selected climate entity's limits.
Change it later through **Configure → Standard temperature → Save changes**.
Both **Schedule control** and **Use standard temperature when schedule is off** are off on first installation.
Existing installations keep their previous behavior until the new switch is enabled.

When schedule control is on, daily periods take priority. When it is off and the standard temperature
switch is on, the integration immediately applies the standard temperature and maintains it at each minute
boundary, including after a restart. Turning both switches off stops automatic temperature writes and
leaves the climate's current target unchanged. Turning the schedule back on immediately restores its
current period. **Apply now** uses the standard temperature in constant mode; otherwise it applies
the current scheduled period even if automatic control is off.

The **Active period** sensor always shows the current enabled schedule period based on local time,
even when schedule control is off and standard temperature control is on. It is unknown only when
no periods are enabled. This does not change which temperature is applied to the climate entity.

The **Scheduled temperature** sensor always displays the current enabled period's temperature,
independently of both control switches. For a period using **Use standard temperature**, it displays
the current standard temperature. If no periods are enabled, it is unknown. When schedule control
is off, standard temperature control still applies the standard temperature to the climate entity;
this does not change what the Scheduled temperature sensor displays.

### Use the standard temperature in a period

In **Configure**, open a period and enable **Use standard temperature** instead of choosing a separate
target temperature. The period follows the current standard temperature automatically, including later
changes saved through **Configure → Standard temperature**. The overview shows the effective temperature
and marks it as standard. The period's own temperature is retained for use if this option is turned off.
This option works independently of the switch controlling standard temperature when the schedule is off.
Existing periods keep their own temperatures after an upgrade; this option defaults to off.

On Home Assistant Core 2026.11 and newer, the period temperature slider hides immediately when
**Use standard temperature** is enabled and reappears when it is disabled. The saved custom temperature
is retained while using the standard temperature. Older Core versions keep the slider visible for compatibility.

## Data storage

The selected `climate` entity and period count are stored in the config entry.
Start times, temperatures, and enabled states are stored in that entry's `options`, in Home Assistant's internal file
`/config/.storage/core.config_entries`. Do not edit this file manually; the data is included in regular backups.

## Tests

Unit tests in `tests/` cover active period calculation, transitions across midnight, temperature application,
value normalization, the initial config flow, and the period configuration wizard.
Use a Python version supported by your Home Assistant version:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install uv==0.9.6
.venv/bin/uv pip install -r requirements-test.txt
.venv/bin/pytest
```

`requirements-test.txt` pins the Home Assistant test harness to version `0.13.301`,
which is compatible with Python 3.13.

To generate a coverage report:

```bash
.venv/bin/pytest --cov --cov-report=term-missing
```