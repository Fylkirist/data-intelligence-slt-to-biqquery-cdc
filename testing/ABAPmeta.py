"""
ABAP Metadata class
-------------------
Handling the ABAP metadata attributes across the operators in the SLT to Google BigQuery suite

"""

__version__ = '0.2'
__author__ = 'BK'

import pyarrow as pa

class AbapMeta:
    # Constants
    PASSTHROUGH = "Passthrough"
    OPTIMIZE = "Optimize"
    OPTIMIZE_WITH_NULLS = "Optimize with NULLS"

    def __init__(self, attributes):
        # Get attributes from the config environment
        self.optimize_method = attributes.get("ak.abap.data_transformer")
        self.alpha_conversion = attributes.get("ak.abap.alpha_conversion")
        self.insert_timestamp = attributes.get("ak.abap.insert_timestamp")
        # Check if EOF message (Initial Load scenario)
        if attributes["ABAP"]["Kind"] == "Element":
            self.lastBatch = True
            #self.is_valid_ABAP = False
            # api.send("output", data)
            # api.send("info", "Received lastBatch=True message from SLT")
            return
        self.lastBatch = False
        ABAPKEY = attributes["ABAP"]
        METAKEY = attributes["metadata"]
        self.col_names = []
        self.col_types = {}
        self.col_meta = {}

        if self.insert_timestamp:  # Add new column in ABAP description - not available in source
            ABAPKEY["Fields"].append(
                {
                "Name": "INSERT_TS",
                "Type": "",
                "Kind": "Z",
                "Length": 0.0,
                "Decimals": 0.0
            })
        for columnname in ABAPKEY["Fields"]:
            self.col_names.append(columnname["Name"])
            # col_types[columnname['Name']] = columnname['Kind']
            self.col_types[
                columnname["Name"]
            ] = columnname  # add the abap struct to the columnname for easier lookup
            # abapdesc = [item for item in ABAPKEY["Fields"] if item["Name"] == columnname['Name']][0]
            # print(abapdesc)
            desc = (
                {"MD_DOMNAME": "SAP_DI", "ABAPTYPE": "CHAR"}
                if columnname["Name"]
                in [
                    "TABLE_NAME",
                    "IUUC_OPERATION",
                    "INSERT_TS",
                ]
                else [
                    item
                    for item in METAKEY
                    if item["Field"]["COLUMNNAME"] == columnname["Name"]
                ][0]["Field"]
            )
            self.col_meta[columnname["Name"]] = desc
            # print(desc)
            self.is_valid_ABAP = True
        return

    # Methods to easily retreive values
    def meta_value(self, colname, metaname):  # ABAP struct
        return self.col_meta[colname][metaname]

    def abap_value(self, colname, abapname):  # metadata struct
        return self.col_types[colname][abapname]

    def meta(self, colname):
        return self.col_meta[colname]

    def set_abap_kind(self, colname, kind):
        if colname in self.col_types and len(kind) == 1:
            self.col_types[colname]["Kind"] = kind
        else:
            raise Exception(
                f"ABAPmeta: Could not set {colname} to {kind}, the column name do not exist in structure or length of type >1!"
            )

    def pyarrow_schema(self):
        print(f"opt_met={self.optimize_method}, const={self.OPTIMIZE_WITH_NULLS}")
        if self.optimize_method != self.OPTIMIZE_WITH_NULLS:
            print("Strings only")
            _schema = {c: pa.string() for c in self.col_names}
            return _schema
        _schema = {}
        print("Specific datatypes")
        for _col in self.col_names:
            if self.col_types[_col]["Kind"] in [
                "I",
                "N",
                "s",
            ]:  # "s" is an internal INT2 ABAP type
                _dt = pa.int64()
            elif self.col_types[_col]["Kind"] in [
                "F",
            ]:
                _dt = pa.float64()
            elif self.col_types[_col]["Kind"] in ["P"]:
                if self.col_meta[_col]["MD_DOMNAME"] in ["/SCMB/TMDL_TZNTSTMPS", "/SCWM/DO_TIMESTAMP_WH"]:
                    _dt = pa.int64()
                else:
                    _dt = pa.string()
            else:
                _dt = pa.string()
            _schema[_col] = _dt
        return _schema
        
    def pyarrow_strings_can_be_null(self):
        return True if self.optimize_method == self.OPTIMIZE_WITH_NULLS else False

## MAIN -- will only run when testing code
if __name__ == "__main__":
    print("Executed when invoked directly")
    import json
    import pyarrow as pa
    import pyarrow.csv as csv

    # Reading in JSON file and CSV file for SR_ACT
    PATH = "<mypath>"
    JSON_FILE = PATH + "/" + "tu_sr_act_initial.json"

    with open(JSON_FILE, "r") as f:
        mydict = json.load(f)

    mydict["ak.abap.data_transformer"] = "Optimize with NULLS"
    m = AbapMeta(mydict)
    print(m.optimize_method)
    print(m.pyarrow_strings_can_be_null())
    print(m.pyarrow_schema())
    
