"""
This is the main file to be run for the Server Gateway
"""
import logging
import sys
import platform
RPI = False
if platform.system() == "Linux":
    if platform.release().find('raspi'):
        print("THIS IS A RASPBIAN SYSTEM\n")
        RPI = True
        ### DEFINE GPIO PINS ###
        import RPi.GPIO as GPIO     # GPIO
        import adafruit_rfm9x       # LoRa
        GPIO.setmode(GPIO.board)
        ## GPIO.setup
        ## GPIO.output
        

# import threading

def main():
    """
    Main function - will be run if this file is specified in terminal
    """
    try:
        # Configuring startup settings
        FMT = "%(asctime)s | main\t\t: %(message)s"
        logging.basicConfig(format=FMT, level=logging.INFO,
                            datefmt="%Y-%m-%D %H:%M:%S")
        logging.info("Starting up device...")

        while True:
            packet = None
            if RPI:
                packet = rfm9x.receive()        # Check for packet rx
            if packet is None:
                logging.info('Waiting for PKT...')
            else:
                logging.info("Packet received!")
    except ValueError as val_err:
        return str(val_err)

if __name__ == "__main__":
    sys.exit(main())
