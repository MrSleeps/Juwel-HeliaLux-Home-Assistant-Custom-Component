from datetime import timedelta
import re
DOMAIN = "juwel_helialux"
ENTITY_ID_FORMAT = DOMAIN + '.{}'
DEFAULT_NAME = 'Fish Tank'
DEFAULT_DATE_FORMAT = "%y-%m-%dT%H:%M:%S"
DEFAULT_HOST = "192.168.1.1"
ATTR_MEASUREMENT_DATE = 'date'
ATTR_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)
STATUS_VARS_REGEX = re.compile(r"(?P<name>[a-zA-Z0-9]+)=((?P<number>\d+)|'(?P<string>[^']+)'|\[(?P<digit_list>(\d+,?)+)\]|\[(?P<string_list>(\"([^\"]+)\",?)+)\]);")