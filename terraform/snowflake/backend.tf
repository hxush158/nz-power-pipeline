# 状态文件放在 Azure 存储账号的同一个 tfstate 容器里，用单独的 key，与 Azure 资源的状态分开。
# 认证和订阅 ID 同 ../README.md（az login + ARM_SUBSCRIPTION_ID）。
terraform {
  backend "azurerm" {
    resource_group_name  = "rg_nz_power"
    storage_account_name = "nzpowerhxu"
    container_name       = "tfstate"
    key                  = "snowflake.tfstate"
  }
}
