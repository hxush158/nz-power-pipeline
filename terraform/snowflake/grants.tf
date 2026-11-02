# 权限设计（最小权限）：
#   NZ_LOADER       只写 RAW（建表、建 Stage、建文件格式、往 RAW 表里加载数据）
#   NZ_TRANSFORMER  读 RAW；在 STAGING、MART 里建表和视图（dbt 用）
#   NZ_REPORTER     只读 MART（ChemQ 引擎用）；读不了 RAW 和 STAGING，也不能写任何东西
# 表和视图的 SELECT / INSERT 用 future grant：之后新建的对象自动获得权限。
# 现在这些 schema 里还没有对象，所以不需要 "all" 形式的授权。

locals {
  # 所有角色都需要用 Warehouse 和数据库
  usage_roles = local.roles

  schema_grants = {
    loader_raw       = { role = "NZ_LOADER", schema = "RAW", privileges = ["USAGE", "CREATE TABLE", "CREATE STAGE", "CREATE FILE FORMAT"] }
    transformer_raw  = { role = "NZ_TRANSFORMER", schema = "RAW", privileges = ["USAGE"] }
    transformer_stg  = { role = "NZ_TRANSFORMER", schema = "STAGING", privileges = ["USAGE", "CREATE TABLE", "CREATE VIEW"] }
    transformer_mart = { role = "NZ_TRANSFORMER", schema = "MART", privileges = ["USAGE", "CREATE TABLE", "CREATE VIEW"] }
    reporter_mart    = { role = "NZ_REPORTER", schema = "MART", privileges = ["USAGE"] }
  }

  # 未来对象的权限：谁在哪个 schema 里读哪类对象
  future_select_grants = {
    transformer_raw_tables = { role = "NZ_TRANSFORMER", schema = "RAW", object_type = "TABLES", privileges = ["SELECT"] }
    reporter_mart_tables   = { role = "NZ_REPORTER", schema = "MART", object_type = "TABLES", privileges = ["SELECT"] }
    reporter_mart_views    = { role = "NZ_REPORTER", schema = "MART", object_type = "VIEWS", privileges = ["SELECT"] }
    loader_raw_tables      = { role = "NZ_LOADER", schema = "RAW", object_type = "TABLES", privileges = ["SELECT", "INSERT"] }
  }
}

resource "snowflake_grant_privileges_to_account_role" "warehouse_usage" {
  for_each = local.usage_roles

  account_role_name = snowflake_account_role.roles[each.key].name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.wh_xs.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "database_usage" {
  for_each = local.usage_roles

  account_role_name = snowflake_account_role.roles[each.key].name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.nz_power.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "schema" {
  for_each = local.schema_grants

  account_role_name = snowflake_account_role.roles[each.value.role].name
  privileges        = each.value.privileges
  on_schema {
    schema_name = snowflake_schema.layers[each.value.schema].fully_qualified_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "future_objects" {
  for_each = local.future_select_grants

  account_role_name = snowflake_account_role.roles[each.value.role].name
  privileges        = each.value.privileges
  on_schema_object {
    future {
      object_type_plural = each.value.object_type
      in_schema          = snowflake_schema.layers[each.value.schema].fully_qualified_name
    }
  }
}
