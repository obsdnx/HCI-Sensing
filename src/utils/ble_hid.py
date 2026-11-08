"""
BLE HID keyboard. Runs on ESP32 MicroPython.
Pairs with your computer as a Bluetooth keyboard.
Call send({'key': 'A'}) to type a character.
"""
import bluetooth
import struct
import time

_ADV_TYPE_FLAGS              = 0x01
_ADV_TYPE_NAME               = 0x09
_ADV_TYPE_APPEARANCE         = 0x19
_ADV_TYPE_UUID16_COMPLETE    = 0x03

_APPEARANCE_HID_KEYBOARD     = 0x03C1
_HID_SERVICE_UUID            = bluetooth.UUID(0x1812)
_HID_REPORT_UUID             = bluetooth.UUID(0x2A4D)
_HID_REPORT_MAP_UUID         = bluetooth.UUID(0x2A4B)
_HID_INFO_UUID               = bluetooth.UUID(0x2A4A)
_HID_CTRL_POINT_UUID         = bluetooth.UUID(0x2A4C)
_REPORT_REF_UUID             = bluetooth.UUID(0x2908)
_CLIENT_CHAR_CONFIG_UUID     = bluetooth.UUID(0x2902)

_REPORT_DESC = bytes([
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01,
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7,
    0x15, 0x00, 0x25, 0x01, 0x75, 0x01,
    0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
    0x75, 0x08, 0x81, 0x01, 0x95, 0x06,
    0x75, 0x08, 0x15, 0x00, 0x25, 0x65,
    0x05, 0x07, 0x19, 0x00, 0x29, 0x65,
    0x81, 0x00, 0xC0,
])

# ASCII → HID keycode (a-z, A-Z, 0-9, space)
_CHAR_TO_HID = {c: i + 4 for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
_CHAR_TO_HID.update({c: i + 4 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
_CHAR_TO_HID[" "] = 0x2C
_MODIFIER = {c: 0x02 for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}


class BleHID:
    def __init__(self, name="ESP32-IMU-KB"):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._conn = None

        hid_service = (
            _HID_SERVICE_UUID,
            (
                (_HID_REPORT_MAP_UUID, bluetooth.FLAG_READ),
                (_HID_INFO_UUID,       bluetooth.FLAG_READ),
                (_HID_CTRL_POINT_UUID, bluetooth.FLAG_WRITE_NO_RESPONSE),
                (_HID_REPORT_UUID,     bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
                    ((_CLIENT_CHAR_CONFIG_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_WRITE),
                     (_REPORT_REF_UUID, bluetooth.FLAG_READ),)),
            ),
        )

        ((self._report_map, self._hid_info, self._ctrl, self._report, _, _),) = \
            self._ble.gatts_register_services((hid_service,))

        self._ble.gatts_write(self._report_map, _REPORT_DESC)
        self._ble.gatts_write(self._hid_info, struct.pack("<HBB", 0x0111, 0x00, 0x02))

        self._advertise(name)
        print("BLE HID advertising — pair with your computer")

    def _irq(self, event, data):
        _IRQ_CENTRAL_CONNECT    = 1
        _IRQ_CENTRAL_DISCONNECT = 2
        if event == _IRQ_CENTRAL_CONNECT:
            self._conn, _, _ = data
            print("BLE connected")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._conn = None
            self._advertise()

    def _advertise(self, name="ESP32-IMU-KB"):
        payload = (
            bytes([2, _ADV_TYPE_FLAGS, 0x06]) +
            bytes([3, _ADV_TYPE_UUID16_COMPLETE, 0x12, 0x18]) +
            bytes([3, _ADV_TYPE_APPEARANCE,
                   _APPEARANCE_HID_KEYBOARD & 0xFF,
                   (_APPEARANCE_HID_KEYBOARD >> 8) & 0xFF]) +
            bytes([len(name) + 1, _ADV_TYPE_NAME]) + name.encode()
        )
        self._ble.gap_advertise(100_000, adv_data=payload)

    def send(self, sample):
        """Expects sample={'key': 'A'} or sample={'text': 'hello'}."""
        if self._conn is None:
            return
        text = sample.get("text") or sample.get("key", "")
        for ch in text:
            keycode  = _CHAR_TO_HID.get(ch, 0)
            modifier = _MODIFIER.get(ch, 0)
            report = struct.pack("8B", modifier, 0, keycode, 0, 0, 0, 0, 0)
            self._ble.gatts_notify(self._conn, self._report, report)
            time.sleep_ms(20)
            # key up
            self._ble.gatts_notify(self._conn, self._report, bytes(8))
            time.sleep_ms(20)
