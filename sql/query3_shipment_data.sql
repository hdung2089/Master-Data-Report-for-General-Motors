-- ============================================================
-- query3_shipment_data.sql
-- ============================================================
-- Extracts shipment master data from the Infor Nexus TMS
-- (EM = Event Management module).
--
-- Output is used as the "Query 3" input tab in Replicate_file.xlsx
-- which feeds the Python ETL pipeline (pipeline/etl_pipeline.py).
--
-- Key fields extracted:
--   STI#, container ID/type, HBL, MBL, SCAC, vessel name,
--   lane ID, origin/dest DUNS, CBM, weight, PRN, SO#
-- ============================================================

SELECT DISTINCT
    ES.EM_SHIPMENT_ID                           AS [STI#],
    ES.SHIPMENT_ID_NUMBER,
    ES.SHIPMENT_PIECES                          AS [NUMBER OF PACKAGES],
    ES.ULTIMATE_ORIGIN_ALIAS                    AS [ORIGIN DUN],
    ES.ULTIMATE_DEST_ALIAS                      AS [DEST DUN],
    ES.SHIPMENT_PIECES                          AS [NUMBER OF PACKAGES],
    E1.REFERENCE_NUMBER                         AS [MODE],
    E2.REFERENCE_NUMBER                         AS [CCA LOCATION],
    E3.REFERENCE_NUMBER                         AS [PRN#],
    E4.REFERENCE_NUMBER                         AS [SO#],
    U.REFERENCE_NUMBER                          AS [HBL],
    U2.REFERENCE_NUMBER                         AS [MBL],
    C.CONVEYANCE_ID_NUMBER                      AS [CONT ID],
    C.CONVEYANCE_TYPE_DESC                      AS [CONT TYPE],
    S.REFERENCE_NUMBER                          AS [LANE ID],
    ES.SHIPMENT_CUBE                            AS [VOL1],
    ES.SHIPMENT_WEIGHT                          AS [WEIGHT1],
    C.CONVEYANCE_CUBE                           AS [VOL2],
    C.CONVEYANCE_WEIGHT                         AS [WEIGHT2],
    OP.PACKAGE_ID_NUMBER                        AS [PACKAGING TYPE],
    L.LOCATION_ALIAS                            AS [CONSOL DUN]

FROM EM_SHIPMENT ES

-- Reference type joins for shipment-level attributes
LEFT JOIN EM_SHIPMENT_REFERENCE_LISTITEM_VIEW E1
    ON E1.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID
    AND E1.REFERENCE_TYPE_ID = 100033          -- Mode of transport

LEFT JOIN EM_SHIPMENT_REFERENCE_LISTITEM_VIEW E2
    ON E2.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID
    AND E2.REFERENCE_TYPE_ID = 100265          -- CCA location

LEFT JOIN EM_SHIPMENT_REFERENCE_LISTITEM_VIEW E3
    ON E3.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID
    AND E3.REFERENCE_TYPE_ID = 100318          -- PRN#

LEFT JOIN EM_SHIPMENT_REFERENCE_LISTITEM_VIEW E4
    ON E4.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID
    AND E4.REFERENCE_TYPE_ID = 100742          -- SO#

-- Operational milestone join (links shipment to master unitload)
LEFT JOIN EM_SHIPMENT_OPERATIONAL_MILESTONE E5
    ON E5.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID

-- HBL (House Bill of Lading)
LEFT JOIN MASTER_UL_REFERENCE_VIEW U
    ON U.MASTER_UNITLOAD_ID = E5.MASTER_UNITLOAD_ID
    AND U.REFERENCE_TYPE_ID = 100352

-- MBL (Master Bill of Lading) — priority waterfall: 100000 > 100006 > 100183
LEFT JOIN (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY MASTER_UNITLOAD_ID
               ORDER BY
                   CASE
                       WHEN REFERENCE_TYPE_ID = 100000 THEN 1
                       WHEN REFERENCE_TYPE_ID = 100006 THEN 2
                       WHEN REFERENCE_TYPE_ID = 100183 THEN 3
                       ELSE 4
                   END
           ) AS rn
    FROM MASTER_UL_REFERENCE_VIEW
    WHERE REFERENCE_TYPE_ID IN (100000, 100006, 100183)
) U2
    ON U2.MASTER_UNITLOAD_ID = E5.MASTER_UNITLOAD_ID
    AND U2.rn = 1

-- Container attributes
LEFT JOIN MASTER_UNITLOAD_CONTAINER_ASSN_VIEW V
    ON V.MASTER_UNITLOAD_ID = E5.MASTER_UNITLOAD_ID

LEFT JOIN CONTAINER_ATTRIBUTES C
    ON C.CONTAINER_ATTRIBUTES_ID = V.CONTAINER_ATTRIBUTES_ID

-- Lane ID from shipment status document
LEFT JOIN SHIPMENT_STATUS_DOC T
    ON T.MASTER_UNITLOAD_ID = E5.MASTER_UNITLOAD_ID

LEFT JOIN SHIPMENT_STATUS_DOC_REFERENCE_VIEW S
    ON S.STATUS_DOC_ID = T.STATUS_DOC_ID
    AND S.REFERENCE_TYPE_ID = 100794

-- Order-level packaging
LEFT JOIN EM_SHIPMENT_ORDERS_ASSN E6
    ON E6.EM_SHIPMENT_ID = ES.EM_SHIPMENT_ID

LEFT JOIN ORDER_PACKAGE OP
    ON OP.ORDER_ID = E6.ORDER_ID

-- Consol DUNS — filter to known CEVA consolidation locations only
LEFT JOIN LOCATION_ENTITY_LISTITEM_VIEW L
    ON L.ENTITY_ID = E5.LOCATION_ENTITY_ID
    AND E5.OPERATIONAL_MILESTONE_TYPE_ID = 100001
    AND L.LOCATION_ALIAS IN (
        '528177112',   -- CEVA Shenzhen CC
        '544931926',   -- CEVA Shanghai CC
        '543129368',   -- CEVA Tianjin Xingang CC
        '687767889'    -- CEVA Busan CC
    )

-- Active intransit shipments only
WHERE ES.CURRENT_STATE_TYPE_ID = 100000
  AND ES.EM_SHIPMENT_ID IN (
      -- Paste current STI# list here, or join to a staging table
  )
