import argparse
import subprocess


MAX_MINUTES = 0xFFFFFFFF // 60


def set_sleep_timeout(ac_minutes=None, dc_minutes=None):
    """Set the active power plan's idle sleep timeouts (0 means never)."""
    if ac_minutes is None and dc_minutes is None:
        raise ValueError("Specify an AC or DC timeout")

    for power_source, minutes in (("ac", ac_minutes), ("dc", dc_minutes)):
        if minutes is None:
            continue
        if type(minutes) is not int or not 0 <= minutes <= MAX_MINUTES:
            raise ValueError(f"Timeout must be an integer from 0 to {MAX_MINUTES} minutes")
        subprocess.run(
            ["powercfg", "/change", f"standby-timeout-{power_source}", str(minutes)],
            check=True,
        )


def minute_argument(value):
    try:
        minutes = int(value)
        if 0 <= minutes <= MAX_MINUTES:
            return minutes
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"Enter an integer from 0 to {MAX_MINUTES}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set Windows sleep timeout (0 = never)")
    parser.add_argument("--ac", type=minute_argument, help="Plugged in: minutes")
    parser.add_argument("--dc", type=minute_argument, help="On battery: minutes")
    options = parser.parse_args()
    if options.ac is None and options.dc is None:
        parser.error("Specify --ac or --dc")
    set_sleep_timeout(options.ac, options.dc)
