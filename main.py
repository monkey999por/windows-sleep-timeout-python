"""Command-line interface for the sleep timeout library."""

import argparse

from sleep_settings import MAX_MINUTES, SleepTimeoutManager


def minute_argument(value: str) -> int:
    try:
        minutes = int(value)
        if 0 <= minutes <= MAX_MINUTES:
            return minutes
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"Enter an integer from 0 to {MAX_MINUTES}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set Windows sleep timeout (0 = never)")
    parser.add_argument("--ac", type=minute_argument, help="Plugged in: minutes")
    parser.add_argument("--dc", type=minute_argument, help="On battery: minutes")
    parser.add_argument("--show", action="store_true", help="Show the active plan's timeouts")
    parser.add_argument("--restore", action="store_true", help="Restore the saved timeouts")
    options = parser.parse_args()
    if sum((options.ac is not None or options.dc is not None, options.show, options.restore)) != 1:
        parser.error("Specify --ac/--dc, --show, or --restore")
    manager = SleepTimeoutManager()
    if options.show:
        snapshot = manager.read()
        print(f"Plan: {snapshot.scheme_guid}\nAC: {snapshot.ac_seconds} seconds\nDC: {snapshot.dc_seconds} seconds")
    elif options.restore:
        manager.restore()
    else:
        manager.set(options.ac, options.dc)


if __name__ == "__main__":
    main()
