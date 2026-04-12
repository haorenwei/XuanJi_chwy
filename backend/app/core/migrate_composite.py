"""
Database migration script for composite tools and tool versioning.

Adds:
- description_zh, tool_type columns to tools table
- tool_compositions table
- tool_versions table
- Initial v1 version snapshot for existing tools

This script is idempotent — safe to run multiple times.

Usage:
    cd backend
    python -m app.core.migrate_composite
"""

from sqlalchemy import inspect, text

from app.core.database import engine


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in columns


def _table_exists(inspector, table_name: str) -> bool:
    """Check if a table exists."""
    return inspector.has_table(table_name)


def migrate() -> None:
    """Run all migration steps."""
    inspector = inspect(engine)

    with engine.connect() as conn:
        # --- 1. ALTER TABLE tools: add description_zh ---
        if _table_exists(inspector, "tools") and not _column_exists(inspector, "tools", "description_zh"):
            conn.execute(text("ALTER TABLE `tools` ADD COLUMN `description_zh` TEXT NULL"))
            print("[migrate] Added column tools.description_zh")

        # --- 2. ALTER TABLE tools: add tool_type ---
        if _table_exists(inspector, "tools") and not _column_exists(inspector, "tools", "tool_type"):
            conn.execute(text(
                "ALTER TABLE `tools` ADD COLUMN `tool_type` VARCHAR(20) NOT NULL DEFAULT 'atomic'"
            ))
            print("[migrate] Added column tools.tool_type")

        # --- 3. CREATE TABLE tool_compositions ---
        if not _table_exists(inspector, "tool_compositions"):
            conn.execute(text("""
                CREATE TABLE `tool_compositions` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                    `composite_tool_id` BIGINT NOT NULL,
                    `sub_tool_id` BIGINT NOT NULL,
                    `step_order` INT NOT NULL,
                    `input_mapping` JSON NULL,
                    `output_key` VARCHAR(100) NOT NULL,
                    CONSTRAINT `fk_tc_composite_tool` FOREIGN KEY (`composite_tool_id`)
                        REFERENCES `tools` (`id`) ON DELETE CASCADE,
                    CONSTRAINT `fk_tc_sub_tool` FOREIGN KEY (`sub_tool_id`)
                        REFERENCES `tools` (`id`) ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            print("[migrate] Created table tool_compositions")

        # --- 4. CREATE TABLE tool_versions ---
        if not _table_exists(inspector, "tool_versions"):
            conn.execute(text("""
                CREATE TABLE `tool_versions` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                    `tool_id` BIGINT NOT NULL,
                    `version` INT NOT NULL,
                    `code` TEXT NULL,
                    `description` TEXT NULL,
                    `description_zh` TEXT NULL,
                    `pipeline_snapshot` JSON NULL,
                    `change_summary` TEXT NULL,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `created_by` BIGINT NULL,
                    CONSTRAINT `fk_tv_tool` FOREIGN KEY (`tool_id`)
                        REFERENCES `tools` (`id`) ON DELETE CASCADE,
                    CONSTRAINT `fk_tv_created_by` FOREIGN KEY (`created_by`)
                        REFERENCES `users` (`id`) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            print("[migrate] Created table tool_versions")

        # --- 5. ALTER TABLE user_settings: add intent_llm columns ---
        if _table_exists(inspector, "user_settings"):
            for col in ("intent_llm_provider", "intent_llm_api_key", "intent_llm_model_name"):
                if not _column_exists(inspector, "user_settings", col):
                    col_type = "VARCHAR(20)" if col == "intent_llm_provider" else (
                        "VARCHAR(500)" if col == "intent_llm_api_key" else "VARCHAR(100)"
                    )
                    conn.execute(text(
                        f"ALTER TABLE `user_settings` ADD COLUMN `{col}` {col_type} NULL"
                    ))
                    print(f"[migrate] Added column user_settings.{col}")

        # --- 6. INSERT initial v1 snapshots for existing tools ---
        result = conn.execute(text("""
            SELECT t.id, t.code, t.description, t.description_zh, t.created_by
            FROM `tools` t
            WHERE NOT EXISTS (
                SELECT 1 FROM `tool_versions` tv WHERE tv.tool_id = t.id
            )
        """))
        rows = result.fetchall()
        for row in rows:
            conn.execute(text("""
                INSERT INTO `tool_versions` (`tool_id`, `version`, `code`, `description`, `description_zh`, `change_summary`, `created_by`)
                VALUES (:tool_id, 1, :code, :description, :description_zh, 'Initial version snapshot', :created_by)
            """), {
                "tool_id": row[0],
                "code": row[1],
                "description": row[2],
                "description_zh": row[3],
                "created_by": row[4],
            })
        if rows:
            print(f"[migrate] Created v1 snapshots for {len(rows)} existing tools")

        # --- 7. ALTER TABLE user_settings: add show_tool_result ---
        if _table_exists(inspector, "user_settings") and not _column_exists(inspector, "user_settings", "show_tool_result"):
            conn.execute(text(
                "ALTER TABLE `user_settings` ADD COLUMN `show_tool_result` TINYINT(1) DEFAULT 1"
            ))
            print("[migrate] Added column user_settings.show_tool_result")

        # --- 8. ALTER TABLE token_usages: add role_name ---
        if _table_exists(inspector, "token_usages") and not _column_exists(inspector, "token_usages", "role_name"):
            conn.execute(text(
                "ALTER TABLE `token_usages` ADD COLUMN `role_name` VARCHAR(20) NULL"
            ))
            print("[migrate] Added column token_usages.role_name")

        # --- 9. ALTER TABLE user_settings: add show_collaboration ---
        if _table_exists(inspector, "user_settings") and not _column_exists(inspector, "user_settings", "show_collaboration"):
            conn.execute(text(
                "ALTER TABLE `user_settings` ADD COLUMN `show_collaboration` TINYINT(1) DEFAULT NULL"
            ))
            print("[migrate] Added column user_settings.show_collaboration")

        conn.commit()

    print("[migrate] Migration completed successfully.")


if __name__ == "__main__":
    migrate()
