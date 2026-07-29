"""Sprint 3 L3: sorgu ve veri boyutu kullanım takibi demosu."""

from __future__ import annotations

import json

import pandas as pd

from src.utils.logger import clear_request_id, set_request_id
from src.utils.usage_tracker import UsageTracker


def main() -> None:
    tracker = UsageTracker()
    set_request_id("req-demo-usage-001")

    try:
        query_result = pd.DataFrame(
            {
                "category": ["Tekstil", "Elektronik", "Gıda"],
                "revenue": [12000, 9500, 7800],
            }
        )

        tracker.record_query(
            result_data=query_result,
            source_type="postgresql",
            tenant_id="tenant-demo",
            user_id="user-demo",
            session_id="sess-demo",
        )
        tracker.record_query(
            source_type="postgresql",
            success=False,
            tenant_id="tenant-demo",
            user_id="user-demo",
            session_id="sess-demo",
            row_count=0,
            data_size_bytes=0,
        )

        print("\nTENANT KULLANIM ÖZETİ")
        print(
            json.dumps(
                tracker.summarize(tenant_id="tenant-demo").as_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        clear_request_id()


if __name__ == "__main__":
    main()
