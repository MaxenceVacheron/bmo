# BMO Project

## Power Saving (Raspberry Pi)

To minimize power consumption, the following underclocking and undervolting settings have been applied to `/boot/firmware/config.txt` on the Raspberry Pi:

```ini
# BMO Power Saving
arm_freq=600
over_voltage_min=-2
```

### How to Revert
If BMO becomes unstable or too slow, you can revert these changes by:
1. Connecting via SSH to the Pi.
2. Editing the config file: `sudo nano /boot/firmware/config.txt`.
3. Removing the lines under `# BMO Power Saving`.
4. Rebooting the Pi: `sudo reboot`.