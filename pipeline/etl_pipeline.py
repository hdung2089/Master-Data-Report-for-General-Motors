"""
etl_pipeline.py
───────────────
Core ETL transformation script for the GM AP-GMNA supply chain report.

Reads from:
  - Combined File.xlsx        (base shipment template)
  - Replicate_file.xlsx       (TMS data exports: Intransit, Query 3, Query 4, etc.)

Outputs:
  - FinalReplicate.xlsx       (master report for Power BI)

Key transformations:
  - 20+ lookup table merges (supplier names, locations, plant names)
  - CBM and weight calculation from container type references
  - 12-stage shipment status waterfall logic
  - CCA (Customs Consolidation Area) routing logic
"""

import pandas as pd
import numpy as np

# ==================== CONFIGURATION ====================
combined_path  = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\Combined File.xlsx"
replicate_path = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\Replicate_file.xlsx"
output_path    = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\FinalReplicate.xlsx"
# =======================================================

combined_df        = pd.read_excel(combined_path)
replicate_df       = pd.read_excel(replicate_path, sheet_name="Intransit")
replicate_query3   = pd.read_excel(replicate_path, sheet_name="Query 3")
replicate_Location = pd.read_excel(replicate_path, sheet_name="Location")
replicate_query4   = pd.read_excel(replicate_path, sheet_name="Query 4")
replicate_notes    = pd.read_excel(replicate_path, sheet_name="Notes")
replicate_cca      = pd.read_excel(replicate_path, sheet_name="CCA")
replicate_io       = pd.read_excel(replicate_path, sheet_name="IO")
replicate_yesterday= pd.read_excel(replicate_path, sheet_name="Yesterday")
replicate_trailer  = pd.read_excel(replicate_path, sheet_name="PRN")
replicate_csp      = pd.read_excel(replicate_path, sheet_name="CSP")

# ── Base fields ──────────────────────────────────────────────────────
combined_df["LSC Tracking Number"]  = replicate_df["STI#"]
combined_df["LSC"]                  = "CEVV"
combined_df["Specialized Transport"]= "NO"
combined_df["SID Number"]           = replicate_df["SHIPMENT_ID_NUMBER"]
combined_df["Part Number"]          = replicate_df["PART_NUMBER"]
combined_df["Quantity"]             = replicate_df["QUANTITY"]
combined_df["Service Level"]        = replicate_df["REFERENCE_NUMBER"]
combined_df["Ship Date from Supplier"] = replicate_df["SHIPMENT_DATETIME"]
combined_df["Mode"]                 = "OCEAN"
combined_df["Provider Lane ID"]     = "MGOB"

# ── Lookups from Query 3 ─────────────────────────────────────────────
lookup_origin_dun    = replicate_query3.set_index("STI#")["ORIGIN DUN"].to_dict()
lookup_so            = replicate_query3.set_index("STI#")["SO#"].to_dict()
lookup_num_packages  = replicate_query3.set_index("STI#")["NUMBER OF PACKAGES"].to_dict()
lookup_packaging_type= replicate_query3.set_index("STI#")["MODIFIED PACKAGING TYPE"].to_dict()
lookup_prn           = replicate_query3.set_index("STI#")["MODIFIED PRN#"].to_dict()
lookup_hbl           = replicate_query3.set_index("STI#")["MODIFIED HBL"].to_dict()
lookup_mbl           = replicate_query3.set_index("STI#")["MODIFIED MBL"].to_dict()
lookup_contid        = replicate_query3.set_index("STI#")["MODIFIED CONT ID"].to_dict()
lookup_contype       = replicate_query3.set_index("STI#")["MODIFIED CONT TYPE"].to_dict()
lookup_btc           = replicate_query3.set_index("STI#")["BTC"].to_dict()
lookup_vol1          = replicate_query3.set_index("STI#")["MODIFIED VOL1"].to_dict()
lookup_weight1       = replicate_query3.set_index("STI#")["MODIFIED WEIGHT1"].to_dict()
lookup_vol2          = replicate_query3.set_index("STI#")["MODIFIED VOL2"].to_dict()
lookup_weight2       = replicate_query3.set_index("STI#")["MODIFIED WEIGHT2"].to_dict()
lookup_consol        = replicate_query3.set_index("STI#")["MODIFIED CONSOL DUN"].to_dict()
lookup_dest_dun      = replicate_query3.set_index("STI#")["DEST DUN"].to_dict()
lookup_cca           = replicate_cca.set_index("DUNS Number")["CCA"].to_dict()
lookup_manifest      = replicate_query3.set_index("STI#")["MODIFIED MANIFEST"].to_dict()
lookup_mti           = replicate_query3.set_index("STI#")["MODIFIED MASTER_UNITLOAD_ID"].to_dict()
lookup_scac          = replicate_query3.set_index("STI#")["MODIFIED SCAC CODE"].to_dict()
lookup_vessel        = replicate_query3.set_index("STI#")["MODIFIED VESSEL NAME"].to_dict()
lookup_path          = replicate_query3.set_index("STI#")["PATH"].to_dict()
lookup_scacname      = replicate_notes.set_index("Carrier SCAC/IATA")["Name"].to_dict()
lookup_outbound      = replicate_trailer.set_index("LSC Tracking Number")["Outbound Trailer #"].to_dict()
lookup_tms           = replicate_trailer.set_index("LSC Tracking Number")["Outbound TMS #"].to_dict()

# ── Lookups from Location tab ────────────────────────────────────────
lookup_num_Suppliername    = replicate_Location.set_index("LOCATION_ALIAS")["NAME"].to_dict()
lookup_num_Suppliercity    = replicate_Location.set_index("LOCATION_ALIAS")["CITY"].to_dict()
lookup_num_Supplierstate   = replicate_Location.set_index("LOCATION_ALIAS")["STATE"].to_dict()
lookup_num_Suppliercountry = replicate_Location.set_index("LOCATION_ALIAS")["COUNTRY_NAME"].to_dict()

# ── Map all lookup fields ────────────────────────────────────────────
combined_df["Supplier DUNS"]          = combined_df["LSC Tracking Number"].map(lookup_origin_dun)
combined_df["SO#"]                    = combined_df["LSC Tracking Number"].map(lookup_so)
combined_df["Manifest"]               = combined_df["LSC Tracking Number"].map(lookup_manifest)
combined_df["MTI"]                    = combined_df["LSC Tracking Number"].map(lookup_mti)
combined_df["Steamship Line SCAC"]    = combined_df["LSC Tracking Number"].map(lookup_scac)
combined_df["Vessel Name"]            = combined_df["LSC Tracking Number"].map(lookup_vessel)
combined_df["Path"]                   = combined_df["LSC Tracking Number"].map(lookup_path)
combined_df["Number of Packages"]     = combined_df["LSC Tracking Number"].map(lookup_num_packages)
combined_df["Packaging type"]         = combined_df["LSC Tracking Number"].map(lookup_num_packages)
combined_df["Supplier Name"]          = combined_df["Supplier DUNS"].map(lookup_num_Suppliername)
combined_df["Origin Supplier City"]   = combined_df["Supplier DUNS"].map(lookup_num_Suppliercity)
combined_df["Origin Supplier Province"]= combined_df["Supplier DUNS"].map(lookup_num_Supplierstate)
combined_df["Origin Supplier Country"]= combined_df["Supplier DUNS"].map(lookup_num_Suppliercountry)
combined_df["PRN#"]                   = combined_df["LSC Tracking Number"].map(lookup_prn)
combined_df["HBOL"]                   = combined_df["LSC Tracking Number"].map(lookup_hbl)
combined_df["MBOL"]                   = combined_df["LSC Tracking Number"].map(lookup_mbl)
combined_df["Container Number"]       = combined_df["LSC Tracking Number"].map(lookup_contid)
combined_df["Container Type"]         = combined_df["LSC Tracking Number"].map(lookup_contype)
combined_df["Bill to Cisco"]          = combined_df["LSC Tracking Number"].map(lookup_btc)
combined_df["VOL1"]                   = combined_df["LSC Tracking Number"].map(lookup_vol1)
combined_df["WEIGHT1"]                = combined_df["LSC Tracking Number"].map(lookup_weight1)
combined_df["VOL2"]                   = combined_df["LSC Tracking Number"].map(lookup_vol2)
combined_df["WEIGHT2"]                = combined_df["LSC Tracking Number"].map(lookup_weight2)
combined_df["Origin Consol DUNS"]     = combined_df["LSC Tracking Number"].map(lookup_consol)
combined_df["Dest Dun"]               = combined_df["LSC Tracking Number"].map(lookup_dest_dun)
combined_df["Dest Country"]           = combined_df["Dest Dun"].map(lookup_num_Suppliercountry)
combined_df["CCA"]                    = combined_df["Dest Dun"].map(lookup_cca)
combined_df["Steamship Line"]         = combined_df["Steamship Line SCAC"].map(lookup_scacname)
combined_df["Outbound Trailer #"]     = combined_df["LSC Tracking Number"].map(lookup_outbound)
combined_df["Outbound TMS #"]         = combined_df["LSC Tracking Number"].map(lookup_tms)

# ── Normalize numeric keys for Query 4 merge ────────────────────────
def normalize_shipment_id(series):
    """Convert IDs to numeric format (handles numbers, strings, datetimes, Excel serials)"""
    cleaned = []
    for val in series:
        if pd.isna(val):
            cleaned.append(np.nan)
        elif isinstance(val, pd.Timestamp):
            cleaned.append(int(val.strftime("%Y%m%d")))
        elif isinstance(val, (int, float)) and 20000 < val < 90000:
            try:
                date = pd.to_datetime("1899-12-30") + pd.to_timedelta(val, unit="D")
                cleaned.append(int(date.strftime("%Y%m%d")))
            except Exception:
                cleaned.append(np.nan)
        else:
            try:
                cleaned.append(float(val))
            except Exception:
                cleaned.append(np.nan)
    return pd.Series(cleaned, dtype="float64")

combined_df["LSC Tracking Number"]            = normalize_shipment_id(combined_df["LSC Tracking Number"])
replicate_query4["EM_SHIPMENT_ID_CLEAN"]      = normalize_shipment_id(replicate_query4["EM_SHIPMENT_ID"])

# ── Query 4 column mapping ───────────────────────────────────────────
query4_columns = {
    " Arrived at Consol":                        "Arrived at Consol Actual Date/Time",
    "Depart Consol Center":                      "Departed Consol Actual Date/Time",
    "Actual Arrived at Port of Departure":       "Actual Date of arrival to the origin port ",
    "Expected Arrived at Transshipment Port":    "Expected Arrival Date To Transshipment Port",
    "Actual Arrived at Transshipment Port":      "Actual Arrival Date To Transshipment Port",
    "Expected Departed Transshipment Port":      "Expected Departure Date From Transshipment Port",
    "Actual Departed Transshipment Port":        "Actual Departure Date From Transshipment Port",
    "Expected Depart Origin Port":               "Expected Date Of Departure From Origin Port",
    "Actual Depart Origin Port":                 "Actual Date Of Departure From Origin Port",
    "Expected Arrived at Port of Entry":         "Expected Date of Arrival To Destination Port",
    "Actual Arrived at Port of Entry":           "Actual Date of Arrival To Destination Port",
    "Expected Outgate":                          "Expected Outgate Date From Destination Port",
    "Actual Outgate":                            "Actual Outgate Date From Destination Port",
    "expected Arrived Destination Rail Ramp":    "Estimated Arrival Date To Destination Rail Yard",
    "Actual Arrived Destination Rail Ramp":      "Actual Arrival Date To Destination Rail Yard",
    "Expected Departed Destination Rail Ramp":   "Expected Departure Date From Destination Rail Yard",
    "Actual Departed Destination Rail Ramp":     "Actual Departure from Dest Rail",
    "POL":                                       "Port of Loading Code",
    "Transshipment Port":                        "Transshipment Port Name",
    "POD":                                       "Port of Destination Code"
}

existing_cols = [col for col in query4_columns.keys() if col in replicate_query4.columns]

merged_q4 = combined_df[["LSC Tracking Number"]].merge(
    replicate_query4[["EM_SHIPMENT_ID_CLEAN"] + existing_cols],
    how="left",
    left_on="LSC Tracking Number",
    right_on="EM_SHIPMENT_ID_CLEAN"
)

for src_col, dest_col in query4_columns.items():
    if src_col in merged_q4.columns:
        combined_df[dest_col] = merged_q4[src_col]

combined_df.drop(columns=["EM_SHIPMENT_ID_CLEAN"], inplace=True, errors="ignore")

# ── Destination DUNS logic ───────────────────────────────────────────
combined_df["Destination DUNS"] = np.where(
    (combined_df["CCA"] == "CCA")
    & (combined_df["Service Level"].str.upper() == "LCL")
    & (combined_df["Dest Country"].str.upper() == "UNITED STATES OF AMERICA"),
    101452410,
    combined_df["Dest Dun"]
)

lookup_finaldest = replicate_Location.set_index("LOCATION_ALIAS")["NAME"].to_dict()
combined_df["Final Delivery Location Name"] = combined_df["Destination DUNS"].map(lookup_finaldest)
combined_df["Destination City"]             = combined_df["Destination DUNS"].map(lookup_num_Suppliercity)
combined_df["Destination State"]            = combined_df["Destination DUNS"].map(lookup_num_Supplierstate)
combined_df["Destination Country"]          = combined_df["Destination DUNS"].map(lookup_num_Suppliercountry)

# ── Plant Name logic ─────────────────────────────────────────────────
lookup_io_name          = replicate_io.set_index("Cisco Code")["Cisco Supplier Name"].to_dict()
lookup_q3_cca_location  = replicate_query3.set_index("STI#")["MODIFIED CCA LOCATION"].to_dict()
lookup_cca_name         = replicate_cca.set_index("DUNS Number")["Cisco Supplier Name"].to_dict()

mask_blank_cca = combined_df["CCA"].isna() | (combined_df["CCA"].astype(str).str.strip() == "")
combined_df.loc[mask_blank_cca, "Plant Name"] = combined_df.loc[mask_blank_cca, "Bill to Cisco"].map(lookup_io_name)

mask_cca = combined_df["CCA"].astype(str).str.strip().eq("CCA")
combined_df.loc[mask_cca, "Plant Name"] = combined_df.loc[mask_cca, "LSC Tracking Number"].map(lookup_q3_cca_location)

mask_missing_after_q3 = mask_cca & (
    combined_df["Plant Name"].isna() | (combined_df["Plant Name"].astype(str).str.strip() == "")
)
mask_pontiac  = mask_missing_after_q3 & (combined_df["Destination DUNS"] == 101452410)
mask_lookup_cca = mask_missing_after_q3 & (combined_df["Destination DUNS"] != 101452410)

combined_df.loc[mask_pontiac, "Plant Name"]    = "UNIVERSAL PONTIAC CROSS DOCK"
combined_df.loc[mask_lookup_cca, "Plant Name"] = combined_df.loc[mask_lookup_cca, "Destination DUNS"].map(lookup_cca_name)
combined_df["Plant Name"] = combined_df["Plant Name"].fillna("")

# ── Container reference table ────────────────────────────────────────
container_data = {
    "Container type": [
        "20' Standard", "40' Standard ISO", "40' High Cube",
        "20' Standard NON-Operating Reefer", "40' Standard NON-Operating Reefer",
        "40' High Cube NON-Operating Reefer", "20' Standard Reefer",
        "40' Standard Container Reefer", "40' High Cube Reefer",
        "45' High Cube", "45' High Cube Reefer"
    ],
    "Max CBM":    [31.1, 63.6, 72.2, 28.2, 65.6, 63.9, 28.2, 65.6, 63.9, 88.28, 88.28],
    "Max Weight": [19550, 19550, 19550, 16330, 16330, 16330, 16330, 16330, 16330, 19550, 19550]
}
container_df = pd.DataFrame(container_data)

# ── CBM calculation ──────────────────────────────────────────────────
if "LSC Tracking Number" in replicate_yesterday.columns and "CBM" in replicate_yesterday.columns:
    cbm_lookup = (replicate_yesterday[["LSC Tracking Number", "CBM"]]
        .dropna(subset=["LSC Tracking Number"])
        .drop_duplicates(subset=["LSC Tracking Number"], keep="first")
        .set_index("LSC Tracking Number")["CBM"].to_dict())
else:
    cbm_lookup = {}

combined_df["CBM"] = combined_df["LSC Tracking Number"].map(cbm_lookup)
container_cbm_lookup = container_df.set_index("Container type")["Max CBM"].to_dict()
combined_df["Smaller_VOL"] = combined_df[["VOL1", "VOL2"]].min(axis=1)

def calculate_cbm(row):
    current_cbm = row.get("CBM")
    if pd.notna(current_cbm) and current_cbm != "":
        return current_cbm
    vol_value = row.get("Smaller_VOL")
    container_type = row.get("Container Type")
    max_cbm = container_cbm_lookup.get(container_type)
    if pd.isna(vol_value) or pd.isna(max_cbm):
        return None
    vol_m3 = vol_value * 0.02831685
    return vol_m3 if vol_m3 <= max_cbm else None

combined_df.loc[combined_df["CBM"].isna(), "CBM"] = combined_df.apply(calculate_cbm, axis=1)
combined_df.drop(columns=["Smaller_VOL"], inplace=True, errors="ignore")

# ── Weight calculation ───────────────────────────────────────────────
if "LSC Tracking Number" in replicate_yesterday.columns and "Weight in KG" in replicate_yesterday.columns:
    weight_lookup = (replicate_yesterday[["LSC Tracking Number", "Weight in KG"]]
        .dropna(subset=["LSC Tracking Number"])
        .drop_duplicates(subset=["LSC Tracking Number"], keep="first")
        .set_index("LSC Tracking Number")["Weight in KG"].to_dict())
else:
    weight_lookup = {}

combined_df["Weight in KG"] = combined_df["LSC Tracking Number"].map(weight_lookup)
container_weight_lookup = container_df.set_index("Container type")["Max Weight"].to_dict()
combined_df["Smaller_Weight"] = combined_df[["WEIGHT1", "WEIGHT2"]].min(axis=1)

def calculate_weight(row):
    current_weight = row.get("Weight in KG")
    if pd.notna(current_weight) and current_weight != "":
        return current_weight
    weight_value = row.get("Smaller_Weight")
    container_type = row.get("Container Type")
    max_weight = container_weight_lookup.get(container_type)
    if pd.isna(weight_value) or pd.isna(max_weight):
        return None
    weight_kg = weight_value * 0.45359237
    return weight_kg if weight_kg <= max_weight else None

combined_df.loc[combined_df["Weight in KG"].isna(), "Weight in KG"] = combined_df.apply(calculate_weight, axis=1)
combined_df.drop(columns=["Smaller_Weight"], inplace=True, errors="ignore")

# ── CBM and Weight from CSP ──────────────────────────────────────────
combined_df["CBM"] = combined_df["CBM"].replace("", pd.NA)
if "Shipment Number (Hwb)" in replicate_csp.columns and "Cubic Meters" in replicate_csp.columns:
    lookup_cbm_csp = (replicate_csp[["Shipment Number (Hwb)", "Cubic Meters"]]
        .dropna(subset=["Shipment Number (Hwb)"])
        .drop_duplicates(subset=["Shipment Number (Hwb)"], keep="first")
        .set_index("Shipment Number (Hwb)")["Cubic Meters"].to_dict())
else:
    lookup_cbm_csp = {}

combined_df["CBM"] = combined_df["CBM"].fillna(combined_df["HBOL"].map(lookup_cbm_csp))
combined_df["CBM"] = combined_df["CBM"].replace("", pd.NA)

combined_df["Weight in KG"] = combined_df["Weight in KG"].replace("", pd.NA)
if "Shipment Number (Hwb)" in replicate_csp.columns and "Actual Wt Kgs" in replicate_csp.columns:
    lookup_weight_csp = (replicate_csp[["Shipment Number (Hwb)", "Actual Wt Kgs"]]
        .dropna(subset=["Shipment Number (Hwb)"])
        .drop_duplicates(subset=["Shipment Number (Hwb)"], keep="first")
        .set_index("Shipment Number (Hwb)")["Actual Wt Kgs"].to_dict())
else:
    lookup_weight_csp = {}

combined_df["Weight in KG"] = combined_df["Weight in KG"].fillna(combined_df["HBOL"].map(lookup_weight_csp))
combined_df["Weight in KG"] = combined_df["Weight in KG"].replace("", pd.NA)

# ── Lane ID ──────────────────────────────────────────────────────────
if "LSC Tracking Number" in replicate_yesterday.columns and "OCEAN or AIR LANE ID" in replicate_yesterday.columns:
    lookup_laneid_yesterday = (replicate_yesterday[["LSC Tracking Number", "OCEAN or AIR LANE ID"]]
        .dropna(subset=["LSC Tracking Number"])
        .drop_duplicates(subset=["LSC Tracking Number"], keep="first")
        .set_index("LSC Tracking Number")["OCEAN or AIR LANE ID"].to_dict())
else:
    lookup_laneid_yesterday = {}

combined_df["OCEAN or AIR LANE ID"] = combined_df["LSC Tracking Number"].map(lookup_laneid_yesterday)
combined_df["OCEAN or AIR LANE ID"] = combined_df["OCEAN or AIR LANE ID"].replace("", pd.NA)

if "STI#" in replicate_query3.columns and "MODIFIED LANE ID" in replicate_query3.columns:
    lookup_laneid_query3 = (replicate_query3[["STI#", "MODIFIED LANE ID"]]
        .dropna(subset=["STI#"])
        .drop_duplicates(subset=["STI#"], keep="first")
        .set_index("STI#")["MODIFIED LANE ID"].to_dict())
else:
    lookup_laneid_query3 = {}

combined_df["OCEAN or AIR LANE ID"] = combined_df["OCEAN or AIR LANE ID"].fillna(
    combined_df["LSC Tracking Number"].map(lookup_laneid_query3))
combined_df["OCEAN or AIR LANE ID"] = combined_df["OCEAN or AIR LANE ID"].replace("", pd.NA)

if "Shipment Number (Hwb)" in replicate_csp.columns and "Extracted_LaneID" in replicate_csp.columns:
    lookup_laneid_csp = (replicate_csp[["Shipment Number (Hwb)", "Extracted_LaneID"]]
        .dropna(subset=["Shipment Number (Hwb)"])
        .drop_duplicates(subset=["Shipment Number (Hwb)"], keep="first")
        .set_index("Shipment Number (Hwb)")["Extracted_LaneID"].to_dict())
else:
    lookup_laneid_csp = {}

combined_df["OCEAN or AIR LANE ID"] = combined_df["OCEAN or AIR LANE ID"].fillna(
    combined_df["HBOL"].map(lookup_laneid_csp))
combined_df["OCEAN or AIR LANE ID"] = combined_df["OCEAN or AIR LANE ID"].replace("", pd.NA)

# ── MBL from CSP ─────────────────────────────────────────────────────
if "Shipment Number (Hwb)" in replicate_csp.columns and "Last MB Number" in replicate_csp.columns:
    lookup_mbl_csp = (replicate_csp[["Shipment Number (Hwb)", "Last MB Number"]]
        .dropna(subset=["Shipment Number (Hwb)"])
        .drop_duplicates(subset=["Shipment Number (Hwb)"], keep="first")
        .set_index("Shipment Number (Hwb)")["Last MB Number"].to_dict())
else:
    lookup_mbl_csp = {}

combined_df["MBOL"] = combined_df["MBOL"].fillna(combined_df["HBOL"].map(lookup_mbl_csp))
combined_df["MBOL"] = combined_df["MBOL"].replace("", pd.NA)

# ── Origin Consol name ───────────────────────────────────────────────
origin_consol_table = pd.DataFrame({
    "Origin Consol DUNS": [528177112, 544931926, 543129368, 687767889],
    "Origin Consol": [
        "CEVA Logistics - Shenzhen CC",
        "CEVA Logistics - Shanghai CC",
        "CEVA Logistics - Tianjin Xingang CC",
        "CEVA Logistics - Busan CC"
    ]
})
lookup_consolname = origin_consol_table.set_index("Origin Consol DUNS")["Origin Consol"].to_dict()
combined_df["Origin Consol"] = combined_df["Origin Consol DUNS"].map(lookup_consolname)

# ── 12-stage shipment status waterfall ──────────────────────────────
def get_status(row):
    supplier     = row["Ship Date from Supplier"]
    departed_cfs = row["Departed Consol Actual Date/Time"]
    arrived_pol  = row["Actual Date of arrival to the origin port "]
    departed_pol = row["Actual Date Of Departure From Origin Port"]
    arrived_pod  = row["Actual Date of Arrival To Destination Port"]
    outgate_pod  = row["Actual Outgate Date From Destination Port"]
    arrived_rail = row["Actual Arrival Date To Destination Rail Yard"]
    departed_rail= row["Actual Departure from Dest Rail"]
    delivered    = row["Actual Arrival to Final Destination"]

    if pd.notna(delivered):                                                          return "12. Delivered"
    if pd.notna(departed_rail) and pd.isna(delivered):                              return "11. Outgate Destination Rail"
    if pd.notna(arrived_rail) and pd.isna(departed_rail):                           return "10. Arrived Destination Rail"
    if pd.notna(outgate_pod) and pd.isna(arrived_rail):                             return "9. Outgate POD"
    if pd.notna(arrived_pod) and pd.isna(outgate_pod) and pd.isna(arrived_rail):   return "7. Arrived POD"
    if pd.notna(departed_pol) and pd.isna(arrived_pod):                             return "6. Departed POL"
    if pd.notna(arrived_pol) and pd.isna(departed_pol):                             return "5. Arrived POL"
    if (pd.notna(departed_cfs) and pd.isna(arrived_pol) and pd.isna(departed_pol)
            and pd.isna(arrived_pod) and pd.isna(outgate_pod)
            and pd.isna(arrived_rail) and pd.isna(departed_rail)):                  return "4. Outgate CFS"
    if pd.notna(supplier) and all(pd.isna(row[col]) for col in [
        "Departed Consol Actual Date/Time",
        "Actual Date of arrival to the origin port ",
        "Actual Date Of Departure From Origin Port",
        "Actual Date of Arrival To Destination Port",
        "Actual Outgate Date From Destination Port",
        "Actual Arrival Date To Destination Rail Yard",
        "Actual Departure from Dest Rail",
        "Actual Arrival to Final Destination"
    ]):                                                                              return "2. Departed Supplier"
    return np.nan

combined_df["Status of Container"] = combined_df.apply(get_status, axis=1)

# ── Save output ──────────────────────────────────────────────────────
combined_df.to_excel(output_path, index=False)
print("✅ Columns populated and file saved successfully to:", output_path)
