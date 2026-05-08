import re
import pandas as pd
import pdfplumber
from pathlib import Path
import aiosqlite
import asyncio
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.chroma import get_pdf_collection
from app.tools.csv_tool import load_csvs

logger   = get_logger()
settings = get_settings()

CSV_TABLE_MAP = {
    "movies":               "movies",
    "viewers":              "viewers",
    "watch_activity":       "watch_activity",
    "reviews":              "reviews",
    "marketing_spend":      "marketing_spend",
    "regional_performance": "regional_performance",
}

# ── Sensitivity classifier ────────────────────────────────────────────────────
HIGH_PATTERNS = re.compile(
    r"\bconfidential\b|\binternal\s+only\b|\bdo\s+not\s+distribute\b|"
    r"\bexecutive\s+compensation\b|\bsalary\b|\bacquisition\s+cost\b|"
    r"\bebitda\b|\bprofit\s+margin\b|\bnet\s+loss\b|\bforecast\b",
    re.IGNORECASE
)

MEDIUM_PATTERNS = re.compile(
    r"\bcampaign\b|\bregional\b|\baudience\s+segment\b|\bconversion\b|"
    r"\bimpressions\b|\bspend\b|\bengagement\s+score\b|\bdemographic\b|"
    r"\bmarketing\b|\broas\b|\brevenue\b|\bbudget\b|\bquarterly\b|"
    r"\bperformance\b|\bfinancial\b|\bcost\b",
    re.IGNORECASE
)


def classify_sensitivity(text: str) -> str:
    """
    Classify a text chunk as low | medium | high sensitivity.
    - high:   financial details, executive reports, internal cost data
    - medium: campaign performance, regional breakdowns, audience segments
    - low:    general trends, public summaries, genre analysis
    """
    if HIGH_PATTERNS.search(text):
        return "high"
    if MEDIUM_PATTERNS.search(text):
        return "medium"
    return "low"


# ── CSV → SQLite ──────────────────────────────────────────────────────────────
async def ingest_csvs_to_sqlite():
    csv_dir = Path(settings.data_dir) / "csv"
    db_path = settings.sqlite_db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        for csv_name, table_name in CSV_TABLE_MAP.items():
            csv_path = csv_dir / f"{csv_name}.csv"
            if not csv_path.exists():
                logger.warning(f"ingest: CSV not found: {csv_path}")
                continue

            df = pd.read_csv(csv_path)
            await db.execute(f"DROP TABLE IF EXISTS {table_name}")
            await db.commit()

            col_defs = []
            for col, dtype in df.dtypes.items():
                if "int" in str(dtype):
                    sql_type = "INTEGER"
                elif "float" in str(dtype):
                    sql_type = "REAL"
                else:
                    sql_type = "TEXT"
                col_defs.append(f'"{col}" {sql_type}')

            create_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(col_defs)})'
            await db.execute(create_sql)
            await db.commit()

            cols_str     = ", ".join([f'"{c}"' for c in df.columns])
            placeholders = ", ".join(["?" for _ in df.columns])
            insert_sql   = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"

            batch_size = 500
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                rows  = [tuple(row) for _, row in batch.iterrows()]
                await db.executemany(insert_sql, rows)
            await db.commit()

            logger.info(f"ingest: loaded {csv_name} → {table_name} ({len(df)} rows)")

    load_csvs()
    logger.info("ingest: CSVs loaded into pandas cache")


# ── PDF → ChromaDB ────────────────────────────────────────────────────────────
def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words  = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks


def ingest_pdfs_to_chroma():
    pdf_dir    = Path(settings.data_dir) / "pdf"
    collection = get_pdf_collection()

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info("ingest: cleared existing PDF collection")

    doc_id       = 0
    sensitivity_counts = {"low": 0, "medium": 0, "high": 0}

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        source = pdf_path.stem
        logger.info(f"ingest: processing PDF: {source}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text or not text.strip():
                        continue

                    chunks = _chunk_text(text, chunk_size=400, overlap=40)
                    for chunk in chunks:
                        sensitivity = classify_sensitivity(chunk)
                        sensitivity_counts[sensitivity] += 1

                        collection.add(
                            documents=[chunk],
                            metadatas=[{
                                "source":      source,
                                "page":        str(page_num),
                                "file":        pdf_path.name,
                                "sensitivity": sensitivity,   # ← tagged here
                            }],
                            ids=[f"doc_{doc_id}"],
                        )
                        doc_id += 1

            logger.info(f"ingest: {source} → {doc_id} chunks total")

        except Exception as e:
            logger.error(f"ingest: failed to process {source}: {e}")

    logger.info(
        f"ingest: PDF ingestion complete. Total chunks: {doc_id}",
    )
    logger.info(
        "ingest: sensitivity distribution",
        extra=sensitivity_counts
    )
    return doc_id


async def run_full_ingestion():
    from app.services.schema import refresh_schema_cache
    logger.info("ingest: starting full data ingestion")
    await ingest_csvs_to_sqlite()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, ingest_pdfs_to_chroma)
    refresh_schema_cache()
    logger.info("ingest: full ingestion complete")
    return {"status": "success", "message": "All data sources ingested successfully."}