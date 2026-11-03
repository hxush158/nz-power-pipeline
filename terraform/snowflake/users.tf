# ChemQ 引擎用的只读服务用户：密钥对认证，只能读 MART。
# 私钥由 ChemQ 保管（已加密），这里只登记公钥。公钥文件是 PEM 格式，Snowflake 要求
# 只放正文、不含 BEGIN/END 两行、合成一行，所以先在这里剥掉头尾和换行。

locals {
  chemq_reporter_public_key = join("", [
    for line in split("\n", trimspace(file(pathexpand(var.chemq_reporter_public_key_path)))) :
    trimspace(line) if !startswith(line, "-----")
  ])
}

resource "snowflake_service_user" "chemq_reporter" {
  name    = var.chemq_reporter_user_name
  comment = "ChemQ engine, read-only access to NZ_POWER.MART"

  default_role      = snowflake_account_role.roles["NZ_REPORTER"].name
  default_warehouse = snowflake_warehouse.wh_xs.name
  default_namespace = "${snowflake_database.nz_power.name}.${snowflake_schema.layers["MART"].name}"

  # 单条语句最多跑 30 秒，防止 AI 生成的慢查询长时间占用 Warehouse。
  statement_timeout_in_seconds = 30

  rsa_public_key = local.chemq_reporter_public_key
}

# default_role 不会自动授权，必须单独把角色授给用户。
resource "snowflake_grant_account_role" "chemq_reporter" {
  role_name = snowflake_account_role.roles["NZ_REPORTER"].name
  user_name = snowflake_service_user.chemq_reporter.name
}

# ---- dbt 用的服务用户：以 NZ_TRANSFORMER 身份读 RAW，在 STAGING/MART 建对象 ----
# 与 ChemQ 用户同一套做法：密钥对认证，私钥加密并留在本机，这里只登记公钥。
# 不设 statement_timeout：dbt 全量构建比 AI 查询慢，不应被 30 秒截断。

locals {
  dbt_public_key = join("", [
    for line in split("\n", trimspace(file(pathexpand(var.dbt_public_key_path)))) :
    trimspace(line) if !startswith(line, "-----")
  ])
}

resource "snowflake_service_user" "dbt" {
  name    = var.dbt_user_name
  comment = "dbt transformations: reads RAW, builds STAGING and MART"

  default_role      = snowflake_account_role.roles["NZ_TRANSFORMER"].name
  default_warehouse = snowflake_warehouse.wh_xs.name
  default_namespace = "${snowflake_database.nz_power.name}.${snowflake_schema.layers["STAGING"].name}"

  rsa_public_key = local.dbt_public_key
}

resource "snowflake_grant_account_role" "dbt" {
  role_name = snowflake_account_role.roles["NZ_TRANSFORMER"].name
  user_name = snowflake_service_user.dbt.name
}
