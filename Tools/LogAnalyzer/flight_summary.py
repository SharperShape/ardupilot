import sys
import glob
import argparse
from DataflashLog import DataflashLog, DataflashLogHelper
from datetime import datetime, timedelta


class FileSummary():

    def __init__(self, filename, min_flight_altitude_m):
        self.logdata = DataflashLog(filename)
        self.filename = filename
        self.created = None
        self.first_takeoff = None
        self.last_landing = None
        self.flights = 0
        self.mAh_total = 0
        
        self.flight_time_total = 0

        if DataflashLogHelper.isLogEmpty(self.logdata):
            return

        self._set_created()
        self._set_flight(min_flight_altitude_m)
        self._set_mAh_total()

    @staticmethod
    def header():
        return 'filename, created, first-takeoff, last-landing, num-flights, flight-time, mAh-total'

    def summary(self):
        return '{}, {}, {}, {}, {}, {}, {}'.format(
            self.filename,
            self._format_date(self.created),
            self._format_date(self.first_takeoff),
            self._format_date(self.last_landing),
            self.flights,
            self.flight_time_total,
            self.mAh_total
        )

    def _set_created(self):
        gps_week = self.logdata.channels['GPS']['GWk'].listData[0][1]
        gps_milliseconds = self.logdata.channels['GPS']['GMS'].listData[0][1]
        self.created = self._gps_to_utc_time(gps_week, gps_milliseconds)

    def _set_flight(self, min_flight_altitude_m):
        prev_is_flying = False
        curr_is_flying = False
        can_increase_flight_count = True
        flying_dur_s = 0
        takeoff_time = None
        


        for event_id, altitude in self.logdata.channels['BARO']['Alt'].listData:
            prev_is_flying = curr_is_flying
            curr_is_flying = False if altitude < min_flight_altitude_m else True

            if not prev_is_flying and curr_is_flying:
                takeoff_time = self._get_utc_time_by_event_id(event_id)

            if not self.first_takeoff and takeoff_time is not None:
                self.first_takeoff = takeoff_time

            if can_increase_flight_count and curr_is_flying and flying_dur_s > 5:
                can_increase_flight_count = False
                self.flights += 1

            if prev_is_flying and not curr_is_flying:
                self.last_landing = self._get_utc_time_by_event_id(event_id)

            if curr_is_flying:
                flying_dur_s = (self._get_utc_time_by_event_id(
                    event_id) - takeoff_time).total_seconds()
            else:
                can_increase_flight_count = True
                self.flight_time_total += flying_dur_s
                flying_dur_s = 0

    def _get_utc_time_by_event_id(self, event_id):
        gps_week = self.logdata.channels['GPS']['GWk'].getNearestValue(event_id)[0]
        gps_milliseconds = self.logdata.channels['GPS']['GMS'].getNearestValue(event_id)[0]
        return self._gps_to_utc_time(gps_week, gps_milliseconds)

    @staticmethod
    def _format_date(date):
        if date is not None:
            return date.strftime('%Y-%m-%dT%H:%M:%S')
        return None

    @staticmethod
    def _gps_to_utc_time(gps_weeks, gps_milliseconds, leapseconds=18):
        return datetime(1980, 1, 6) + timedelta(weeks=gps_weeks, milliseconds=(gps_milliseconds + leapseconds))

    def _set_mAh_total(self):
        self.mAh_total = self.logdata.channels['CURR']['CurrTot'].max()


def main(args):
    parser = argparse.ArgumentParser(description='Flight summary')
    parser.add_argument(
        '--log-dir', help='path to Dataflash log file directory', required=False)
    parser.add_argument(
        '--log-file', help='path to Dataflash log file', required=False)
    parser.add_argument('--min-flight-altitude',
                        help='threshold of the takeoff and landing', type=int, default=5, required=False)
    args = parser.parse_args()

    #print("sdgsdgsdgsdg", args.min_flight_altitude)
    print(FileSummary.header())
    if args.log_dir:
        for log_file in glob.glob('{}/*.[bB][iI][nN]'.format(args.log_dir)):
            file_summary = FileSummary(log_file, args.min_flight_altitude)
            print(file_summary.summary())
        for log_file in glob.glob('{}/*.[lL][oO][gG]'.format(args.log_dir)):
            file_summary = FileSummary(log_file, args.min_flight_altitude)
            print(file_summary.summary())

    if args.log_file:
        file_summary = FileSummary(args.log_file, args.min_flight_altitude)
        print(file_summary.summary())


if __name__ == '__main__':
    main(sys.argv[1:])
