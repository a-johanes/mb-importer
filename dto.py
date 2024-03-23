from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import datetime
from enum import Enum


class InOutCode(Enum):
    Income = 0
    Expenses = 1


@dataclass
class Category:
    id: str
    name: str
    in_out_code: InOutCode
    sub_category: Optional[List['Category']] = None

    @staticmethod
    def from_money_book(obj: Dict[str, Any], in_out_code: InOutCode) -> 'Category':
        id = obj.get('mcid', obj.get('mcscid', ''))
        name = obj.get('mcname', obj.get('mcscname', ''))
        sub_category = [Category.from_money_book(cat, in_out_code) for cat in obj.get('mcsc', [])] or None
        return Category(id, name, in_out_code, sub_category)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "in_out_code": self.in_out_code.name
        }

        if self.sub_category is not None:
            d["sub_category"] = [c.to_dict() for c in self.sub_category]

        return d


@dataclass
class Asset:
    id: str
    name: str
    money: float

    @staticmethod
    def from_money_book(obj: Dict[str, Any]) -> 'Asset':
        id = obj.get('assetId', '')
        name = obj.get('assetName', '')
        money = obj.get('assetMoney', '')
        money = float(money)
        return Asset(id, name, money)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money,
        }


@dataclass
class AssetGroup:
    id: str = ""
    name: str = ""
    money: float = 0
    children: Optional[List['Asset']] = None

    @staticmethod
    def from_money_book(obj: Dict[str, Any]) -> 'AssetGroup':
        id = obj.get('assetGroupId', '')
        name = obj.get('assetName', '')
        money = obj.get('assetMoney', '')
        money = float(money)

        children = [Asset.from_money_book(asset) for asset in obj.get('children', [])]
        return AssetGroup(id, name, money, children)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class CreateInOutTransactionRequest:
    in_out_code: InOutCode
    asset: Asset
    category: Category
    date: datetime.date = datetime.datetime.now()
    money: Optional[float] = None
    note: Optional[str] = None
    description: Optional[str] = None
    sub_category: Optional[Category] = None

    def __post_init__(self):
        if self.in_out_code != self.category.in_out_code:
            raise ValueError('category in out code has to be the same with transaction in out code')

        if self.sub_category is not None:
            if self.category.sub_category is None:
                raise ValueError("the category doesn't has any sub category")

            if self.sub_category not in self.category.sub_category:
                raise ValueError('sub category is not part of the given category')

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'mbDate': self.date.strftime('%Y-%m-%dT%H:%M:%S'),
            'inOutCode': self.in_out_code.value,
            'assetId': self.asset.id,
            'mcid': self.category.id,
        }

        if self.sub_category is not None:
            d['mcscid'] = self.sub_category.id

        field_names = {
            'money': 'mbCash',
            'note': 'mbContent',
            'description': 'mbDetailContent'
        }

        for field_name, request_field_name in field_names.items():
            field_value = self.__dict__[field_name]

            if field_value is not None:
                d[request_field_name] = field_value

        return d


@dataclass
class CreateTransferTransactionRequest:
    from_asset: Asset
    to_asset: Asset
    date: datetime.date = datetime.datetime.now()
    money: Optional[float] = None
    note: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'moveDate': self.date.strftime('%Y-%m-%dT%H:%M:%S'),
            'toAssetId': self.to_asset.id,
            'fromAssetId': self.from_asset.id,
        }

        field_names = {
            'money': 'moveMoney',
            'note': 'moneyContent',
            'description': 'mbDetailContent'
        }

        for field_name, request_field_name in field_names.items():
            field_value = self.__dict__[field_name]

            if field_value is not None:
                d[request_field_name] = field_value

        return d


if __name__ == '__main__':
    asset = Asset("9a423682-a294-46a4-b71a-7b1feb6da4fc", 'name', 110)
    # sub_category = Category('49abda9d-53a7-4a49-9006-9c1833f859f5', 'rent', InOutCode.Expenses)
    # category = Category('11', 'household', InOutCode.Expenses, sub_category=[sub_category])
    # r = CreateInOutTransactionRequest(InOutCode.Expenses, asset, category, sub_category=sub_category)
    r = CreateTransferTransactionRequest(asset, asset, money=10)
    print(r.to_dict())
