terraform {
  required_version = ">= 1.6"

  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.20"
    }
  }
}

# 密钥对认证（SNOWFLAKE_JWT）。私钥文件放在仓库外面，路径通过变量传入。
# 注意：provider 里 preview 资源默认关闭，且不受大版本约束，不要随手打开 preview_features_enabled。
provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_user
  authenticator     = "SNOWFLAKE_JWT"
  private_key       = file(pathexpand(var.snowflake_private_key_path))
  role              = var.snowflake_role
}
