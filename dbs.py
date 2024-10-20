import datetime
from dataclasses import dataclass
from typing import List, Dict

import pandas as pd

from dto import AssetGroup, CreateTransferTransactionRequest
from finance_manager import FinanceManager


@dataclass
class Transaction:
    date: datetime.date
    value_date: datetime.date
    statement_code: str
    reference_code: str
    debit: float
    credit: float
    reference: str
    additional_info: str
    misc_info: str

    def to_request(self, asset_groups: List[AssetGroup]) -> CreateTransferTransactionRequest | None:
        asset_group = next(
            (group for group in asset_groups if group.id == '1'), None)
        if asset_group is None:
            return

        from_asset = next((asset for asset in asset_group.children if asset.id ==
                           '17ecb0ea-09b1-4251-aae0-c2706755f22d'), None)
        if from_asset is None:
            return

        to_asset = next((asset for asset in asset_group.children if asset.id ==
                         '05c64c05-8fa5-4b8d-a33c-0ab1a662fc65'), None)
        if to_asset is None:
            return

        request = CreateTransferTransactionRequest(
            from_asset,
            to_asset,
            self.date,
            self.debit,
            note=self.reference,
            description=self.additional_info if not self.misc_info else f'{self.additional_info} {self.misc_info}'
        )

        return request


class DBS:

    @staticmethod
    def parse_transaction_history_csv(path: str) -> pd.DataFrame:
        df = pd.read_csv(path, index_col=False, skiprows=19, na_filter=False)

        if df['Debit Amount'].dtypes == object:
            df.loc[df['Debit Amount'].str.isspace(), 'Debit Amount'] = 0

        df.loc[df['Debit Amount'] == '', 'Debit Amount'] = 0

        if df['Credit Amount'].dtypes == object:
            df.loc[df['Credit Amount'].str.isspace(), 'Credit Amount'] = 0

        df.loc[df['Credit Amount'] == '', 'Credit Amount'] = 0

        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], dayfirst=True)
        df['Value Date'] = pd.to_datetime(df['Value Date'], dayfirst=True)

        df = df.astype({
            'Debit Amount': float,
            'Credit Amount': float
        })

        return df


if __name__ == '__main__':
    dbs_df = DBS.parse_transaction_history_csv('/home/ajohanes/Downloads/b8fd0fffea50be10f53ff12d06f4026d.P000000077958701.csv')
    filtered_df = dbs_df.loc[((dbs_df['Statement Code'] == 'POS') & (dbs_df['Reference'] == 'BAT')) | ((dbs_df['Statement Code'] == 'GR') & (dbs_df['Reference'] == 'IBG'))]
    transactions = filtered_df.apply(lambda row: Transaction(*row), axis=1).to_list()

    # print(*transactions, sep='\n')

    m = FinanceManager("192.168.0.193:8888")
    m.load_asset_data()
    m.load_init_data()

    for transaction in transactions[::-1]:
        request = transaction.to_request(m.asset_groups)
        print(request.to_dict())

        m.create_transfer_transaction(request)
