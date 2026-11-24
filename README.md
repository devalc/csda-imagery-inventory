# Reusable NASA CSDA metadata inventory workflow

Python scripts and Jupyter notebooks for searching NASA Commercial SmallSat Data Acquisition (CSDA) catalog metadata by area of interest (AOI) and date range. The event-window workflow identifies imagery records within, before, and after user-defined periods.

## Catalog search and account access

The inventory queries the public CSDA STAC catalog and separately records vendor entitlements from the authenticated CSDA account. Catalog results describe the records returned for the selected collections, AOI, and dates. Zero results indicate that the query returned no matching records.

The workflow covers catalog discovery and account reporting. Asset downloads, archive requests, orders, and satellite tasking are outside its scope.

## Repository layout

```text
.
├── aoi/                         # Your GeoJSON boundaries
├── config/
│   ├── areas.example.json       # AOIs, inventory dates, collection choices
│   └── event_windows.example.json
├── notebooks/
│   ├── 01_csda_inventory.ipynb
│   └── 02_event_windows.ipynb
├── scripts/
│   ├── csda_common.py           # Shared safe metadata helpers
│   ├── setup_credentials.py     # Hidden password prompt; writes .env mode 600
│   ├── test_auth.py             # Minimal authenticated verification
│   ├── inventory.py             # Paginated AOI catalog inventory
│   └── event_windows.py         # Pre/during/post-event filtering and ranking
├── .env.example
├── .gitignore
├── requirements-notebooks.txt
└── requirements.txt
```

## First-time setup on a new device

1. Install **Python 3.12 or newer** and **Git**. The install command uses Git to fetch NASA's CSDA client, including when you downloaded this repository as a ZIP.
2. Clone the repository or download and extract the whole ZIP. Open a terminal in the folder that contains this README and the requirements files.
3. Create a virtual environment and run the install command for your workflow. The notebook requirements include the script dependencies.

### macOS and Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt             # Scripts only
# python -m pip install -r requirements-notebooks.txt # Jupyter or VS Code notebooks
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt             # Scripts only
# .\.venv\Scripts\python.exe -m pip install -r requirements-notebooks.txt # Jupyter or VS Code notebooks
```

For notebook use, run the notebook install line without the leading `#` in place of the scripts-only line. Installation is a one-time step per environment. On macOS and Linux, reactivate `.venv` when you open a new terminal. On Windows, use `.\.venv\Scripts\python.exe` wherever the terminal instructions below say `python`.

## Secure authentication

Use your own Earthdata login with CSDA access for a live inventory. Never commit `.env`.

```bash
python scripts/setup_credentials.py
python scripts/test_auth.py
```

The password prompt is hidden. The test prints only sanitized status information.

## Run in Jupyter or VS Code

Use the `.venv` where you installed `requirements-notebooks.txt`.

In VS Code, install the Python and Jupyter extensions and open the repository folder.
Open a notebook, click **Select Kernel**, and choose the repository's `.venv` under
**Python Environments**. For JupyterLab, run `python -m jupyterlab` from the repository folder.

Set up Earthdata credentials in the terminal and prepare the JSON configs as described below.
Run [01_csda_inventory.ipynb](notebooks/01_csda_inventory.ipynb) first, then
[02_event_windows.ipynb](notebooks/02_event_windows.ipynb). Both use the same configs
and output files as the command-line tools. If you change the inventory output folder
in the first notebook, set the same folder in the second. The event-window notebook
can run offline once the inventory has been saved.

## Configure an AOI inventory

Copy the example files:

```bash
cp config/areas.example.json config/areas.json
cp config/event_windows.example.json config/event_windows.json
```

In Windows PowerShell:

```powershell
Copy-Item config/areas.example.json config/areas.json
Copy-Item config/event_windows.example.json config/event_windows.json
```

Place a longitude/latitude GeoJSON file in `aoi/`, then edit `config/areas.json`:

```json
{
  "as_of": "2026-08-20T23:59:59Z",
  "search_start": "2000-01-01T00:00:00Z",
  "max_items_per_collection": 5000,
  "collections": ["planet", "satellogic", "blacksky", "maxar-legion"],
  "areas": [
    {
      "id": "example_watershed",
      "name": "Example watershed",
      "geojson": "aoi/example_watershed.geojson"
    }
  ]
}
```

Set `collections` to `null` to query all collections advertised by the CSDA STAC endpoint. The `max_items_per_collection` setting limits the number of records retrieved per collection. The pagination audit records truncated searches.

Run the inventory:

```bash
python scripts/inventory.py --config config/areas.json
```

For each AOI, the script writes:

- `outputs/<area_id>/inventory.csv`
- `outputs/<area_id>/summary.json`
- `outputs/<area_id>/pagination_audit.json`

It also writes `outputs/account_access_summary.json`, with sensitive fields removed.

## Configure event-date analysis

Edit `config/event_windows.json` after the inventory is complete:

```json
{
  "imagery_collections": ["planet", "satellogic", "blacksky", "maxar-legion"],
  "areas": {
    "example_watershed": [
      {
        "name": "pre_fire",
        "start": "2026-06-16",
        "end": "2026-07-15",
        "description": "Clear baseline before ignition"
      },
      {
        "name": "during_and_after",
        "start": "2026-07-16",
        "end": "2026-08-20",
        "description": "Active-fire and initial response period"
      }
    ]
  }
}
```

Run:

```bash
python scripts/event_windows.py --config config/event_windows.json
```

This creates:

- `outputs/event_window_summary.csv`
- `outputs/event_window_candidates.csv`

Candidate rows are labeled `in_window`, `nearest_before`, or `nearest_after`. In-window rows are ranked using reported cloud cover, AOI coverage, and recency.

## Known limitations

- STAC requests use bounding boxes. The workflow then checks intersection with the AOI geometry locally.
- Metadata field conventions vary by vendor and collection.
- Cloud percentage and GSD are included only when the item exposes them.
- EarthDEM products derived from WorldView imagery are elevation products.
