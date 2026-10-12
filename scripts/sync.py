"""Synchronize the core integration and vendor the standalone library."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT.parent / "home-assistant-core/homeassistant/components/indevolt"
LIBRARY = ROOT.parent / "indevolt-modbus"
TARGET = ROOT / "custom_components/indevolt_modbus"


def main() -> None:
    """Copy owned files; leave custom transport.py and repository metadata intact."""
    for source in CORE.iterdir():
        if source.suffix not in {".py", ".json"}:
            continue
        content = source.read_text().replace(
            "from indevolt_modbus", "from .vendor.indevolt_modbus"
        )
        if source.name in {"__init__.py", "config_flow.py"}:
            content = content.replace(
                "from homeassistant.components.modbus import", "from .transport import"
            )
        if source.name == "__init__.py":
            content = content.replace(
                "unit = async_get_unit(", "unit = await async_get_unit("
            )
            start = content.index(
                "    await coordinator.async_config_entry_first_refresh()"
            )
            end = content.index("    return True", start)
            setup = content[start:end]
            guarded = "    try:\n" + "".join(
                "    " + line if line.strip() else line
                for line in setup.splitlines(keepends=True)
            )
            guarded += (
                "    except BaseException:\n"
                "        await async_release_unit(hass, entry)\n"
                "        raise\n"
            )
            content = content[:start] + guarded + content[end:]
            content = content.replace(
                "return await hass.config_entries.async_unload_platforms"
                "(entry, PLATFORMS)",
                "if not await hass.config_entries.async_unload_platforms"
                "(entry, PLATFORMS):\n"
                "        return False\n    await async_release_unit(hass, entry)\n"
                "    return True",
            )
            content = content.replace(
                "from .transport import async_get_unit",
                "from .transport import async_get_unit, async_release_unit",
            )
        if source.name == "const.py":
            content = content.replace(
                'DOMAIN = "indevolt"', 'DOMAIN = "indevolt_modbus"'
            )
        if source.name == "manifest.json":
            data = json.loads(content)
            previous = (
                json.loads((TARGET / source.name).read_text())
                if (TARGET / source.name).exists()
                else {}
            )
            data.update(
                domain="indevolt_modbus",
                name="Indevolt Modbus",
                version="0.1.0",
                requirements=["modbus-connection[tmodbus]>=4.12.4"],
                documentation="https://docs.indevolt.com/docs/hardware/open-data/modbus/",
                loggers=["modbus_connection", "tmodbus"],
            )
            for key in ("codeowners", "documentation", "issue_tracker"):
                if previous.get(key):
                    data[key] = previous[key]
            data = {
                key: data[key]
                for key in ["domain", "name", *sorted(set(data) - {"domain", "name"})]
            }
            content = json.dumps(data, indent=2) + "\n"
        (TARGET / source.name).write_text(content)
    translations = TARGET / "translations"
    translations.mkdir(exist_ok=True)
    shutil.copyfile(TARGET / "strings.json", translations / "en.json")
    vendor = TARGET / "vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / "__init__.py").write_text('"""Vendored standalone device library."""\n')
    shutil.copytree(
        LIBRARY / "src/indevolt_modbus",
        vendor / "indevolt_modbus",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copyfile(LIBRARY / "LICENSE", vendor / "LICENSE")


if __name__ == "__main__":
    main()
