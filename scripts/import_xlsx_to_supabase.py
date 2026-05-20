import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Please add it to your .env file.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace("-", "_")
    )

    return df


def prepare_dataframe(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path)
    df = normalize_columns(df)

    print("Original columns:")
    print(list(df.columns))

    required_columns = [
        "school_name",
        "source",
        "source_course_title",
        "target",
        "effdate",
        "target_course_title",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise RuntimeError(
                f"Missing required column: {column}. Current columns: {list(df.columns)}"
            )

    # 只保留 effdate 包含 To Present 的课程
    df["effdate"] = df["effdate"].astype(str).str.strip()

    df = df[
        df["effdate"]
        .str.contains("To Present", case=False, na=False)
    ].copy()

    # 重命名成数据库字段
    df = df.rename(
        columns={
            "school_name": "school_name",
            "source": "source_course_code",
            "source_course_title": "source_course_title",
            "target": "target_course_code",
            "target_course_title": "target_course_title",
            "effdate": "effective_date",
        }
    )

    output_columns = [
        "school_name",
        "source_course_code",
        "source_course_title",
        "target_course_code",
        "target_course_title",
        "effective_date",
    ]

    df = df[output_columns]

    # 清洗空值
    df = df.where(pd.notnull(df), None)

    return df


def import_to_supabase(df: pd.DataFrame, imported_from: str):
    columns = [
        "school_name",
        "source_course_code",
        "source_course_title",
        "target_course_code",
        "target_course_title",
        "effective_date",
        "imported_from",
    ]

    rows = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        row_dict["imported_from"] = imported_from
        rows.append(tuple(row_dict.get(column) for column in columns))

    if not rows:
        print("No valid rows to import after filtering To Present.")
        return

    insert_sql = f"""
           insert into transfer_equivalencies_raw ({", ".join(columns)})
           values %s
           on conflict (
           school_name,
           source_course_code,
           target_course_code,
           effective_date
         ) do nothing
     """

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows)
        conn.commit()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("python scripts/import_xlsx_to_supabase.py data/courses.xlsx")
        sys.exit(1)

    xlsx_path = Path(sys.argv[1]).resolve()

    if not xlsx_path.exists():
        raise FileNotFoundError(f"File not found: {xlsx_path}")

    print(f"Reading file: {xlsx_path}")

    df = prepare_dataframe(xlsx_path)

    print(f"Rows after filtering To Present: {len(df)}")
    print("Preview:")
    print(df.head())

    import_to_supabase(df, imported_from=xlsx_path.name)

    print(f"Successfully imported {len(df)} rows into Supabase.")


if __name__ == "__main__":
    main()