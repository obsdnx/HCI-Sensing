# MODE: 'serial' | 'wifi' | 'ble' | 'sd'
MODE = 'serial'

# I2C
I2C_BUS   = 0
SDA_PIN   = 21
SCL_PIN   = 22

# Sample rate
SAMPLE_RATE_HZ = 100

# WiFi (MODE='wifi')
WIFI_SSID     = 'your_ssid'
WIFI_PASSWORD = 'your_password'
HOST_IP       = '192.168.1.100'   # your computer's IP
UDP_PORT      = 5005

# SD card SPI pins (MODE='sd')
SD_SCK  = 18
SD_MOSI = 23
SD_MISO = 19
SD_CS   = 5
