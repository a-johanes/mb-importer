
import datetime
from enum import Enum
from dataclasses import dataclass
import re
from typing import List, Tuple
import PyPDF2

from dto import *
from finance_manager import *


class TransportType(Enum):
    MRT = 0
    BUS = 1
    MIXED = 2


@dataclass
class Transaction:
    time: datetime.time
    from_destination: str
    to_destination: str
    fare: float
    transport: 'TransportType'


@dataclass
class Trip:
    date: datetime.date
    from_destination: str
    to_destination: str
    fare: float
    transactions: List['Transaction']

    def __str__(self) -> str:
        transaction_str = [str(transaction)
                           for transaction in self.transactions]
        transaction_lines = '\n\t'.join(transaction_str)

        return f'Trip(date={self.date}, from={self.from_destination}, to={self.to_destination}, fare={self.fare}, transport={self.get_transport_type()}, transactions=\n\t{transaction_lines})'

    def get_transport_type(self) -> 'TransportType':
        transportTypes = {
            transaction.transport for transaction in self.transactions}

        match len(transportTypes):
            case 0:
                return None
            case 1:
                return transportTypes.pop()
            case _:
                return TransportType.MIXED

    def to_request(self, asset_groups: List[AssetGroup], categories: Dict[InOutCode, List[Category]]) -> CreateInOutTransactionRequest:
        in_out_code = InOutCode.Expenses
        asset_group = next(
            (group for group in asset_groups if group.id == '1'), None)
        if asset_group is None:
            return
        # print(asset_group)
        asset = next((asset for asset in asset_group.children if asset.id ==
                     '05c64c05-8fa5-4b8d-a33c-0ab1a662fc65'), None)
        if asset is None:
            return
        # print(asset)
        expense_categories = categories[in_out_code]
        category = next(
            (cat for cat in expense_categories if cat.id == '9'), None)
        if category is None:
            return
        # print(category)
        last_transaction = self.transactions[-1]

        time = datetime.datetime.combine(self.date, last_transaction.time)

        sub_category = None
        match self.get_transport_type():
            case TransportType.MRT:
                sub_category = next((cat for cat in category.sub_category if cat.id ==
                                    '0fcb0e69-1b4e-4362-8d08-17d741deef39'), None)
            case TransportType.BUS:
                sub_category = next(
                    (cat for cat in category.sub_category if cat.id == '26'), None)
            case TransportType.MIXED:
                sub_category = next((cat for cat in category.sub_category if cat.id ==
                                    '8b3d8e7f-7845-40fe-844f-11855077ded6'), None)

        request = CreateInOutTransactionRequest(
            in_out_code,
            asset,
            category,
            time,
            self.fare,
            f'{self.from_destination} - {self.to_destination}',
            sub_category=sub_category,
        )

        return request


class SimplyGo:

    @staticmethod
    def parse_pdf(path: str) -> List['Trip']:
        pdf_text = SimplyGo.extract_pdf(path)
        # print(*pdf_text,sep='\n')
        return SimplyGo.parse_trip_data(pdf_text)

    def extract_pdf(path: str) -> List[str]:
        with open(path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)

            result = []

            for page in pdf_reader.pages:
                text_list = page.extract_text(space_width=1.0).splitlines()
                # print(text_list)
                text_list = [line for line in text_list if line != " "]

                result += text_list

            return result

    trip_start_regex = re.compile(
        "^(\\w{3}, \\d{2}/\\d{2}/\\d{4})(\s?)(.*) - (((.*) \\$(\\d+\\.\\d+))|(.*))$")
    fare_regex = re.compile("^(.*)\\$([0-9.]+)$")
    tansaction_start_regex = re.compile(
        "^(\\d{2}:\\d{2} [AP][M])(.*) - ((.*) (\\$([0-9.]+))|(.*))$")

    date_format_pattern = "%a, %d/%m/%Y"
    time_format_pattern = "%I:%M %p"

    @staticmethod
    def parse_trip_data(data: List[str]) -> List['Trip']:
        trips = []
        curr_trip: Trip = None
        need_trip_detail: bool = False
        curr_transaction: Transaction = None
        need_transaction_detail: bool = False

        for line in data:
            trimmed_line = line.strip()

            if trimmed_line.startswith('POSTED'):
                continue

            trip_start_match = SimplyGo.trip_start_regex.findall(trimmed_line)
            if len(trip_start_match) > 0:
                if curr_trip is not None:
                    trips.append(curr_trip)

                value = trip_start_match[0]
                curr_trip = Trip(
                    date=datetime.datetime.strptime(
                        value[0], SimplyGo.date_format_pattern).date(),
                    from_destination=value[2],
                    to_destination=value[5] if value[6] != "" else value[7],
                    fare=float(value[6]) if value[6] != "" else 0,
                    transactions=[]
                )

                # determined full description based on if it contains the fare
                need_trip_detail = curr_trip.fare == 0
                continue

            if trimmed_line.startswith("[Posting"):
                fare_match = SimplyGo.fare_regex.findall(trimmed_line)
                if len(fare_match) > 0:
                    curr_trip.fare = float(fare_match[0][1])
                    need_trip_detail = False
                else:
                    raise ValueError("Wrong format, posting doesn't have fare")
                continue

            if need_trip_detail and not trimmed_line == "":
                fare_match = SimplyGo.fare_regex.findall(trimmed_line)
                if len(fare_match) > 0:
                    curr_trip.to_destination += ' ' +fare_match[0][0]
                    curr_trip.fare = float(fare_match[0][1])
                    need_trip_detail = False
                else:
                    curr_trip.to_destination += ' ' +trimmed_line
                    # raise ValueError("Wrong format, trip detail doesn't have fare")

                continue

            transaction_start_match = SimplyGo.tansaction_start_regex.findall(
                trimmed_line)
            if len(transaction_start_match) > 0:
                value = transaction_start_match[0]

                fare = value[5]
                # determined full description based on if it contains the fare
                need_transaction_detail = fare == ""

                to_destination: str = value[3] or value[6]
                match = re.findall("\\(\\d+\\)", to_destination)

                curr_transaction = Transaction(
                    time=datetime.datetime.strptime(
                        value[0], SimplyGo.time_format_pattern).time(),
                    from_destination=value[1],
                    to_destination=to_destination,
                    fare=fare if not need_transaction_detail else 0,
                    transport=TransportType.BUS if match else TransportType.MRT
                )

                if not need_transaction_detail:
                    curr_trip.transactions.append(curr_transaction)

                continue

            if need_transaction_detail and not trimmed_line == "":
                fare_match = SimplyGo.fare_regex.findall(trimmed_line)
                if len(fare_match) > 0:
                    # end of transaction, found fare
                    value = fare_match[0]
                    route_detail = value[0].strip()

                    curr_transaction.to_destination += f' {route_detail}'
                    curr_transaction.fare = float(value[1])

                    match = re.findall("\\(\\d+\\)", route_detail)
                    curr_transaction.transport = TransportType.BUS if match else TransportType.MRT

                    need_transaction_detail = False
                    curr_trip.transactions.append(curr_transaction)
                else:
                    raise ValueError("missing transaction detail")

                continue

        trips.append(curr_trip)
        return trips


if __name__ == '__main__':
    m = FinanceManager("192.168.0.193:8888")
    m.load_asset_data()
    m.load_init_data()

    assets = m.asset_groups
    categories = {
        InOutCode.Expenses: m.expense_categories,
        InOutCode.Income: m.income_categories,
    }

    trips = SimplyGo.parse_pdf('../doc/TL-SimplyGo-TransactionHistory-12-Mar-24-00-33-56.pdf')
    # print(*trips, sep='\n')

    for trip in trips[::-1]:
        request = trip.to_request(assets, categories)
        print(request.to_dict())

        m.create_in_out_transaction(request)