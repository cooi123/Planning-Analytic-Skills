# TI data sources and external systems

How a TurboIntegrator process gets data in: the source types, how each is defined
in the PAW process editor, how TM1 v11 and v12 differ, and how to bring in SAP,
Cognos and other external systems.

## 1. Source types in the PAW process editor

Open the process, then **Data Source** tab → **Data source** menu:

| PAW choice | TI type (`DataSourceType`) | Use |
|---|---|---|
| **File** | `CHARACTERDELIMITED` | A delimited text file |
| **Location** | (file path or URL) | A file on a path (v11) or a URL (v12) |
| **Database connection** | `ODBC` | A SQL query against a database |
| **Cube** (view) | `VIEW` | Cells of a TM1 cube view |
| **Dimension set** | `SUBSET` | Elements of a set |
| (none) | `NULL` | Prolog and Epilog only |

Every type ends the same way: **Preview** → **Set variables** (names and types)
→ **Save**. Variable names may contain letters, numbers and underscores, and must
start with a letter. Check every type the editor guessed, especially numbers
stored as text.

### File

**Data source → File**, then pick the file from the **File** menu, or use
**Upload file** to add it.

- Delimited text with any extension.
- **Not** Excel (`.xls`/`.xlsx`), and **not** fixed-width text. Save Excel as CSV
  first.
- The editor detects the delimiter, quote character, decimal and thousands
  separators, and header rows. Confirm them in **Preview**. A wrong decimal
  separator silently scales every number.

### Location

**Data source → Location**, then give a path or URL:

| Deployment | What a location can be |
|---|---|
| PA on Cloud / PA Local (v11) | A path relative to the data directory (`./data_sources/file.txt`), or the shared `s:/` directory on PA on Cloud |
| PA Local only | A mapped drive, local drive or UNC path the TM1 service account can read |
| TM1 12 (PA as a Service, Cloud Pak for Data) | An **HTTP or HTTPS URL**. If it needs authentication, call `ExecuteHttpRequest` in the Prolog |

On v12, a Location is how a process reads a file published by another system:
object storage, a REST export, an OData feed.

### Database connection (ODBC)

**Data source → Database connection**, then:

1. Enter a **Username** and **Password** if the database needs them. The user
   enters these in PAW; never put them in the script or in chat.
2. Enter the **Database connection query** (SQL in the database's own dialect).
3. **Preview** → **Set variables** → **Save**.

**v11 (PA Local, older PA on Cloud).** TM1 calls an ODBC driver and DSN installed
on the TM1 server. `DatasourceNameForServer` is the DSN name.

**v12 (PA as a Service).** The cloud engine has no local drivers. Install the
**Planning Analytics ODBC Data Connector** (ODBCIS) on a machine that can reach the
database and has the driver and DSN. It publishes the DSN as an OData REST service.

- The process's data source name becomes the connector URL:
  `http://<id>:<secret>@<host>:<port>/api/v1/DataSources('<DSN>')`.
  The process's username and password are reused as the connector's id and
  secret.
- The connector is configured in `config.internal.json` in its `deployment`
  directory (gateway host and port).
- On older PA on Cloud, the IBM Secure Gateway did this job.

### Cube view

**Data source → Cube**. Choose **Cube** or **Control cube**, then the **Cube**, then
the **View**, then **Preview** → **Set variables** → **Save**.

Native views become MDX views when opened in PAW. For loads, prefer a temporary
MDX view built in Prolog over a saved view. A saved view can be changed by someone
else, and concurrent runs collide on it (`TI-004`):

```
# Prolog
sView = '}tmp_' | GetProcessName() | '_' | TIMST( NOW, '\Y\m\d\h\i\s' );
ViewCreateByMDX( pSourceCube, sView,
  'SELECT NON EMPTY {TM1FILTERBYLEVEL({TM1SUBSETALL([Product].[Product])}, 0)} ON 0 ' |
  'FROM [' | pSourceCube | '] WHERE ([Version].[Version].[' | pVersion | '])', 1 );
DataSourceType          = 'VIEW';
DatasourceNameForServer = pSourceCube;
DatasourceCubeview      = sView;
```

`NON EMPTY` skips empty cells. Restricting the sets to leaf level skips
consolidations, so the copy doesn't double count.

## 2. Load templates

### File into a cube, re-runnable

```
# Prolog
IF( CubeExists( pCube ) = 0 );
  LogOutput( 'ERROR', 'Cube not found: ' | pCube );
  ProcessError;
ENDIF;
nRead = 0; nWritten = 0; nRejected = 0;

# clear only the slice this load owns
sClear = '}tmp_clear_' | GetProcessName();
ViewCreateByMDX( pCube, sClear,
  'SELECT {TM1FILTERBYLEVEL({TM1SUBSETALL([Period].[Period])}, 0)} ON 0 FROM [' | pCube |
  '] WHERE ([Version].[Version].[' | pVersion | '])', 1 );
ViewZeroOut( pCube, sClear );

# Metadata
IF( DimensionElementExists( 'Product', vProduct ) = 0 );
  DimensionElementInsert( 'Product', '', vProduct, 'N' );
ENDIF;

# Data
nRead = nRead + 1;
IF( CellIsUpdateable( pCube, pVersion, vPeriod, vProduct, 'Units' ) = 0 );
  nRejected = nRejected + 1;
  ItemReject( 'Not updateable: ' | vPeriod | ' / ' | vProduct );
ENDIF;
CellPutN( vUnits, pCube, pVersion, vPeriod, vProduct, 'Units' );
nWritten = nWritten + 1;

# Epilog
LogOutput( 'INFO', GetProcessName() | ': read ' | NumberToString( nRead ) |
  ', written ' | NumberToString( nWritten ) | ', rejected ' | NumberToString( nRejected ) );
```

- **Name every dimension in the clear view.** `ViewZeroOut` clears the leaf cells
  under the view's elements. A dimension left to its default member clears
  whatever that member covers, often the whole dimension. The example clears one
  version, every period and everything else. Narrow it to what the load owns.
- `ItemReject` ends processing of the current record, so the `CellPutN` after it
  doesn't run for rejected rows.
- Check each function against your TM1 version's TI reference before relying on
  it. Function availability differs between v11 and v12.

### Database query, with the source set in code

```
# Prolog
DataSourceType          = 'ODBC';
DatasourceNameForServer = pDSN;        # v11: DSN name. v12: ODBC Data Connector URL
DatasourceQuery         = 'SELECT period, product, units FROM sales WHERE fiscal_year = ' | pYear;
```

`ODBCOpen`, `ODBCOutput` and `ODBCClose` write back to a database from Data or
Epilog.

## 3. External systems

| System | Route | Notes |
|---|---|---|
| **SAP** (BW, BW/4HANA, ECC, S/4HANA, HANA) | **IBM Planning Analytics Connector for SAP** | A standalone program that reads SAP OData services and pushes data straight into cubes, in both directions, without flat files. IBM's current recommendation |
| SAP HANA tables | ODBC with the HANA driver | A plain relational read, when the data is in HANA tables or views |
| SAP BW (alternative) | IBM Cognos Integration Server | A separate product for extracting from cube-style sources into TM1 |
| SAP (legacy) | TM1 Package Connector | **Deprecated since PA 2.0.8.** Don't start new work on it |
| **Cognos Analytics** | ODBC to the **database behind** the Cognos model | TI can't read Cognos reports or data modules |
| Cognos Analytics, no database access | A scheduled report to CSV, then a File or Location source | Works, but column changes break the load. Agree a fixed layout |
| Data warehouses (SQL Server, Oracle, Snowflake, Postgres, Db2) | ODBC | v12: through the ODBC Data Connector |
| ETL / iPaaS (Informatica, Azure Data Factory and others) | The tool writes into cubes through the **TM1 REST API** | No TI source on the TM1 side. Keep a TI process for clearing and validation |
| Files from any system | File, or Location | The universal fallback |
| REST / OData endpoints (v12) | Location with a URL, plus `ExecuteHttpRequest` for authentication | Simple pulls without middleware |

Cognos Analytics and PA usually connect **the other way round**: Cognos reports on
PA cubes through a data server connection and data modules. If the requirement is
reporting, that's simpler than copying data into TM1.

### Choosing

1. If the data is in a database TM1 can reach, use **ODBC**. It's re-runnable and
   parameterised, with no file handoffs.
2. If it's SAP and you have the connector, use the **SAP connector**.
3. If an ETL platform already owns the data movement, have it **push through
   REST**.
4. Otherwise use a **file**, with an agreed fixed layout and a header row.

## 4. Security

- Database and system credentials are entered by the user in the PAW data source
  or connection, or held by the connector. They don't belong in process code.
- The ODBC Data Connector URL can carry an id and secret. Treat a process
  containing one as a secret.
- A process runs with the rights of whoever runs it, or of the chore's account.
  Scheduled loads should run under a dedicated least-privilege account.

## Sources

- IBM, PAW process editor:
  [Define a data source](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=processes-define-data-source),
  [File](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=source-define-file-data),
  [Location](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=source-define-location-data),
  [Database connection](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=source-define-database-connection-data),
  [Cube view](https://www.ibm.com/docs/en/planning-analytics/2.0.0?topic=source-define-cube-view-data).
- IBM, ODBC Data Connector:
  [Importing data in TM1 12](https://www.ibm.com/docs/en/planning-analytics/3.1.0?topic=upaodc-importing-data-tm1-12-planning-analytics-odbc-data-connector),
  [Download](https://www.ibm.com/support/pages/download-ibm-planning-analytics-engine-data-connector).
- IBM, SAP:
  [Planning Analytics support for SAP as a data source](https://www.ibm.com/support/pages/planning-analytics-support-sap-data-source),
  [Download the PA Connector for SAP](https://www.ibm.com/support/pages/download-ibm-planning-analytics-connector-sap-1010).
- IBM, [Cognos Integration Server](https://ibm.com/products/cognos-integration-server).
