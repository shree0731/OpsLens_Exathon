# OpsLens — Exasol Data & System Discovery Report

**Discovery Run Date:** `2026-10-31T20:27:47.476169`  
**Target Exasol DSN:** `127.0.0.1:8563`  
**User Account:** `sys`  

---

## 1. Discovered Schemas in Database

| Schema Name | Schema Owner |
| :--- | :--- |
| `ENERGY` | `SYS` |
| `SCHED` | `SCHEDULER_SVC` |
| `STARTER_KIT` | `SYS` |
| `TPCH` | `SYS` |
| `WEATHER` | `SYS` |

---

## 2. Sample Target Tables Discovery

Per project rules, schemas `ENERGY`, `SCHED`, `WEATHER`, and `TPCH` are immutable reference datasets.

### Table: `SCHED.SCHED_TASKS`

- **Row Count:** `0`
- **Total Columns:** `8`

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`TASK_ID`** | `VARCHAR(128) UTF8` | False |
| 2 | **`ENABLED`** | `BOOLEAN` | True |
| 3 | **`SCHEDULE`** | `VARCHAR(512) UTF8` | True |
| 4 | **`SQL_TEXT`** | `VARCHAR(2000000) UTF8` | False |
| 5 | **`AFTER`** | `VARCHAR(128) UTF8` | True |
| 6 | **`IS_FINAL`** | `BOOLEAN` | True |
| 7 | **`PARALLEL_CHILDREN`** | `BOOLEAN` | True |
| 8 | **`COMMENT`** | `VARCHAR(2000) UTF8` | True |

---

### Table: `SCHED.SCHED_HISTORY`

- **Row Count:** `0`
- **Total Columns:** `9`

**Date/Timestamp Ranges:**
| Column | Min Value | Max Value |
| :--- | :--- | :--- |
| `SCHEDULED_FOR` | `None` | `None` |
| `STARTED_AT` | `None` | `None` |
| `FINISHED_AT` | `None` | `None` |

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`RUN_ID`** | `VARCHAR(36) UTF8` | False |
| 2 | **`GRAPH_RUN_ID`** | `VARCHAR(36) UTF8` | True |
| 3 | **`TASK_ID`** | `VARCHAR(128) UTF8` | False |
| 4 | **`GRAPH_PHASE`** | `VARCHAR(16) UTF8` | False |
| 5 | **`SCHEDULED_FOR`** | `TIMESTAMP(3)` | True |
| 6 | **`STARTED_AT`** | `TIMESTAMP(3)` | False |
| 7 | **`FINISHED_AT`** | `TIMESTAMP(3)` | True |
| 8 | **`STATUS`** | `VARCHAR(16) UTF8` | False |
| 9 | **`ERROR_MESSAGE`** | `VARCHAR(2000000) UTF8` | True |

---

### Table: `ENERGY.ENERGY_READINGS`

- **Row Count:** `108,000`
- **Total Columns:** `3`

**Date/Timestamp Ranges:**
| Column | Min Value | Max Value |
| :--- | :--- | :--- |
| `READING_TS` | `2025-01-01 00:00:00.000000` | `2025-03-31 23:00:00.000000` |

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`METER_ID`** | `DECIMAL(9,0)` | False |
| 2 | **`READING_TS`** | `TIMESTAMP(3)` | False |
| 3 | **`KWH`** | `DECIMAL(8,3)` | False |

---

### Table: `ENERGY.ENERGY_METERS`

- **Row Count:** `50`
- **Total Columns:** `5`

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`METER_ID`** | `DECIMAL(9,0)` | False |
| 2 | **`HOUSEHOLD`** | `VARCHAR(25) UTF8` | False |
| 3 | **`CITY`** | `VARCHAR(25) UTF8` | False |
| 4 | **`TARIFF`** | `VARCHAR(10) UTF8` | False |
| 5 | **`BASE_LOAD_KWH`** | `DECIMAL(6,3)` | False |

---

### Table: `WEATHER.WEATHER_DAILY`

- **Row Count:** `10,960`
- **Total Columns:** `7`

**Date/Timestamp Ranges:**
| Column | Min Value | Max Value |
| :--- | :--- | :--- |
| `W_DATE` | `2023-01-01` | `2025-12-31` |

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`CITY_ID`** | `DECIMAL(9,0)` | False |
| 2 | **`W_DATE`** | `DATE` | False |
| 3 | **`TEMP_AVG_C`** | `DECIMAL(5,1)` | False |
| 4 | **`TEMP_MIN_C`** | `DECIMAL(5,1)` | False |
| 5 | **`TEMP_MAX_C`** | `DECIMAL(5,1)` | False |
| 6 | **`PRECIP_MM`** | `DECIMAL(6,1)` | False |
| 7 | **`WIND_KMH`** | `DECIMAL(5,1)` | False |

---

### Table: `TPCH.ORDERS`

- **Row Count:** `30,000`
- **Total Columns:** `9`

**Date/Timestamp Ranges:**
| Column | Min Value | Max Value |
| :--- | :--- | :--- |
| `O_ORDERDATE` | `1992-01-01` | `1998-08-02` |

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`O_ORDERKEY`** | `DECIMAL(18,0)` | False |
| 2 | **`O_CUSTKEY`** | `DECIMAL(18,0)` | True |
| 3 | **`O_ORDERSTATUS`** | `CHAR(1) UTF8` | True |
| 4 | **`O_TOTALPRICE`** | `DECIMAL(15,2)` | True |
| 5 | **`O_ORDERDATE`** | `DATE` | True |
| 6 | **`O_ORDERPRIORITY`** | `VARCHAR(15) UTF8` | True |
| 7 | **`O_CLERK`** | `VARCHAR(15) UTF8` | True |
| 8 | **`O_SHIPPRIORITY`** | `DECIMAL(18,0)` | True |
| 9 | **`O_COMMENT`** | `VARCHAR(79) UTF8` | True |

---

### Table: `TPCH.LINEITEM`

- **Row Count:** `120,515`
- **Total Columns:** `16`

**Date/Timestamp Ranges:**
| Column | Min Value | Max Value |
| :--- | :--- | :--- |
| `L_SHIPDATE` | `1992-01-03` | `1998-11-29` |
| `L_COMMITDATE` | `1992-02-02` | `1998-10-29` |
| `L_RECEIPTDATE` | `1992-01-08` | `1998-12-25` |

**Columns & Data Types:**
| # | Column Name | Data Type | Nullable |
| :-: | :--- | :--- | :-: |
| 1 | **`L_ORDERKEY`** | `DECIMAL(18,0)` | False |
| 2 | **`L_PARTKEY`** | `DECIMAL(18,0)` | True |
| 3 | **`L_SUPPKEY`** | `DECIMAL(18,0)` | True |
| 4 | **`L_LINENUMBER`** | `DECIMAL(18,0)` | False |
| 5 | **`L_QUANTITY`** | `DECIMAL(15,2)` | True |
| 6 | **`L_EXTENDEDPRICE`** | `DECIMAL(15,2)` | True |
| 7 | **`L_DISCOUNT`** | `DECIMAL(15,2)` | True |
| 8 | **`L_TAX`** | `DECIMAL(15,2)` | True |
| 9 | **`L_RETURNFLAG`** | `CHAR(1) UTF8` | True |
| 10 | **`L_LINESTATUS`** | `CHAR(1) UTF8` | True |
| 11 | **`L_SHIPDATE`** | `DATE` | True |
| 12 | **`L_COMMITDATE`** | `DATE` | True |
| 13 | **`L_RECEIPTDATE`** | `DATE` | True |
| 14 | **`L_SHIPINSTRUCT`** | `VARCHAR(25) UTF8` | True |
| 15 | **`L_SHIPMODE`** | `VARCHAR(10) UTF8` | True |
| 16 | **`L_COMMENT`** | `VARCHAR(44) UTF8` | True |

---

## 3. System & Audit Views Queryability (Query History)

Evaluation of `EXA_*` audit and system views for operational intelligence, query telemetry, and performance tracking.

| System / Audit View | Queryable? | Columns Available | Status / Exact Error |
| :--- | :-: | :--- | :--- |
| `SYS.EXA_ALL_SESSIONS` | **YES** | 18 columns | Accessible |
| `SYS.EXA_USER_SESSIONS` | **YES** | 24 columns | Accessible |
| `SYS.EXA_DBA_SESSIONS` | **YES** | 24 columns | Accessible |
| `SYS.EXA_ALL_AUDIT_SQL` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_ALL_AUDIT_SQL not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_ALL_AUDIT_SQL LIMIT 1
)
 |
| `SYS.EXA_USER_AUDIT_SQL` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_USER_AUDIT_SQL not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_USER_AUDIT_SQL LIMIT 1
)
 |
| `SYS.EXA_DBA_AUDIT_SQL` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_DBA_AUDIT_SQL not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_DBA_AUDIT_SQL LIMIT 1
)
 |
| `SYS.EXA_ALL_AUDIT_SESSIONS` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_ALL_AUDIT_SESSIONS not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_ALL_AUDIT_SESSIONS LIMIT 1
)
 |
| `SYS.EXA_ALL_QUERIES` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_ALL_QUERIES not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_ALL_QUERIES LIMIT 1
)
 |
| `SYS.EXA_USER_QUERIES` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_USER_QUERIES not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_USER_QUERIES LIMIT 1
)
 |
| `SYS.EXA_DBA_QUERIES` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_DBA_QUERIES not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_DBA_QUERIES LIMIT 1
)
 |
| `SYS.EXA_ALL_STATEMENTS` | **NO** | - | Error: 
(
    message     =>  object SYS.EXA_ALL_STATEMENTS not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM SYS.EXA_ALL_STATEMENTS LIMIT 1
)
 |
| `EXA_STATISTICS.EXA_MONITORING_DAILY` | **NO** | - | Error: 
(
    message     =>  object EXA_STATISTICS.EXA_MONITORING_DAILY not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM EXA_STATISTICS.EXA_MONITORING_DAILY LIMIT 1
)
 |
| `EXA_STATISTICS.EXA_SQL_HOURLY` | **YES** | 47 columns | Accessible |
| `EXA_STATISTICS.EXA_SQL_DAILY` | **YES** | 47 columns | Accessible |
| `EXA_STATISTICS.EXA_USAGE_HOURLY` | **YES** | 7 columns | Accessible |
| `EXA_STATISTICS.EXA_USAGE_DAILY` | **YES** | 7 columns | Accessible |
| `EXA_STATISTICS.EXA_CLUSTER_HOURLY` | **NO** | - | Error: 
(
    message     =>  object EXA_STATISTICS.EXA_CLUSTER_HOURLY not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM EXA_STATISTICS.EXA_CLUSTER_HOURLY LIMIT 1
)
 |
| `EXA_STATISTICS.EXA_CLUSTER_DAILY` | **NO** | - | Error: 
(
    message     =>  object EXA_STATISTICS.EXA_CLUSTER_DAILY not found [line 1, column 15] (Session: 1880577715524665344)
    dsn         =>  127.0.0.1:8563
    user        =>  sys
    schema      =>  
    session_id  =>  1880577715524665344
    code        =>  42000
    query       =>  SELECT * FROM EXA_STATISTICS.EXA_CLUSTER_DAILY LIMIT 1
)
 |
| `SYS.EXA_ALL_SCHEMAS` | **YES** | 5 columns | Accessible |
| `SYS.EXA_ALL_TABLES` | **YES** | 10 columns | Accessible |
| `SYS.EXA_ALL_COLUMNS` | **YES** | 21 columns | Accessible |

---

### Detailed Column Sets for Queryable Audit Views

#### `SYS.EXA_ALL_SESSIONS`
`SESSION_ID`, `USER_NAME`, `STATUS`, `COMMAND_NAME`, `STMT_ID`, `DURATION`, `QUERY_TIMEOUT`, `ACTIVITY`, `TEMP_DB_RAM`, `PERSISTENT_DB_RAM`, `LOGIN_TIME`, `CLIENT`, `DRIVER`, `ENCRYPTED`, `CONSUMER_GROUP`, `NICE`, `RESOURCES`, `CLUSTER_NAME`

#### `SYS.EXA_USER_SESSIONS`
`SESSION_ID`, `USER_NAME`, `EFFECTIVE_USER`, `STATUS`, `COMMAND_NAME`, `STMT_ID`, `DURATION`, `QUERY_TIMEOUT`, `ACTIVITY`, `TEMP_DB_RAM`, `PERSISTENT_DB_RAM`, `LOGIN_TIME`, `CLIENT`, `DRIVER`, `ENCRYPTED`, `HOST`, `OS_USER`, `OS_NAME`, `SCOPE_SCHEMA`, `CONSUMER_GROUP`, `NICE`, `RESOURCES`, `CLUSTER_NAME`, `SQL_TEXT`

#### `SYS.EXA_DBA_SESSIONS`
`SESSION_ID`, `USER_NAME`, `EFFECTIVE_USER`, `STATUS`, `COMMAND_NAME`, `STMT_ID`, `DURATION`, `QUERY_TIMEOUT`, `ACTIVITY`, `TEMP_DB_RAM`, `PERSISTENT_DB_RAM`, `LOGIN_TIME`, `CLIENT`, `DRIVER`, `ENCRYPTED`, `HOST`, `OS_USER`, `OS_NAME`, `SCOPE_SCHEMA`, `CONSUMER_GROUP`, `NICE`, `RESOURCES`, `CLUSTER_NAME`, `SQL_TEXT`

#### `EXA_STATISTICS.EXA_SQL_HOURLY`
`CLUSTER_NAME`, `INTERVAL_START`, `COMMAND_NAME`, `COMMAND_CLASS`, `SUCCESS`, `COUNT`, `DURATION_AVG`, `DURATION_MAX`, `CPU_AVG`, `CPU_MAX`, `TEMP_DB_RAM_PEAK_AVG`, `TEMP_DB_RAM_PEAK_MAX`, `PERSISTENT_DB_RAM_PEAK_AVG`, `PERSISTENT_DB_RAM_PEAK_MAX`, `HDD_READ_AVG`, `HDD_READ_MAX`, `HDD_WRITE_AVG`, `HDD_WRITE_MAX`, `LOCAL_READ_SIZE_AVG`, `LOCAL_READ_SIZE_MAX`, `LOCAL_READ_DURATION_AVG`, `LOCAL_READ_DURATION_MAX`, `LOCAL_WRITE_SIZE_AVG`, `LOCAL_WRITE_SIZE_MAX`, `LOCAL_WRITE_DURATION_AVG`, `LOCAL_WRITE_DURATION_MAX`, `CACHE_READ_SIZE_AVG`, `CACHE_READ_SIZE_MAX`, `CACHE_READ_DURATION_AVG`, `CACHE_READ_DURATION_MAX`, `CACHE_WRITE_SIZE_AVG`, `CACHE_WRITE_SIZE_MAX`, `CACHE_WRITE_DURATION_AVG`, `CACHE_WRITE_DURATION_MAX`, `REMOTE_READ_SIZE_AVG`, `REMOTE_READ_SIZE_MAX`, `REMOTE_READ_DURATION_AVG`, `REMOTE_READ_DURATION_MAX`, `REMOTE_WRITE_SIZE_AVG`, `REMOTE_WRITE_SIZE_MAX`, `REMOTE_WRITE_DURATION_AVG`, `REMOTE_WRITE_DURATION_MAX`, `NET_AVG`, `NET_MAX`, `ROW_COUNT_AVG`, `ROW_COUNT_MAX`, `EXECUTION_MODE`

#### `EXA_STATISTICS.EXA_SQL_DAILY`
`CLUSTER_NAME`, `INTERVAL_START`, `COMMAND_NAME`, `COMMAND_CLASS`, `SUCCESS`, `COUNT`, `DURATION_AVG`, `DURATION_MAX`, `CPU_AVG`, `CPU_MAX`, `TEMP_DB_RAM_PEAK_AVG`, `TEMP_DB_RAM_PEAK_MAX`, `PERSISTENT_DB_RAM_PEAK_AVG`, `PERSISTENT_DB_RAM_PEAK_MAX`, `HDD_READ_AVG`, `HDD_READ_MAX`, `HDD_WRITE_AVG`, `HDD_WRITE_MAX`, `LOCAL_READ_SIZE_AVG`, `LOCAL_READ_SIZE_MAX`, `LOCAL_READ_DURATION_AVG`, `LOCAL_READ_DURATION_MAX`, `LOCAL_WRITE_SIZE_AVG`, `LOCAL_WRITE_SIZE_MAX`, `LOCAL_WRITE_DURATION_AVG`, `LOCAL_WRITE_DURATION_MAX`, `CACHE_READ_SIZE_AVG`, `CACHE_READ_SIZE_MAX`, `CACHE_READ_DURATION_AVG`, `CACHE_READ_DURATION_MAX`, `CACHE_WRITE_SIZE_AVG`, `CACHE_WRITE_SIZE_MAX`, `CACHE_WRITE_DURATION_AVG`, `CACHE_WRITE_DURATION_MAX`, `REMOTE_READ_SIZE_AVG`, `REMOTE_READ_SIZE_MAX`, `REMOTE_READ_DURATION_AVG`, `REMOTE_READ_DURATION_MAX`, `REMOTE_WRITE_SIZE_AVG`, `REMOTE_WRITE_SIZE_MAX`, `REMOTE_WRITE_DURATION_AVG`, `REMOTE_WRITE_DURATION_MAX`, `NET_AVG`, `NET_MAX`, `ROW_COUNT_AVG`, `ROW_COUNT_MAX`, `EXECUTION_MODE`

#### `EXA_STATISTICS.EXA_USAGE_HOURLY`
`CLUSTER_NAME`, `INTERVAL_START`, `USERS_AVG`, `USERS_MAX`, `QUERIES_AVG`, `QUERIES_MAX`, `IDLE`

#### `EXA_STATISTICS.EXA_USAGE_DAILY`
`CLUSTER_NAME`, `INTERVAL_START`, `USERS_AVG`, `USERS_MAX`, `QUERIES_AVG`, `QUERIES_MAX`, `IDLE`

#### `SYS.EXA_ALL_SCHEMAS`
`SCHEMA_NAME`, `SCHEMA_OWNER`, `SCHEMA_OBJECT_ID`, `SCHEMA_IS_VIRTUAL`, `SCHEMA_COMMENT`

#### `SYS.EXA_ALL_TABLES`
`TABLE_SCHEMA`, `TABLE_NAME`, `TABLE_OWNER`, `TABLE_OBJECT_ID`, `TABLE_IS_VIRTUAL`, `TABLE_HAS_DISTRIBUTION_KEY`, `TABLE_HAS_PARTITION_KEY`, `TABLE_ROW_COUNT`, `DELETE_PERCENTAGE`, `TABLE_COMMENT`

#### `SYS.EXA_ALL_COLUMNS`
`COLUMN_SCHEMA`, `COLUMN_TABLE`, `COLUMN_OBJECT_TYPE`, `COLUMN_NAME`, `COLUMN_TYPE`, `COLUMN_TYPE_ID`, `COLUMN_MAXSIZE`, `COLUMN_NUM_PREC`, `COLUMN_NUM_SCALE`, `COLUMN_ORDINAL_POSITION`, `COLUMN_IS_VIRTUAL`, `COLUMN_IS_NULLABLE`, `COLUMN_IS_ZONEMAPPED`, `COLUMN_IS_DISTRIBUTION_KEY`, `COLUMN_PARTITION_KEY_ORDINAL_POSITION`, `COLUMN_DEFAULT`, `COLUMN_IDENTITY`, `COLUMN_OWNER`, `COLUMN_OBJECT_ID`, `STATUS`, `COLUMN_COMMENT`
