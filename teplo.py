#!/usr/bin/python
#--------------------------------------
import smbus
import time
import requests
import datetime
import lnetatmo
import RPi.GPIO as GPIO  

# Define display constants
SLEEPTIME = 1 # secs to display 
REVOL = 600 # number of revolving before fetching new temperature
TEMPERFILE = "/var/www/html/netatmo.txt"

# Define some device parameters
I2C_ADDR  = 0x27 # I2C device address
LCD_WIDTH = 20   # Maximum characters per line
#LCD_WIDTH = 16   # Maximum characters per line

# Define some device constants
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command

LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

ENABLE = 0b00000100 # Enable bit

# Timing constants
E_PULSE = 0.0006
E_DELAY = 0.0006

#Open I2C interface
#bus = smbus.SMBus(0)  # Rev 1 Pi uses 0
bus = smbus.SMBus(1) # Rev 2 Pi uses 1


#nastaveni Backlight pomoci GPIO10 (19.pin)

GPIO.setmode(GPIO.BOARD)  # choose BCM or BOARD numbering schemes. I use BCM

GPIO.setup(19, GPIO.IN)# set GPIO 19 as input

# Nastaveni nadmorske vysky: Meters above the sea
mnm = 330 



def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = the data
  # mode = 1 for data
  #        0 for command

  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  # High bits
  bus.write_byte(I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  # Low bits
  bus.write_byte(I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  # Toggle enable
  time.sleep(E_DELAY)
  bus.write_byte(I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  # Send string to display
  message = message.ljust(LCD_WIDTH," ")
  lcd_byte(line, LCD_CMD)
  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)

def main():
  # Main program block
  # Initialise display
  lcd_init()

  napis = "Opakovani n="

  while True:
    #           12345678901234567890
    lcd_string("Getting tempture1...",LCD_LINE_1)
    lcd_string("From NetAtmo and ",LCD_LINE_2)
    lcd_string("From DS18B20 sensor",LCD_LINE_3)
    lcd_string("Dvorek,puda,pudicka",LCD_LINE_4)
    #req = "Teplota 00 :-("
    datumcas = datetime.datetime.now().strftime("Cas: %Y-%m-%d %H:%M:%S")
    dvorek = "000"
    puda   = "000"

    try:	
      reqt = requests.get('http://www.t1.cz/puda.temp',timeout=10)
      esp8266 = reqt.text.rstrip()
      tlak = esp8266.split(' ')
      akt = float(tlak[0][:-2])
      atm = float(tlak[1][:-3])
      # Math Expression to count pressure to the sea level:
      # ( pressure * 9.80665 * meters_above_sea ) / (273 + actual_temperature + (meters_above_sea/400)) + pressure
      vypocet = (atm * 9.80665 * mnm)/(287 * (273 + akt + (mnm/400))) + atm
      tlak_hladina = int(round(vypocet))
      esp_line = "ESP: "+str(akt)+"C, "+str(tlak_hladina)+"hPa"
    except requests.exceptions.RequestException as reqt:
      print datumcas
      print reqt
      esp8266 = "ESP nejede"

    try:
      # 1 : Authenticate NetAtmo
      authorization = lnetatmo.ClientAuth()
      # 2 : Get devices list
      devList = lnetatmo.DeviceList(authorization)
    except IOError:
      print "IOError"

    dvorek = devList.lastData("Plzenska")['dvorek']['Temperature']
    puda = devList.lastData("Plzenska")['puda']['Temperature']
    netatmo = str(dvorek)+", "+str(puda)
    datum = datetime.datetime.now().strftime("Date: %Y-%m-%d")
    fo = open(TEMPERFILE, "w")
    fo.write( netatmo );
    fo.close()
    for i in range (REVOL):
      if (GPIO.input(19)):
	LCD_BACKLIGHT  = 0x08  # On
      else:
	LCD_BACKLIGHT = 0x00  # Off

      #print("LCD Backlight")
      #print(LCD_BACKLIGHT)
      #lcd_byte(0x0C, LCD_CMD)

      cas = datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")
      lcd_string("Venku: "+str(dvorek)+"C..W"+str(i),LCD_LINE_1)
      lcd_string(" Puda: "+str(puda)+"C",LCD_LINE_2)
      lcd_string(esp_line,LCD_LINE_3)
      lcd_string(cas,LCD_LINE_4)

      time.sleep(SLEEPTIME)

#End of while


if __name__ == '__main__':

  try:
    main()
  except KeyboardInterrupt:
    pass
  finally:
    lcd_byte(0x01, LCD_CMD)
