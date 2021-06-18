"""Several Helper Functions."""

import datetime
import time
import json
import math
from typing import OrderedDict
import logging
import yaml
from cmath import rect, phase
from math import gamma, radians, degrees

from sqlite import SQLFunctions
from const import (
    DEVICE_STATUS,
    EXTERNAL_DIRECTORY,
    UNITS_IMPERIAL,
)

_LOGGER = logging.getLogger(__name__)


class ConversionFunctions:
    """Class to help with converting from different units."""

    def __init__(self, unit_system):
        self._unit_system = unit_system

    async def temperature(self, value) -> float:
        """Convert Temperature Value."""
        if value is not None:
            if self._unit_system == UNITS_IMPERIAL:
                return round((value * 9 / 5) + 32, 1)
            return round(value, 1)

        _LOGGER.error("FUNC: temperature ERROR: Temperature value was reported as NoneType. Check the sensor")

    async def pressure(self, value) -> float:
        """Convert Pressure Value."""
        if value is not None:
            if self._unit_system == UNITS_IMPERIAL:
                return round(value * 0.02953, 3)
            return round(value, 2)

        _LOGGER.error("FUNC: pressure ERROR: Pressure value was reported as NoneType. Check the sensor")

    async def speed(self, value, kmh=False) -> float:
        """Convert Wind Speed."""
        if value is not None:
            if self._unit_system == UNITS_IMPERIAL:
                return round(value * 2.2369362920544, 2)
            if kmh:
                return round((value * 18 / 5), 1)
            return round(value, 1)

        _LOGGER.error("FUNC: speed ERROR: Wind value was reported as NoneType. Check the sensor")

    async def distance(self, value) -> float:
        """Convert distance."""
        if value is not None:
            if self._unit_system == UNITS_IMPERIAL:
                return round(value / 1.609344, 2)
            return value

        _LOGGER.error("FUNC: distance ERROR: Lightning Distance value was reported as NoneType. Check the sensor")

    async def rain(self, value) -> float:
        """Convert rain."""
        if value is not None:
            if self._unit_system == UNITS_IMPERIAL:
                return round(value * 0.0393700787, 2)
            return round(value, 2)

        _LOGGER.error("FUNC: rain ERROR: Rain value was reported as NoneType. Check the sensor")

    async def rain_type(self, value) -> str:
        """Convert rain type."""
        type_array = ["None", "Rain", "Hail", "Heavy Rain"]
        try:
            return type_array[int(value)]
        except IndexError as e:
            _LOGGER.debug("VALUE is: %s", value)
            return f"Unknown - {value}"

    async def direction(self, value) -> str:
        """Returns a directional Wind Direction string."""
        if value is None:
            return "N"
        direction_array = [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
            "N",
        ]
        direction = direction_array[int((value + 11.25) / 22.5)]
        return direction

    async def air_density(self, temperature, station_pressure):
        """Returns the Air Density."""
        if temperature is not None and station_pressure is not None:
            kelvin = temperature + 273.15
            pressure = station_pressure
            r_specific = 287.058
            decimals = 2

            air_dens = (pressure * 100) / (r_specific * kelvin)

            if self._unit_system == UNITS_IMPERIAL:
                air_dens = air_dens * 0.06243
                decimals = 4

            return round(air_dens, decimals)

        _LOGGER.error("FUNC: air_density ERROR: Temperature or Pressure value was reported as NoneType. Check the sensor")

    async def sea_level_pressure(self, station_press, elevation):
        """Returns Sea Level pressure."""
        if station_press is not None:
            elev = float(elevation)
            press = float(station_press)
            # Constants
            gravity = 9.80665
            gas_constant = 287.05
            atm_rate = 0.0065
            std_pressure = 1013.25
            std_temp = 288.15
            # Sub Calculation
            l = gravity / (gas_constant * atm_rate)
            c = gas_constant * atm_rate / gravity
            u = math.pow(1 + math.pow(std_pressure / press, c) * (atm_rate * elev / std_temp), l)
            sea_pressure = (press * u)

            return await self.pressure(sea_pressure)

        _LOGGER.error("FUNC: sea_level_pressure ERROR: Temperature or Pressure value was reported as NoneType. Check the sensor")

    async def dewpoint(self, temperature, humidity):
        """Returns Dewpoint."""
        if temperature is not None and humidity is not None:
            dewpoint_c = round(
                243.04
                * (
                    math.log(humidity / 100)
                    + ((17.625 * temperature) / (243.04 + temperature))
                )
                / (
                    17.625
                    - math.log(humidity / 100)
                    - ((17.625 * temperature) / (243.04 + temperature))
                ),
                1,
            )
            return await self.temperature(dewpoint_c)

        _LOGGER.error("FUNC: dewpoint ERROR: Temperature and/or Humidity value was reported as NoneType. Check the sensor")

    async def rain_rate(self, value):
        """Returns rain rate per hour."""
        if not value:
            return 0
        return await self.rain(value * 60)

    async def feels_like(self, temperature, humidity, windspeed):
        """Calculates the feel like temperature."""
        if temperature is None or humidity is None or windspeed is None:
            return 0

        e_value = (
            humidity * 0.06105 * math.exp((17.27 * temperature) / (237.7 + temperature))
        )
        feelslike_c = temperature + 0.348 * e_value - 0.7 * windspeed - 4.25
        return await self.temperature(feelslike_c)

    async def average_bearing(self, bearing_arr) -> int:
        """Returns the average Wind Bearing from an array of bearings."""
        mean_angle = degrees(phase(sum(rect(1, radians(d)) for d in bearing_arr)/len(bearing_arr)))
        return int(abs(mean_angle))

    async def visibility(self, elevation):
        """Returns the visibility."""
        if self._unit_system == UNITS_IMPERIAL:
            return round(1.22459 * math.sqrt(elevation * 3.2808), 1)
        return round(3.56972 * math.sqrt(elevation), 1)

    async def humanize_time(self, value):
        """Humanize Time in Seconds."""
        if value is None:
            return "None"
        return str(datetime.timedelta(seconds=value))

    async def device_status(self, value):
        """Return device status as string."""
        if value is None:
            return
            
        binvalue = str(bin(value))
        binarr = binvalue[2:]
        return_value = []
        for x in range(len(binarr)):
            if binarr[x:x+1] == "1":
                return_value.append(DEVICE_STATUS[len(binarr)-x])

        return return_value

class DataStorage:
    """Handles reading and writing of the external storage file."""

    logging.basicConfig(level=logging.DEBUG)

    async def read_config(self):
        """Reads the config file, to look for sensors."""
        try:
            filepath = f"{EXTERNAL_DIRECTORY}/config.yaml"
            with open(filepath, "r") as file:
                data = yaml.load(file, Loader=yaml.FullLoader)
                sensors = data.get("sensors")

                return sensors

        except FileNotFoundError as e:
            return None
        except Exception as e:
            _LOGGER.debug("Could not read config.yaml file. Error message: %s", e)
            return None

    def getVersion(self):
        """Returns the version number stored in the VERSION file."""
        try:
            filepath = f"{EXTERNAL_DIRECTORY}/VERSION"
            with open(filepath, "r") as file:
                lines = file.readlines()
                for line in lines:
                    if line != "\n":
                        return line.replace("\n", "")


        except FileNotFoundError as e:
            return None
        except Exception as e:
            _LOGGER.debug("Could not read config.yaml file. Error message: %s", e)
            return None

