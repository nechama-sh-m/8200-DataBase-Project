import json
import os
import db_api
from db_api import *

import operator

operator_dict = {"<": operator.lt,
                 "<=": operator.le,
                 "=": operator.eq,
                 "!=": operator.ne,
                 ">=": operator.ge,
                 ">": operator.gt}

Table_data = f"./{DB_ROOT}/Table_data.json"
index_dir_path = f"./{DB_ROOT}/Table_indexes"


@dataclass_json
@dataclass
class DBTable(db_api.DBTable):
    name: str
    fields: List[DBField]
    key_field_name: str

    def count(self) -> int:
        new_dict = DataBase.get_table_as_dict(DataBase, self.name)
        return len(new_dict.keys())
        # raise NotImplementedError

    def insert_record(self, values: Dict[str, Any]) -> None:
        table = DataBase.get_table_as_dict(DataBase, self.name)
        # new key exists already
        if str(values[self.key_field_name]) in table.keys():
            raise ValueError
        # we keep the table itself without the key
        dict_without_key = {i: values[i] for i in values.keys() if i != self.key_field_name}
        table[values[self.key_field_name]] = dict_without_key
        DataBase.set_table(DataBase, self.name, table)

        # function updates whatever indexes exists
        self.update_index_if_need(dict_without_key, values[self.key_field_name], "insert")

    def delete_record(self, key: Any) -> None:
        key_as_str = str(key)
        new_dict = DataBase.get_table_as_dict(DataBase, self.name)

        if key_as_str not in new_dict.keys():
            raise ValueError

        # function updates whatever indexes exists
        self.update_index_if_need(new_dict[key_as_str], key_as_str, "delete")
        new_dict.pop(key_as_str, None)
        DataBase.set_table(DataBase, self.name, new_dict)

    def delete_records(self, criteria: List[SelectionCriteria]) -> None:
        # get all records that need to be deleted
        list_to_delete = self.query_table(criteria)

        for record in list_to_delete:
            self.delete_record(record[self.key_field_name])

    def get_record(self, key: Any) -> Dict[str, Any]:
        table = DataBase.get_table_as_dict(DataBase, self.name)
        record = table.get(str(key))
        # add the key to record
        if record is not None:
            record[self.key_field_name] = key
        return record

    def update_record(self, key: Any, values: Dict[str, Any]) -> None:
        old_record = self.get_record(key)
        self.delete_record(key)

        # update the record to insert back
        for key_to_change in values.keys():
            old_record[key_to_change] = values[key_to_change]
        # insert gets the record with the key
        old_record[self.key_field_name] = key
        self.insert_record(old_record)

    def query_key_field(self, condition: SelectionCriteria, table: dict):
        matching_records = []
        operator_func = operator_dict[condition.operator]
        # if the operator is "=" go straight to right key
        if condition.operator == "=":
            if table.get(str(condition.value)):
                return {str(condition.value)}
        else:
            # go through all key and find matching to condition
            for key in table.keys():
                if operator_func(key, str(condition.value)):
                    matching_records += [key]

            return set(matching_records)

    def query_from_index(self, condition: SelectionCriteria, path: str):
        matching_records = []
        operator_func = operator_dict[condition.operator]
        # open the right index file
        with open(path) as the_file:
            index_table = json.load(the_file)
        # if the operator is "=" go straight to right key in index table
        if condition.operator == "=":
            if index_table.get(str(condition.value)):
                return set(index_table.get(str(condition.value)))
        else:
            # go through all key in index table and find matching to condition
            for key in index_table.keys():
                if operator_func(key, str(condition.value)):
                    matching_records += index_table[key]
            return set(matching_records)

    def query_no_index(self, condition: SelectionCriteria, table: dict):
        matching_records = []
        operator_func = operator_dict[condition.operator]
        # go through entire table and find maching to condition
        for key in table.keys():
            if table[key].get(condition.field_name):
                if operator_func(str(table[key].get(condition.field_name)), str(condition.value)):
                    matching_records += [key]
        return set(matching_records)

    def query_table(self, criteria: List[SelectionCriteria]) -> List[Dict[str, Any]]:
        table = DataBase.get_table_as_dict(DataBase, self.name)
        query_return_list = []
        # in the list we will store a set each condition
        list_of_set = []
        for condition in criteria:
            # if the condition is on th key
            if condition.field_name == self.key_field_name:
                list_of_set.append(self.query_key_field(condition, table))

            else:
                path = f"{index_dir_path}/{self.name}_index/{condition.field_name}_index.json"
                # if we have an index for this field
                if Path(path).exists():
                    with open(path) as the_file:
                        self.query_from_index(condition, path)

                else:
                    # no index,regular search
                    list_of_set.append(self.query_no_index(condition, table))

        if len(list_of_set) == 0:
            return []
        # intersection of all sets will to give us the key that match all condition
        query_return_keys = list_of_set[0]
        for i in range(len(list_of_set)):
            query_return_keys = query_return_keys & list_of_set[i]
        # get full records og all matching keys and add to list
        for i in query_return_keys:
            query_return_list.append(self.get_record(i))

        return query_return_list

    def create_index(self, field_to_index: str) -> None:
        # create a directory to hold index tables (if not exist yet)
        if not Path(index_dir_path).exists():
            os.mkdir(index_dir_path)
        dir_for_index = f"{index_dir_path}/{self.name}_index"
        # create directary for this table's indexes if doesn't exist yet
        if not Path(dir_for_index).exists():
            os.mkdir(dir_for_index)

        path = f"{dir_for_index}/{field_to_index}_index.json"
        # if already have requested index - no need to create
        if Path(path).exists():
            return

        table = DataBase.get_table_as_dict(DataBase, self.name)
        index_dict = {}
        for key in table.keys():
            key_to_index = str(table[key].get(field_to_index))
            if index_dict.get(key_to_index) is None:
                index_dict[key_to_index] = []
            index_dict[key_to_index].append(key)

        with open(path, 'w') as outfile:
            json.dump(index_dict, outfile, default=str)

    def update_index_if_need(self, new_record: dict, key: str, action: str):
        # loop through all fields in record
        for field in new_record.keys():
            path = f"{index_dir_path}/{self.name}_index/{field}_index.json"
            # for each field check if there is an index
            if Path(path).exists():
                with open(path) as the_file:
                    index_dict = json.load(the_file)
                # to things according to the right action
                if action == "delete":
                    index_dict[str(new_record[field])].remove(key)
                elif action == "insert":
                    new_key_for_index = str(new_record[field])
                    # if the value of the field doesn't exist yet in index - add it
                    if index_dict.get(new_key_for_index) is None:
                        index_dict[new_key_for_index] = []
                    # add key of record to list of the right index
                    if key not in index_dict[new_key_for_index]:
                        index_dict[new_key_for_index].append(key)

                with open(path, 'w') as outfile:
                    json.dump(index_dict, outfile, default=str)


@dataclass_json
@dataclass
class DataBase(db_api.DataBase):

    # Put here any instance information needed to support the API
    def create_table(self,
                     table_name: str,
                     fields: List[DBField],
                     key_field_name: str) -> DBTable:

        # create a file for all tables' data (if not exist yet)
        if not Path(Table_data).exists():
            with open(Table_data, 'w') as outfile:
                json.dump({}, outfile)

            # if the key field is not in the list of fields
            if key_field_name not in [y.name for y in fields]:
                raise ValueError

        new_table = {}
        path = f"./{DB_ROOT}/{table_name}.json"

        # open file for new table and add empty dict
        with open(path, 'w') as outfile:
            json.dump(new_table, outfile)

        # add details of new table to tables' data list
        with open(Table_data) as the_file:
            table_data_dict = json.load(the_file)

        fields_list = []
        for field in fields:
            fields_list.append(field.to_dict())

        table_data_dict[table_name] = tuple([path, fields_list, key_field_name])

        with open(Table_data, 'w') as outfile:
            json.dump(table_data_dict, outfile, default=str)

        return_table = DBTable(table_name, fields, key_field_name)
        return return_table

    def num_tables(self) -> int:
        # count keys in tables' data
        if Path(Table_data).exists():
            with open(Table_data) as the_file:
                path_dict = json.load(the_file)
            return len(path_dict.keys())
        else:
            return 0

    def get_table_as_dict(self, table_name: str) -> DBTable:
        with open(Table_data) as the_file:
            table_data = json.load(the_file)
            # get the right path from table's data
        path = table_data.get(table_name)[0]
        if path is None:
            return None
        with open(path) as the_file:
            table = json.load(the_file)
        return table

    def get_table(self, table_name: str) -> DBTable:
        with open(Table_data) as the_file:
            table_data = json.load(the_file)
        return DBTable(table_name, table_data.get(table_name)[1], table_data.get(table_name)[2])

    def set_table(self, table_name: str, table):
        path = f"./{DB_ROOT}/{table_name}.json"
        with open(path, 'w') as outfile:
            json.dump(table, outfile, default=str)

    def delete_table(self, table_name: str) -> None:
        with open(Table_data) as the_file:
            table_data = json.load(the_file)
        # delete json file of table
        os.remove(table_data.get(table_name)[0])
        # remove data of this table from tables_data file
        table_data.pop(table_name)
        with open(Table_data, 'w') as outfile:
            json.dump(table_data, outfile)

    def get_tables_names(self) -> List[Any]:
        # get all key from tables_data file
        with open(Table_data) as the_file:
            table_data = json.load(the_file)
        return list(table_data.keys())
        # raise NotImplementedError

    def join_two_table(self, first: list, second: list, fields_to_join_by: List[str]):
        joined_tables = []
        # for each record in first table, compare fields_to_join_by with each record in second table
        for record_first in first:
            for record_second in second:
                for field in fields_to_join_by:
                    if record_first[field] != record_second[field]:
                        break
                # didn't go to break - all fields_to_join_by were the same - add to joined table
                else:
                    joined_and_marge = record_first.copy()
                    joined_and_marge.update(record_second)
                    joined_tables.append(joined_and_marge)
        return joined_tables

    def query_multiple_tables(
            self,
            tables: List[str],
            fields_and_values_list: List[List[SelectionCriteria]],
            fields_to_join_by: List[str]
    ) -> List[Dict[str, Any]]:
        lists_of_matching_records = []
        # for each table get records that math its condition
        for tables_index in range(len(tables)):
            lists_of_matching_records.append(
                self.get_table(tables[tables_index]).query_table([fields_and_values_list[tables_index]]))
        # if got less than two table - nothing to join with
        if len(lists_of_matching_records) < 2:
            return lists_of_matching_records

        # start with joining first two table
        joined_tables = self.join_two_table(lists_of_matching_records[0],
                                  lists_of_matching_records[1], fields_to_join_by)

        # for each of the rest of tables - join with already joined
        for table_index in range(2, len(lists_of_matching_records)):
            joined_tables = self.join_two_table(joined_tables, lists_of_matching_records[table_index],
                                      fields_to_join_by)

        return joined_tables

