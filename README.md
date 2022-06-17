HID descriptor parser
=====================

Parses HID report descriptors and prints their contents in a human-readable format.

Sample output:

```
Application 0d:04 = Digitizers: Touch Screen
  Feature 0x0a
    u8[256] ff00:c5 = Vendor: Microsoft Device Certification Status
  Feature 0x0c
    u8 0d:55 = Digitizers: Contact Max
  Input 0x0c
    u8 padding
    u8 0d:54 = Digitizers: Contact Count
    Logical 0d:22 = Digitizers: Finger
      u1 0d:42 = Digitizers: Tip Switch
      u1 padding
      u1 0d:47 = Digitizers: Confidence
      u1[5] padding
      u16 0d:51 = Digitizers: Contact Id         # 0 to 255
      u16 01:30 = Generic Desktop: X             # 0 to 8676 = 0 to 21.69 cm
      u16 01:31 = Generic Desktop: Y             # 0 to 5424 = 0 to 13.56 cm
    Logical 0d:22 = Digitizers: Finger
      u1 0d:42 = Digitizers: Tip Switch
      u1 padding
      u1 0d:47 = Digitizers: Confidence
      u1[5] padding
      u16 0d:51 = Digitizers: Contact Id         # 0 to 255
      u16 01:30 = Generic Desktop: X             # 0 to 8676 = 0 to 21.69 cm
      u16 01:31 = Generic Desktop: Y             # 0 to 5424 = 0 to 13.56 cm
    u16 0d:56 = Digitizers: Scan Time
```

License: Public domain/CC0
