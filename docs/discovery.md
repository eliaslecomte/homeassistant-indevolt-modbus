# Discovery evidence and implementation

Investigated 2026-10-12. No real-device discovery capture has been collected.
The user reports HTTP, Modbus TCP and Modbus RTU enabled in Local API settings;
that does not establish which advertisements their firmware emits.

## Evidence

- [Vendor Modbus documentation](https://docs.indevolt.com/docs/hardware/open-data/modbus/)
  documents manual IP configuration, TCP port 8899 and unit 1 by default. It does
  not document a Modbus-specific mDNS, SSDP, DHCP or UDP discovery signature.
- [Current built-in HTTP manifest](https://github.com/home-assistant/core/blob/dev/homeassistant/components/indevolt/manifest.json)
  matches `igen_fw*` under `_http._tcp.local.`. Its config flow validates via the
  HTTP API. This is evidence of an Indevolt HTTP advertisement, not evidence
  that Modbus is enabled or uses the advertised HTTP port.
- [Older HTTP implementation](https://github.com/Xirt/homeassistant-indevolt/blob/8e18259e81a02508d465fe205189e1f11b752f3b/manifest.json)
  matches `smd web server*`. We do not adopt this broader legacy signature
  without confirming its relevance to Modbus-capable devices.
- [Vendor HTTP documentation](https://docs.indevolt.com/docs/hardware/open-data/http/)
  describes UDP `AT+IGDEVICEIP` to broadcast port 8099 with local port 10000,
  returning IP and SN; its FAQ says OpenData must be enabled. The prose does not
  specify a complete response grammar. We do not implement an invented parser
  or assume this independently discovers Modbus-enabled devices.
- [HA networking conventions](https://developers.home-assistant.io/docs/network_discovery/)
  provide shared Zeroconf and adapter selection for custom broadcasts.
  [Config-flow conventions](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
  provide `_async_handle_discovery_without_unique_id` for an initial, ignorable
  suggestion when a stable unique ID cannot be established.

## Behavior

The manifest registers only the current HTTP matcher. Discovery uses Home
Assistant's shared mDNS machinery and offers a form with the discovered IP,
Modbus port 8899 and unit 1. All fields remain editable. No background Modbus
probe or polling connection is created; submission performs the existing
Modbus validation using a temporary unit. Failure leaves the form available
for correction. Discovery does not infer serial numbers from names or assign
an IP-based unique ID. Existing entry/entity identity semantics remain intact.

The HA helper suppresses suggestions when an entry already exists and prevents
concurrent initial discovery flows. Further devices use manual setup. There is
no automatic IP migration, no generic network scan and no new poller. Exact
endpoint duplicates are checked again at submission, including if a manual
entry was created while the discovered form was open. Alias detection remains
unresolved. The protocol-version probe is compatibility checking, not strong
manufacturer or serial-number authentication.

## Hardware verification still needed

On the same network as Home Assistant, inspect the mDNS browser for an
`igen_fw*._http._tcp.local.` service. Record the device model, CMS/EMS firmware,
service type/name and advertised port; redact identifying names/IPs before
posting publicly. Confirm that the discovered form uses 8899 rather than the
HTTP port, that disabling Modbus causes submission to fail, and that enabling
it allows setup. Check discovery after ignoring the suggestion and after
configuring an entry. Devices without the advertisement continue to use manual
setup. A sanitized UDP response capture would be needed before implementing
that alternative.
