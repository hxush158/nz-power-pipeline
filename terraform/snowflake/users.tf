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
