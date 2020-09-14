from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Type
from dataclasses_json import dataclass_json

DB_ROOT = Path('db_files')


@dataclass_json
@dataclass
class DBField:
    name: str
    type: Type


@dataclass_json
@dataclass
class SelectionCriteria:
    field_name: str
    operator: str
    value: Any


@dataclass_json
@dataclass
class DBTable:
    name: str
    fields: List[DBField]
    key_field_name: str

    def count(self) -> int:
        raise NotImplementedError

    def insert_record(self, values: Dict[str, Any]) -> None:
        raise NotImplementedError

    def delete_record(self, key: Any) -> None:
        raise NotImplementedError

    def delete_records(self, criteria: List[SelectionCriteria]) -> None:
        raise NotImplementedError

    def get_record(self, key: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def update_record(self, key: Any, values: Dict[str, Any]) -> None:
        raise NotImplementedError

    def query_table(self, criteria: List[SelectionCriteria]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def create_index(self, field_to_index: str) -> None:
        raise NotImplementedError


@dataclass_json
@dataclass
class DataBase:

    # Put here any instance information needed to support the API
    def create_table(self,
                     table_name: str,
                     fields: List[DBField],
                     key_field_name: str) -> DBTable:
        raise NotImplementedError

    def num_tables(self) -> int:
        raise NotImplementedError

    def get_table(self, table_name: str) -> DBTable:
        raise NotImplementedError

    def delete_table(self, table_name: str) -> None:
        raise NotImplementedError

    def get_tables_names(self) -> List[Any]:
        raise NotImplementedError

    def query_multiple_tables(
            self,
            tables: List[str],
            fields_and_values_list: List[List[SelectionCriteria]],
            fields_to_join_by: List[str]
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

# my_db = DataBase()
# field_animals = [DBField("aid", str), DBField("name", str), DBField("age", int), DBField("species", str)]
# field_empolyee = [DBField("pid", str), DBField("pname", str), DBField("phone", int), DBField("category", list)]
# table_animals = my_db.create_table("animals", field_animals, "aid")
# table_employee = my_db.create_table("employee", field_animals, "pid")
# print(my_db.table_dict)
# print(table_animals.count())
# a1_dict = {"aid": "a1",
#            "name": "aaa",
#            "age": 5,
#            "species": "lion"}
# table_animals.insert_record(a1_dict)
# a2_dict = {"aid": "a2",
#            "name": "bbb",
#            "age": 6,
#            "species": "tiger"}
# table_animals.insert_record(a2_dict)
# # table_animals.delete_record("a1")
#
# print(table_animals.get_record("a2"))
# a3_dict = {"aid": "a2",
#            "name": "bbb",
#            "age": 6,
#            "species": "dog"}
#
# table_animals.update_record("a2", a3_dict)
# p1_dict = {"pid": "p1",
#            "pname": "Bob",
#            "contact": "1234",
#            "category": ["lion", "fish"]}
# table_employee.insert_record(p1_dict)
# print(my_db.get_tables_names())
# my_db.delete_table("employee")
# print(my_db.table_dict)
# print(my_db.num_tables())
# c1 = SelectionCriteria("age", ">=", 5)
# c2 = SelectionCriteria("species", "==", "lion")
# c = [c1, c2]
# print(table_animals.query_table(c))
# table_animals.delete_records([c2])
