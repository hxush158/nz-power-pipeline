# Snowflake 读取 Azure 存储（ADLS）用的 Storage Integration。
# 只放开 raw 容器下的 prices/ 路径，不放开整个存储账号。
# apply 之后还要两步手工/另写的授权（见 README「Storage Integration」）：
#   1. 在 Snowflake 里 DESC STORAGE INTEGRATION INT_AZURE_RAW，取出 AZURE_CONSENT_URL，用 Azure 租户管理员打开并同意；
#   2. 在 Azure 里给 Snowflake 的应用（AZURE_MULTI_TENANT_APP_NAME）授予存储账号上的 Storage Blob Data Reader。
# 地址用 blob.core.windows.net（存储账号开了分层命名空间，Snowflake 官方对 ADLS Gen2 也用这个地址；实施时对照文档再确认一次）。

resource "snowflake_storage_integration_azure" "raw" {
  name            = "INT_AZURE_RAW"
  enabled         = true
  azure_tenant_id = var.azure_tenant_id

  storage_allowed_locations = [
    "azure://nzpowerhxu.blob.core.windows.net/raw/prices/",
    "azure://nzpowerhxu.blob.core.windows.net/raw/generation/",
  ]
}

# 只有 NZ_LOADER 能使用这个 integration 创建外部 Stage。
resource "snowflake_grant_privileges_to_account_role" "loader_integration_usage" {
  account_role_name = snowflake_account_role.roles["NZ_LOADER"].name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "INTEGRATION"
    object_name = snowflake_storage_integration_azure.raw.name
  }
}
