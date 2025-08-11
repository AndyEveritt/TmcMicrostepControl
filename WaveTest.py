import re
from time import sleep
from duetwebapi import DuetWebAPI
from duetwebapi.api import DuetAPI
from loguru import logger


def SendGcode(duet: DuetAPI, code: str):
    while True:
        try:
            r = duet.send_code(code)
            return r
        except Exception as e:
            logger.error(f"Error sending code \"{code}\": {e}")
            sleep(1)  # Wait for 1 second before trying again


def GetRegister(duet: DuetAPI, address: int) -> int | None:
    while True:
        try:
            r = SendGcode(duet, f"m569.2 p0 r{int(address)}")
            regVals = re.findall(r'0x[\da-fA-F]{8}', r['response'])
            if regVals is None or len(regVals) == 0:
                logger.warning("No register values found")
                sleep(1)
                continue
            val = int(regVals[-1], 16)
            logger.debug(f"Register[{hex(address)}] = {hex(val)}")
            return int(regVals[-1], 16)
        except Exception as e:
            logger.error(f"{e}")
    logger.error("Could not get register")
    return None


duet = DuetWebAPI("192.168.4.87")


def GetSineTable(duet: DuetAPI, microsteps: int = 256) -> dict:
    data = []

    SendGcode(duet, "G91")
    SendGcode(duet, "M350 X256")
    SendGcode(duet, "M92 X10")
    SendGcode(duet, "G92 X0")

    for i in range(microsteps):
        logger.info(f"Microstep: {i}/{microsteps}")
        positionReg = GetRegister(duet, 0x6a)
        currentReg = GetRegister(duet, 0x6b)
        SendGcode(duet, "G1 X0.1 F6000")

        data.append(
            {
                'position': positionReg & 0x3ff,
                'coilA': (currentReg) & 0xFF if (currentReg >> 8) & 1 == 0 else ((currentReg) & 0xFF) - 0x100,
                'coilB': (currentReg >> 16) & 0xFF if (currentReg >> 24) & 1 == 0 else ((currentReg >> 16) & 0xFF) - 0x100,
            }
        )
        sleep(0.1)

    data.sort(key=lambda x: x['position'])

    SendGcode(duet, "G90")  # Return to absolute positioning mode

    # print(f"Position: {position}")
    # print(f"Current (A): {current['A']}")
    # print(f"Current (B): {current['B']}")

    return data
