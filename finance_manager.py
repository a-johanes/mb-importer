import json

from typing import List

import cson
import requests
from dto import *


class FinanceManager:
    def __init__(self, url: str):
        self.base_url = url
        self.income_categories: List['Category'] = []
        self.expense_categories: List['Category'] = []
        self.asset_groups: List['AssetGroup'] = []

    def get_remote_init_data(self):
        url = f"http://{self.base_url}/moneyBook/getInitData"

        response = requests.get(url)
        data = cson.loads(response.content)

        with open("./remote_all_data.json", "w") as f:
            json.dump(data, f, indent=4)

    def get_remote_asset_data(self):
        url = f"http://{self.base_url}/moneyBook/getAssetData"

        response = requests.get(url)
        data = cson.loads(response.content)

        with open("./remote_asset_data.json", "w") as f:
            json.dump(data, f, indent=4)

    def load_init_data(self):
        with open("./remote_all_data.json") as f:
            data = json.load(f)

        for cat in data['category_0']:
            self.income_categories.append(Category.from_money_book(cat, InOutCode.Income))

        for cat in data['category_1']:
            self.expense_categories.append(Category.from_money_book(cat, InOutCode.Expenses))

        income_category = [c.to_dict() for c in self.income_categories]
        expense_category = [c.to_dict() for c in self.expense_categories]

        with open("./init_data.json", "w") as f:
            json.dump({"income_category": income_category, "expense_category": expense_category}, f, indent=4)

    def load_asset_data(self):
        with open("./remote_asset_data.json") as f:
            data = json.load(f)

        for asset_group in data:
            self.asset_groups.append(AssetGroup.from_money_book(asset_group))

        asset_group = [a.to_dict() for a in self.asset_groups]

        with open("./asset_data.json", "w") as f:
            json.dump(asset_group, f, indent=4)

    def create_in_out_transaction(self, request: CreateInOutTransactionRequest):
        url = f"http://{self.base_url}/moneyBook/create"

        resp = requests.post(url, data=request.to_dict())
        print(resp)

    def create_transfer_transaction(self, request: CreateTransferTransactionRequest):
        url = f"http://{self.base_url}/moneyBook/moveAsset"

        resp = requests.post(url, data=request.to_dict())
        print(resp)


if __name__ == '__main__':
    m = FinanceManager("192.168.0.197:8888")
    m.get_remote_init_data()
    m.get_remote_asset_data()
    m.load_init_data()
    m.load_asset_data()
