# Snowflake 基础设施：额度保护、计算、数据库与 schema、角色。
# 资源名来自 provider 官方文档（均为 Stable，非 preview）。权限在 grants.tf。
#
# 命名：数据库 NZ_POWER；schema RAW / STAGING / MART；Warehouse WH_XS；
#       角色 NZ_LOADER / NZ_TRANSFORMER / NZ_REPORTER。

locals {
  schemas = toset(["RAW", "STAGING", "CORE", "MART"])
  roles   = toset(["NZ_LOADER", "NZ_TRANSFORMER", "NZ_REPORTER"])
}

# 额度保护：每月 20 credits。到 100% 暂停 Warehouse，到 110% 立刻取消正在运行的语句。
# 需要 ACCOUNTADMIN 才能把 monitor 绑定到 Warehouse（provider 连接角色已是 ACCOUNTADMIN）。
resource "snowflake_resource_monitor" "nz_power" {
  name         = "RM_NZ_POWER"
  credit_quota = 20

  frequency       = "MONTHLY"
  start_timestamp = "IMMEDIATELY"

  notify_triggers           = [50, 80]
  suspend_trigger           = 100
  suspend_immediate_trigger = 110
}

resource "snowflake_warehouse" "wh_xs" {
  name                = "WH_XS"
  warehouse_size      = "XSMALL"
  auto_suspend        = 60
  auto_resume         = "true"
  initially_suspended = true
  resource_monitor    = snowflake_resource_monitor.nz_power.name
}

resource "snowflake_database" "nz_power" {
  name = "NZ_POWER"
}

resource "snowflake_schema" "layers" {
  for_each = local.schemas

  database = snowflake_database.nz_power.name
  name     = each.key
}

resource "snowflake_account_role" "roles" {
  for_each = local.roles

  name = each.key
}

# 自定义角色挂到 SYSADMIN 下，管理员能看到这些角色创建的对象。
resource "snowflake_grant_account_role" "to_sysadmin" {
  for_each = local.roles

  role_name        = snowflake_account_role.roles[each.key].name
  parent_role_name = "SYSADMIN"
}
