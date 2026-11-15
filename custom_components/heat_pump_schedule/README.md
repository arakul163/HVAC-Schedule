# HVAC Schedule

Installation instructions and full documentation are in the project's root
`README.md`.

Copy this entire directory to:

```text
/config/custom_components/heat_pump_schedule
```

After restarting Home Assistant, add the integration through the UI and select
the target `climate` entity.

## Standard temperature mode

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

### Use the standard temperature in a period

In **Configure**, open a period and enable **Use standard temperature** instead of choosing a separate
target temperature. The period follows the current standard temperature automatically, including later
changes saved through **Configure → Standard temperature**. The overview shows the effective temperature
and marks it as standard. The period's own temperature is retained for use if this option is turned off.
This option works independently of the switch controlling standard temperature when the schedule is off.
Existing periods keep their own temperatures after an upgrade; this option defaults to off.

The **Active period** sensor always shows the current enabled schedule period based on local time,
even when schedule control is off and standard temperature control is on. It is unknown only when
no periods are enabled. This does not change which temperature is applied to the climate entity.

The **Scheduled temperature** sensor always displays the current enabled period's temperature,
independently of both control switches. For a period using **Use standard temperature**, it displays
the current standard temperature. If no periods are enabled, it is unknown. When schedule control
is off, standard temperature control still applies the standard temperature to the climate entity;
this does not change what the Scheduled temperature sensor displays.

On Home Assistant Core 2026.11 and newer, the period temperature slider hides immediately when
**Use standard temperature** is enabled and reappears when it is disabled. The saved custom temperature
is retained while using the standard temperature. Older Core versions keep the slider visible for compatibility.
